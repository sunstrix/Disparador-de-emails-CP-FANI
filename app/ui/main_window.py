# ==============================================================================
# JANELA PRINCIPAL - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Interface gráfica principal com abas para configuração SMTP, importação de
# contatos, editor de mensagens, controle de envio e visualização de logs.
# Inclui bandeja do sistema, faixa de atualização e integração com UpdateManager.

import os
import json
import sys
import glob
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, QFileDialog,
    QMessageBox, QSpinBox, QProgressBar, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QGroupBox, QFormLayout,
    QMenu, QStatusBar, QApplication, QSystemTrayIcon, QInputDialog,
    QFrame, QStyle
)
from PySide6.QtGui import QPixmap, QIcon, QAction, QFont, QColor, QCloseEvent
from PySide6.QtCore import Qt, QTimer, QThread, Signal

import keyring
from keyring.errors import PasswordDeleteError, KeyringError

from app.config import (
    APP_TITLE, APP_VERSION, MAX_DAILY_LIMIT, DEFAULT_DAILY_LIMIT,
    MIN_INTERVAL_SECONDS, MAX_INTERVAL_SECONDS, SMTP_SERVERS,
    REPORT_EMAIL, LOGO_FILE, FALLBACK_NOME, LOGS_DIR, ICON_FILE
)
from app.core.importer import load_contacts, process_contacts
from app.core.template_engine import render_template, validate_variables
from app.core.smtp_client import SMTPClient
from app.core.sender_worker import SenderWorker
from app.core.logger import CampaignLogger
from app.core.updater import UpdateManager
from app.ui.components import RichTextEditor, ContactsTableView
from app.ui.styles import get_stylesheet

KEYRING_SERVICE = "DisparadorCPFani"


# ==============================================================================
# WORKERS PARA TESTES (P1-1: não bloqueiam a UI)
# ==============================================================================

class SMTPTestWorker(QThread):
    """Worker para testar conexão SMTP em background."""
    finished = Signal(bool, str)
    
    def __init__(self, smtp_config: dict):
        super().__init__()
        self.smtp_config = smtp_config
        
    def run(self):
        try:
            client = SMTPClient(
                provider=self.smtp_config['provider'],
                email=self.smtp_config['email'],
                password=self.smtp_config['password'],
                port=self.smtp_config['port'],
                security=self.smtp_config['security']
            )
            success, message = client.test_connection()
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, str(e))


class TestEmailWorker(QThread):
    """Worker para enviar e-mail de teste em background."""
    finished = Signal(bool, str)
    
    def __init__(self, smtp_config: dict, to_email: str, to_name: str, 
                 subject: str, html_body: str, text_body: str):
        super().__init__()
        self.smtp_config = smtp_config
        self.to_email = to_email
        self.to_name = to_name
        self.subject = subject
        self.html_body = html_body
        self.text_body = text_body
        
    def run(self):
        try:
            client = SMTPClient(
                provider=self.smtp_config['provider'],
                email=self.smtp_config['email'],
                password=self.smtp_config['password'],
                port=self.smtp_config['port'],
                security=self.smtp_config['security']
            )
            success, message = client.send_email(
                self.to_email, self.to_name, self.subject, 
                self.html_body, self.text_body
            )
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, str(e))


class ReportWorker(QThread):
    """Worker para enviar relatório final em background (P0-9)."""
    finished = Signal(bool, str)
    
    def __init__(self, logger: CampaignLogger, summary: dict, smtp_config: dict):
        super().__init__()
        self.logger = logger
        self.summary = summary
        self.smtp_config = smtp_config
        
    def run(self):
        try:
            success, message = self.logger.send_final_report(self.summary, self.smtp_config)
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, str(e))


# ==============================================================================
# JANELA PRINCIPAL
# ==============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} v{APP_VERSION}")
        self.resize(1100, 750)
        self.setMinimumSize(900, 600)
        
        # Aplica o stylesheet global (Parte 3C)
        self.setStyleSheet(get_stylesheet())
        
        # Estado interno
        self.df_raw = None
        self.df_clean = None
        self.contacts_stats = {}
        self.detected_columns = {}
        self.available_sheets = []
        self.current_file_path = ""
        self.worker: Optional[SenderWorker] = None
        self.logger: Optional[CampaignLogger] = None
        self.smtp_config = {}
        
        # Workers de teste (P1-1)
        self.test_worker: Optional[SMTPTestWorker] = None
        self.test_email_worker: Optional[TestEmailWorker] = None
        self.report_worker: Optional[ReportWorker] = None
        
        # Gerenciador de atualização (Parte 4E)
        self.update_manager = UpdateManager()
        
        # Bandeja do sistema (Parte 3B)
        self.tray_icon: Optional[QSystemTrayIcon] = None
        
        self._init_ui()
        self._create_tray_icon()
        self._load_smtp_credentials()
        
        # Inicia verificação de atualização em background (Parte 4E)
        self.update_manager.start_check()

    # ==========================================================================
    # INICIALIZAÇÃO DA INTERFACE
    # ==========================================================================
    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Cabeçalho com Logo, Título e Versão (Parte 3C)
        header_layout = QHBoxLayout()
        
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(80, 80)
        self.logo_label.setAlignment(Qt.AlignCenter)
        self._load_logo()
        header_layout.addWidget(self.logo_label)
        
        title_layout = QVBoxLayout()
        self.title_label = QLabel(APP_TITLE)
        self.title_label.setObjectName("title_label")
        self.title_label.setAlignment(Qt.AlignLeft)
        title_layout.addWidget(self.title_label)
        
        self.version_label = QLabel(f"Versão {APP_VERSION}")
        self.version_label.setObjectName("version_label")
        self.version_label.setAlignment(Qt.AlignLeft)
        title_layout.addWidget(self.version_label)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Botão de verificação manual de atualização (Parte 4E)
        self.btn_check_update = QPushButton("Verificar atualização")
        self.btn_check_update.setProperty("outline", True)
        self.btn_check_update.clicked.connect(self._manual_check_update)
        header_layout.addWidget(self.btn_check_update)
        
        main_layout.addLayout(header_layout)
        
        # Faixa de atualização (Parte 4E)
        self._create_update_banner()
        main_layout.addWidget(self.update_banner)

        # Abas principais
        self.tabs = QTabWidget()
        self.tab_smtp = self._create_smtp_tab()
        self.tab_contacts = self._create_contacts_tab()
        self.tab_message = self._create_message_tab()
        self.tab_send = self._create_send_tab()
        self.tab_log = self._create_log_tab()

        self.tabs.addTab(self.tab_smtp, "1. Configuração SMTP")
        self.tabs.addTab(self.tab_contacts, "2. Destinatários")
        self.tabs.addTab(self.tab_message, "3. Mensagem")
        self.tabs.addTab(self.tab_send, "4. Envio")
        self.tabs.addTab(self.tab_log, "5. Log")

        main_layout.addWidget(self.tabs, 1)

        # Barra de status
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Pronto. Configure o SMTP para começar.")
        
        # Conecta sinais do UpdateManager (Parte 4E)
        if self.update_manager.checker:
            self.update_manager.checker.update_available.connect(self._on_update_available)
            self.update_manager.checker.no_update.connect(self._on_no_update)

    def _load_logo(self):
        """Carrega o logo com fallback para texto."""
        if os.path.exists(LOGO_FILE):
            pixmap = QPixmap(LOGO_FILE)
            if not pixmap.isNull():
                self.logo_label.setPixmap(
                    pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                return
        # Fallback
        self.logo_label.setText("CP\nFANI")
        self.logo_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.logo_label.setStyleSheet("color: #2e7d32;")

    def _create_update_banner(self):
        """Cria a faixa de atualização no topo (Parte 4E)."""
        self.update_banner = QFrame()
        self.update_banner.setStyleSheet("""
            QFrame {
                background-color: #E8F5E9;
                border: 1px solid #2E7D32;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        self.update_banner.setVisible(False)
        
        layout = QHBoxLayout(self.update_banner)
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.update_label = QLabel("Nova versão disponível!")
        self.update_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
        layout.addWidget(self.update_label)
        
        layout.addStretch()
        
        btn_update = QPushButton("Atualizar agora")
        btn_update.setProperty("primary", True)
        btn_update.clicked.connect(self._on_update_now)
        layout.addWidget(btn_update)
        
        btn_later = QPushButton("Depois")
        btn_later.setProperty("outline", True)
        btn_later.clicked.connect(self._on_update_later)
        layout.addWidget(btn_later)

    # ==========================================================================
    # BANDEJA DO SISTEMA (Parte 3B)
    # ==========================================================================
    def _create_tray_icon(self):
        """Cria o ícone da bandeja do sistema com menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
            
        self.tray_icon = QSystemTrayIcon(self)
        
        # Ícone: preferir .ico, fallback para .png
        if os.path.exists(ICON_FILE):
            icon = QIcon(ICON_FILE)
        elif os.path.exists(LOGO_FILE):
            icon = QIcon(LOGO_FILE)
        else:
            icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
            
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip(f"{APP_TITLE} v{APP_VERSION}")
        
        # Menu da bandeja
        tray_menu = QMenu()
        
        open_action = QAction("Abrir janela", self)
        open_action.triggered.connect(self.show_from_tray)
        tray_menu.addAction(open_action)
        
        self.pause_resume_action = QAction("Pausar", self)
        self.pause_resume_action.triggered.connect(self._toggle_pause_from_tray)
        self.pause_resume_action.setEnabled(False)
        tray_menu.addAction(self.pause_resume_action)
        
        tray_menu.addSeparator()
        
        self.status_action = QAction("Status: Aguardando", self)
        self.status_action.setEnabled(False)
        tray_menu.addAction(self.status_action)
        
        tray_menu.addSeparator()
        
        exit_action = QAction("Sair", self)
        exit_action.triggered.connect(self._exit_from_tray)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def show_from_tray(self):
        """Mostra a janela a partir da bandeja."""
        self.show()
        self.showNormal()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        """Duplo clique na bandeja reabre a janela."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_from_tray()

    def _toggle_pause_from_tray(self):
        """Alterna pausa/retomada a partir da bandeja."""
        if not self.worker:
            return
        if self.worker._is_paused:
            self._resume_sending()
        else:
            self._pause_sending()

    def _exit_from_tray(self):
        """Sai do aplicativo a partir da bandeja."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Confirmar saída",
                "Há um envio em andamento. Deseja parar e sair?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            self.worker.stop()
            self.worker.wait(5000)
        
        if self.update_manager:
            self.update_manager.stop_check()
        
        self._cleanup_temp_images()
        QApplication.quit()

    def _cleanup_temp_images(self):
        """Expurga imagens temporárias coladas na área de trabalho/editor (Ctrl+V)."""
        try:
            temp_dir = tempfile.gettempdir()
            # Padrões comuns de imagens salvas na pasta temp
            patterns = [
                os.path.join(temp_dir, "pasted_img_*.png"),
                os.path.join(temp_dir, "pasted_img_*.jpg"),
                os.path.join(temp_dir, "cpfani_temp_*.png")
            ]
            for pattern in patterns:
                for img_path in glob.glob(pattern):
                    try:
                        if os.path.exists(img_path):
                            os.remove(img_path)
                    except Exception:
                        pass
        except Exception:
            pass

    # ==========================================================================
    # CLOSE EVENT (P0-8)
    # ==========================================================================
    def closeEvent(self, event: QCloseEvent):
        """Impede fechamento durante envio, ocultando para bandeja."""
        if self.worker and self.worker.isRunning():
            event.ignore()
            self.hide()
            if self.tray_icon:
                self.tray_icon.showMessage(
                    APP_TITLE,
                    "O envio continua em segundo plano. Clique com o botão direito no ícone da bandeja para mais opções.",
                    QSystemTrayIcon.Information,
                    3000
                )
        else:
            if self.update_manager:
                self.update_manager.stop_check()
            self._cleanup_temp_images()
            event.accept()

    # ==========================================================================
    # ABA 1: CONFIGURAÇÃO SMTP
    # ==========================================================================
    def _create_smtp_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Servidor de E-mail")
        form = QFormLayout()

        self.combo_provider = QComboBox()
        self.combo_provider.addItems(SMTP_SERVERS.keys())
        self.combo_provider.currentTextChanged.connect(self._on_provider_changed)
        form.addRow("Provedor:", self.combo_provider)

        self.combo_port = QComboBox()
        form.addRow("Porta/Segurança:", self.combo_port)

        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("seuemail@gmail.com")
        form.addRow("E-mail remetente:", self.input_email)

        # Senha com botão mostrar/ocultar
        pwd_layout = QHBoxLayout()
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.Password)
        self.input_password.setPlaceholderText("Senha ou Senha de App")
        pwd_layout.addWidget(self.input_password)

        self.btn_toggle_pwd = QPushButton("Mostrar")
        self.btn_toggle_pwd.setCheckable(True)
        self.btn_toggle_pwd.clicked.connect(self._toggle_password_visibility)
        pwd_layout.addWidget(self.btn_toggle_pwd)

        pwd_widget = QWidget()
        pwd_widget.setLayout(pwd_layout)
        form.addRow("Senha:", pwd_widget)

        self.chk_remember = QCheckBox("Lembrar credenciais (armazenamento seguro no SO)")
        form.addRow("", self.chk_remember)

        group.setLayout(form)
        layout.addWidget(group)

        self.label_smtp_warning = QLabel()
        self.label_smtp_warning.setWordWrap(True)
        self.label_smtp_warning.setStyleSheet("color: #d32f2f; font-weight: bold;")
        layout.addWidget(self.label_smtp_warning)

        btn_layout = QHBoxLayout()
        self.btn_test_connection = QPushButton("Testar Conexão")
        self.btn_test_connection.setProperty("primary", True)
        self.btn_test_connection.clicked.connect(self._test_smtp_connection)
        btn_layout.addWidget(self.btn_test_connection)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

        self._on_provider_changed(self.combo_provider.currentText())
        return widget

    def _on_provider_changed(self, provider: str):
        self.combo_port.clear()
        config = SMTP_SERVERS.get(provider, {})
        ports = config.get("ports", {})
        self.combo_port.addItems(ports.keys())
        self.label_smtp_warning.setText(config.get("warning", ""))

    def _toggle_password_visibility(self, checked):
        self.input_password.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        self.btn_toggle_pwd.setText("Ocultar" if checked else "Mostrar")

    def _load_smtp_credentials(self):
        """Carrega credenciais do keyring com tratamento de erros (P0-10)."""
        try:
            saved_email = keyring.get_password(KEYRING_SERVICE, "email")
            if saved_email:
                self.input_email.setText(saved_email)
                self.chk_remember.setChecked(True)
            
            saved_password = keyring.get_password(KEYRING_SERVICE, "password")
            if saved_password:
                self.input_password.setText(saved_password)
        except KeyringError:
            # Backend indisponível ou erro de acesso: ignora silenciosamente
            pass
        except Exception:
            pass

    def _save_smtp_credentials(self):
        """Salva credenciais no keyring com tratamento de erros (P0-10)."""
        try:
            if self.chk_remember.isChecked():
                keyring.set_password(KEYRING_SERVICE, "email", self.input_email.text())
                keyring.set_password(KEYRING_SERVICE, "password", self.input_password.text())
            else:
                try:
                    keyring.delete_password(KEYRING_SERVICE, "email")
                except PasswordDeleteError:
                    pass  # Não existia
                try:
                    keyring.delete_password(KEYRING_SERVICE, "password")
                except PasswordDeleteError:
                    pass  # Não existia
        except KeyringError:
            pass
        except Exception:
            pass

    def _get_smtp_config(self) -> Dict[str, Any]:
        provider = self.combo_provider.currentText()
        port_text = self.combo_port.currentText()
        port_config = SMTP_SERVERS[provider]["ports"][port_text]
        return {
            "provider": provider,
            "email": self.input_email.text().strip(),
            "password": self.input_password.text(),
            "port": port_config["port"],
            "security": port_config["security"]
        }

    def _test_smtp_connection(self):
        """Testa conexão em background (P1-1)."""
        config = self._get_smtp_config()
        if not config["email"] or not config["password"]:
            QMessageBox.warning(self, "Atenção", "Preencha o e-mail e a senha.")
            return

        self.btn_test_connection.setEnabled(False)
        self.btn_test_connection.setText("Testando...")
        self.status_bar.showMessage("Testando conexão SMTP...")
        
        self.test_worker = SMTPTestWorker(config)
        self.test_worker.finished.connect(self._on_test_connection_finished)
        self.test_worker.start()

    def _on_test_connection_finished(self, success: bool, message: str):
        """Callback do teste de conexão."""
        self.btn_test_connection.setEnabled(True)
        self.btn_test_connection.setText("Testar Conexão")
        
        if success:
            QMessageBox.information(self, "Sucesso", message)
            self._save_smtp_credentials()
            self.smtp_config = self._get_smtp_config()
            self.status_bar.showMessage("Conexão SMTP testada com sucesso.")
        else:
            QMessageBox.critical(self, "Falha", message)
            self.status_bar.showMessage("Falha no teste de conexão SMTP.")

    # ==========================================================================
    # ABA 2: DESTINATÁRIOS
    # ==========================================================================
    def _create_contacts_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Importação
        import_group = QGroupBox("Importar Planilha")
        import_layout = QHBoxLayout()

        self.btn_import = QPushButton("Selecionar Arquivo (.xlsx ou .csv)")
        self.btn_import.clicked.connect(self._import_file)
        import_layout.addWidget(self.btn_import)

        import_layout.addWidget(QLabel("Aba:"))
        self.combo_sheet = QComboBox()
        self.combo_sheet.currentTextChanged.connect(self._on_sheet_changed)
        import_layout.addWidget(self.combo_sheet)

        import_group.setLayout(import_layout)
        layout.addWidget(import_group)

        # Mapeamento de colunas
        map_group = QGroupBox("Mapeamento de Colunas (Auto-detectado)")
        map_layout = QFormLayout()

        self.combo_col_codigo = QComboBox()
        self.combo_col_nome = QComboBox()
        self.combo_col_email = QComboBox()

        map_layout.addRow("Coluna Código:", self.combo_col_codigo)
        map_layout.addRow("Coluna Nome:", self.combo_col_nome)
        map_layout.addRow("Coluna E-mail:", self.combo_col_email)

        self.btn_process = QPushButton("Processar e Validar Dados")
        self.btn_process.setProperty("primary", True)
        self.btn_process.clicked.connect(self._process_contacts)
        map_layout.addRow("", self.btn_process)

        map_group.setLayout(map_layout)
        layout.addWidget(map_group)

        # Tabela de pré-visualização
        self.contacts_table = ContactsTableView()
        layout.addWidget(self.contacts_table, 1)

        return widget

    def _clear_contacts_state(self):
        """Limpa o estado de contatos (P0-6)."""
        self.df_raw = None
        self.df_clean = None
        self.contacts_stats = {}
        self.detected_columns = {}
        self.contacts_table.clear()
        self.status_bar.showMessage("Estado de contatos limpo.")

    def _import_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Planilha", "",
            "Planilhas (*.xlsx *.csv);;Todos os arquivos (*)"
        )
        if not file_path:
            return

        # Limpa estado anterior (P0-6)
        self._clear_contacts_state()
        
        self.current_file_path = file_path
        df, result = load_contacts(file_path)

        if not result["success"]:
            QMessageBox.critical(self, "Erro", result["error_message"])
            return

        self.df_raw = df
        self.available_sheets = result["available_sheets"]
        self.detected_columns = result["detected_columns"]

        # Atualiza combo de abas
        self.combo_sheet.blockSignals(True)
        self.combo_sheet.clear()
        if self.available_sheets:
            self.combo_sheet.addItems(self.available_sheets)
        self.combo_sheet.blockSignals(False)

        self._update_column_combos()
        self.status_bar.showMessage(f"Arquivo carregado: {os.path.basename(file_path)}. Clique em 'Processar' para validar.")

    def _on_sheet_changed(self, sheet_name: str):
        """Troca de aba com limpeza de estado (P0-6)."""
        if not self.current_file_path or not sheet_name:
            return
        
        # Limpa estado anterior
        self.df_clean = None
        self.contacts_stats = {}
        self.contacts_table.clear()
        
        df, result = load_contacts(self.current_file_path, sheet_name)
        if result["success"]:
            self.df_raw = df
            self.detected_columns = result["detected_columns"]
            self._update_column_combos()
            self.status_bar.showMessage(f"Aba '{sheet_name}' carregada. Clique em 'Processar' para validar.")
        else:
            QMessageBox.warning(self, "Aviso", result["error_message"])
            self.df_raw = None
            self.detected_columns = {}
            self.status_bar.showMessage("Falha ao carregar aba.")

    def _update_column_combos(self):
        if self.df_raw is None:
            return

        cols = list(self.df_raw.columns)
        for combo in [self.combo_col_codigo, self.combo_col_nome, self.combo_col_email]:
            combo.clear()
            combo.addItems(cols)

        # Aplica auto-detecção
        if "codigo" in self.detected_columns:
            idx = cols.index(self.detected_columns["codigo"])
            self.combo_col_codigo.setCurrentIndex(idx)
        if "nome" in self.detected_columns:
            idx = cols.index(self.detected_columns["nome"])
            self.combo_col_nome.setCurrentIndex(idx)
        if "email" in self.detected_columns:
            idx = cols.index(self.detected_columns["email"])
            self.combo_col_email.setCurrentIndex(idx)

    def _process_contacts(self):
        if self.df_raw is None:
            QMessageBox.warning(self, "Atenção", "Importe um arquivo primeiro.")
            return

        col_codigo = self.combo_col_codigo.currentText()
        col_nome = self.combo_col_nome.currentText()
        col_email = self.combo_col_email.currentText()

        self.df_clean, self.contacts_stats = process_contacts(
            self.df_raw, col_codigo, col_nome, col_email
        )

        self.contacts_table.load_data(self.df_clean, self.contacts_stats)

        if self.contacts_stats["validos"] == 0:
            QMessageBox.warning(self, "Atenção", "Nenhum contato válido encontrado.")
        else:
            self.status_bar.showMessage(
                f"{self.contacts_stats['validos']} contatos válidos prontos para envio."
            )

    # ==========================================================================
    # ABA 3: MENSAGEM
    # ==========================================================================
    def _create_message_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Assunto
        subject_layout = QHBoxLayout()
        subject_layout.addWidget(QLabel("Assunto:"))
        self.input_subject = QLineEdit()
        self.input_subject.setPlaceholderText("Ex: Olá {{primeiro_nome}}, temos uma novidade!")
        subject_layout.addWidget(self.input_subject)

        self.btn_insert_var_subject = QPushButton("Inserir Variável ▼")
        self.btn_insert_var_subject.clicked.connect(lambda: self._show_variables_menu(self.input_subject))
        subject_layout.addWidget(self.btn_insert_var_subject)
        layout.addLayout(subject_layout)

        # Editor Rico
        self.editor = RichTextEditor()
        layout.addWidget(self.editor, 1)

        # Botões de ação
        btn_layout = QHBoxLayout()

        self.btn_insert_var_body = QPushButton("Inserir Variável ▼")
        self.btn_insert_var_body.clicked.connect(lambda: self._show_variables_menu(self.editor.text_edit))
        btn_layout.addWidget(self.btn_insert_var_body)

        self.btn_preview = QPushButton("Pré-visualizar")
        self.btn_preview.clicked.connect(self._preview_message)
        btn_layout.addWidget(self.btn_preview)

        self.btn_save_template = QPushButton("Salvar Modelo")
        self.btn_save_template.clicked.connect(self._save_template)
        btn_layout.addWidget(self.btn_save_template)

        self.btn_load_template = QPushButton("Carregar Modelo")
        self.btn_load_template.clicked.connect(self._load_template)
        btn_layout.addWidget(self.btn_load_template)

        layout.addLayout(btn_layout)

        return widget

    def _show_variables_menu(self, target_widget):
        if self.df_clean is None or self.df_clean.empty:
            QMessageBox.warning(self, "Atenção", "Importe e processe os contatos primeiro.")
            return

        menu = QMenu(self)
        columns = list(self.df_clean.columns)

        # Variáveis especiais
        special_vars = ["primeiro_nome", "nome_completo", "email", "codigorevendedor"]
        for var in special_vars:
            action = QAction(f"{{{{{var}}}}}", self)
            action.triggered.connect(lambda checked, v=var, w=target_widget: self._insert_variable(w, v))
            menu.addAction(action)

        menu.addSeparator()

        # Colunas da planilha
        for col in columns:
            if col not in ["CodigoRevendedor", "Nome", "EMail"]:
                var_name = col.lower().replace(" ", "_")
                action = QAction(f"{{{{{var_name}}}}}", self)
                action.triggered.connect(lambda checked, v=var_name, w=target_widget: self._insert_variable(w, v))
                menu.addAction(action)

        menu.exec(target_widget.mapToGlobal(target_widget.rect().bottomLeft()) if hasattr(target_widget, 'mapToGlobal') else self.mapToGlobal(self.rect().bottomLeft()))

    def _insert_variable(self, widget, var_name: str):
        var_text = f"{{{{{var_name}}}}}"
        if isinstance(widget, QLineEdit):
            widget.insert(var_text)
        elif isinstance(widget, QTextEdit):
            widget.insertPlainText(var_text)

    def _preview_message(self):
        if self.df_clean is None or self.df_clean.empty:
            QMessageBox.warning(self, "Atenção", "Nenhum contato para pré-visualização.")
            return

        first_contact = self.df_clean.iloc[0].to_dict()
        subject = render_template(self.input_subject.text(), first_contact)
        html = render_template(self.editor.to_html(), first_contact)

        preview_dialog = QMessageBox(self)
        preview_dialog.setWindowTitle("Pré-visualização")
        preview_dialog.setText(f"<b>Assunto:</b> {subject}<br><br><b>Corpo:</b><br>{html}")
        preview_dialog.setTextFormat(Qt.RichText)
        preview_dialog.resize(700, 500)
        preview_dialog.exec()

    def _save_template(self):
        name, ok = QInputDialog.getText(self, "Salvar Modelo", "Nome do modelo:")
        if ok and name:
            success, message = self.editor.save_template(name, self.input_subject.text())
            if success:
                QMessageBox.information(self, "Sucesso", message)
            else:
                QMessageBox.critical(self, "Erro", message)

    def _load_template(self):
        templates = self.editor.list_templates()
        if not templates:
            QMessageBox.information(self, "Aviso", "Nenhum modelo salvo ainda.")
            return
        
        name, ok = QInputDialog.getItem(
            self, "Carregar Modelo", "Selecione um modelo:", 
            templates, 0, False
        )
        if ok and name:
            success, subject, html = self.editor.load_template(name)
            if success:
                self.input_subject.setText(subject)
                self.editor.from_html(html)
            else:
                QMessageBox.critical(self, "Erro", "Falha ao carregar modelo.")

    # ==========================================================================
    # ABA 4: ENVIO
    # ==========================================================================
    def _create_send_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Configurações de envio
        config_group = QGroupBox("Configurações de Disparo")
        config_layout = QFormLayout()

        self.spin_daily_limit = QSpinBox()
        self.spin_daily_limit.setRange(1, MAX_DAILY_LIMIT)
        self.spin_daily_limit.setValue(DEFAULT_DAILY_LIMIT)
        self.spin_daily_limit.setSuffix(f" e-mails (máx. {MAX_DAILY_LIMIT}/dia)")
        config_layout.addRow("Limite diário:", self.spin_daily_limit)

        interval_layout = QHBoxLayout()
        self.spin_min_interval = QSpinBox()
        self.spin_min_interval.setRange(1, 3600)
        self.spin_min_interval.setValue(MIN_INTERVAL_SECONDS)
        self.spin_min_interval.setSuffix(" s")
        interval_layout.addWidget(self.spin_min_interval)

        interval_layout.addWidget(QLabel("até"))

        self.spin_max_interval = QSpinBox()
        self.spin_max_interval.setRange(1, 3600)
        self.spin_max_interval.setValue(MAX_INTERVAL_SECONDS)
        self.spin_max_interval.setSuffix(" s")
        interval_layout.addWidget(self.spin_max_interval)

        interval_widget = QWidget()
        interval_widget.setLayout(interval_layout)
        config_layout.addRow("Intervalo entre envios:", interval_widget)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # E-mail de teste
        test_group = QGroupBox("Enviar E-mail de Teste")
        test_layout = QHBoxLayout()
        self.input_test_email = QLineEdit()
        self.input_test_email.setPlaceholderText("seuemail@teste.com")
        test_layout.addWidget(self.input_test_email)

        self.btn_send_test = QPushButton("Enviar Teste")
        self.btn_send_test.clicked.connect(self._send_test_email)
        test_layout.addWidget(self.btn_send_test)
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)

        # Controles de envio
        controls_group = QGroupBox("Controle de Disparo")
        controls_layout = QVBoxLayout()

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("▶ Iniciar")
        self.btn_start.setProperty("primary", True)
        self.btn_start.clicked.connect(self._start_sending)
        btn_row.addWidget(self.btn_start)

        self.btn_pause = QPushButton("⏸ Pausar")
        self.btn_pause.clicked.connect(self._pause_sending)
        self.btn_pause.setEnabled(False)
        btn_row.addWidget(self.btn_pause)

        self.btn_resume = QPushButton("⏵ Retomar")
        self.btn_resume.clicked.connect(self._resume_sending)
        self.btn_resume.setEnabled(False)
        btn_row.addWidget(self.btn_resume)

        self.btn_stop = QPushButton("⏹ Parar")
        self.btn_stop.setProperty("destructive", True)
        self.btn_stop.clicked.connect(self._stop_sending)
        self.btn_stop.setEnabled(False)
        btn_row.addWidget(self.btn_stop)

        controls_layout.addLayout(btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        controls_layout.addWidget(self.progress_bar)

        self.label_progress = QLabel("Aguardando início...")
        controls_layout.addWidget(self.label_progress)

        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        layout.addStretch()
        return widget

    def _send_test_email(self):
        """Envia e-mail de teste em background (P1-1)."""
        test_email = self.input_test_email.text().strip()
        if not test_email:
            QMessageBox.warning(self, "Atenção", "Informe um e-mail de teste.")
            return

        if self.df_clean is None or self.df_clean.empty:
            QMessageBox.warning(self, "Atenção", "Importe contatos primeiro.")
            return

        config = self._get_smtp_config()
        if not config["email"] or not config["password"]:
            QMessageBox.warning(self, "Atenção", "Configure o SMTP primeiro.")
            return

        test_contact = self.df_clean.iloc[0].to_dict()
        test_contact["EMail"] = test_email
        test_contact["Nome"] = "Teste"
        
        subject = render_template(self.input_subject.text(), test_contact)
        html = render_template(self.editor.to_html(), test_contact)
        text = render_template(self.editor.to_plain_text(), test_contact)

        self.btn_send_test.setEnabled(False)
        self.btn_send_test.setText("Enviando...")
        self.status_bar.showMessage("Enviando e-mail de teste...")
        
        self.test_email_worker = TestEmailWorker(
            config, test_email, "Teste", subject, html, text
        )
        self.test_email_worker.finished.connect(self._on_test_email_finished)
        self.test_email_worker.start()

    def _on_test_email_finished(self, success: bool, message: str):
        """Callback do envio de teste."""
        self.btn_send_test.setEnabled(True)
        self.btn_send_test.setText("Enviar Teste")
        
        if success:
            QMessageBox.information(self, "Sucesso", f"E-mail de teste enviado. {message}")
            self.status_bar.showMessage("E-mail de teste enviado com sucesso.")
        else:
            QMessageBox.critical(self, "Falha", message)
            self.status_bar.showMessage("Falha no envio do e-mail de teste.")

    def _start_sending(self):
        if self.df_clean is None or self.df_clean.empty:
            QMessageBox.warning(self, "Atenção", "Nenhum contato válido. Importe e processe os dados.")
            return

        if not self.input_subject.text() or not self.editor.to_plain_text().strip():
            QMessageBox.warning(self, "Atenção", "Preencha o assunto e o corpo da mensagem.")
            return

        # Validação de variáveis
        missing_subject = validate_variables(self.input_subject.text(), list(self.df_clean.columns))
        missing_body = validate_variables(self.editor.to_plain_text(), list(self.df_clean.columns))
        missing = set(missing_subject + missing_body)
        if missing:
            reply = QMessageBox.question(
                self, "Variáveis inválidas",
                f"As seguintes variáveis não existem na planilha:\n{', '.join(missing)}\n\n"
                f"Elas serão substituídas pelo fallback '{FALLBACK_NOME}'.\n\n"
                f"Deseja continuar mesmo assim?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        config = self._get_smtp_config()
        if not config["email"] or not config["password"]:
            QMessageBox.warning(self, "Atenção", "Configure e teste o SMTP primeiro.")
            return

        # Validação de intervalos
        min_interval = self.spin_min_interval.value()
        max_interval = self.spin_max_interval.value()
        if min_interval > max_interval:
            QMessageBox.warning(self, "Atenção", "O intervalo mínimo não pode ser maior que o máximo.")
            return

        self.smtp_config = config
        self.logger = CampaignLogger()

        contacts_list = self.df_clean.to_dict(orient="records")

        self.worker = SenderWorker(
            contacts=contacts_list,
            subject=self.input_subject.text(),
            html_body=self.editor.to_html(),
            text_body=self.editor.to_plain_text(),
            smtp_config=self.smtp_config,
            daily_limit=self.spin_daily_limit.value(),
            min_interval=min_interval,
            max_interval=max_interval
        )

        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.log_updated.connect(self._on_log_updated)
        self.worker.status_changed.connect(self._on_status_changed)
        self.worker.finished_sending.connect(self._on_finished_sending)
        self.worker.error_occurred.connect(self._on_error_occurred)

        # Atualiza bandeja
        if self.update_manager:
            self.update_manager.set_sending_active(True)
        if self.tray_icon and self.pause_resume_action:
            self.pause_resume_action.setEnabled(True)

        self._set_sending_ui_state(True)
        self.worker.start()
        
        # Oculta para bandeja (Parte 3B)
        if self.tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            self.tray_icon.showMessage(
                APP_TITLE,
                "Disparo iniciado. O aplicativo continuará em segundo plano.",
                QSystemTrayIcon.Information,
                3000
            )

    def _pause_sending(self):
        if self.worker:
            self.worker.pause()
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(True)
            if self.pause_resume_action:
                self.pause_resume_action.setText("Retomar")

    def _resume_sending(self):
        if self.worker:
            self.worker.resume()
            self.btn_pause.setEnabled(True)
            self.btn_resume.setEnabled(False)
            if self.pause_resume_action:
                self.pause_resume_action.setText("Pausar")

    def _stop_sending(self):
        if self.worker:
            self.worker.stop()

    def _set_sending_ui_state(self, sending: bool):
        self.btn_start.setEnabled(not sending)
        self.btn_pause.setEnabled(sending)
        self.btn_resume.setEnabled(False)
        self.btn_stop.setEnabled(sending)

    def _on_progress_updated(self, sent: int, failed: int, remaining: int, estimated_time: float):
        total = sent + failed + remaining
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(sent + failed)
        
        # Formata tempo estimado
        if estimated_time > 0:
            minutes = int(estimated_time // 60)
            seconds = int(estimated_time % 60)
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = "calculando..."
        
        self.label_progress.setText(
            f"Enviados: {sent} | Falhas: {failed} | Restantes: {remaining} | Tempo estimado: {time_str}"
        )
        
        # Atualiza bandeja
        if self.tray_icon:
            self.tray_icon.setToolTip(f"{APP_TITLE}: {sent}/{total} enviados")
        if self.status_action:
            self.status_action.setText(f"Status: {sent} enviados / {failed} falhas / {remaining} restantes")

    def _on_log_updated(self, entry: dict):
        if self.logger:
            self.logger.log_entry(entry)

        # Atualiza tabela de log na UI (P1-5: 6 colunas)
        row_count = self.log_table.rowCount()
        self.log_table.insertRow(row_count)
        self.log_table.setItem(row_count, 0, QTableWidgetItem(entry.get("data_hora", "")))
        self.log_table.setItem(row_count, 1, QTableWidgetItem(entry.get("codigo", "")))
        self.log_table.setItem(row_count, 2, QTableWidgetItem(entry.get("destinatario", "")))
        self.log_table.setItem(row_count, 3, QTableWidgetItem(entry.get("nome", "")))
        
        status_item = QTableWidgetItem(entry.get("status", ""))
        status = entry.get("status", "")
        if status == "ENVIADO":
            status_item.setForeground(QColor("#2E7D32"))
        elif status == "FALHA":
            status_item.setForeground(QColor("#D32F2F"))
        self.log_table.setItem(row_count, 4, status_item)
        
        self.log_table.setItem(row_count, 5, QTableWidgetItem(entry.get("erro", "")))
        self.log_table.scrollToBottom()

    def _on_status_changed(self, status: str):
        self.status_bar.showMessage(status)

    def _on_finished_sending(self, summary: dict):
        self._set_sending_ui_state(False)
        self.progress_bar.setValue(self.progress_bar.maximum())
        
        # Atualiza bandeja
        if self.update_manager:
            self.update_manager.set_sending_active(False)
        if self.tray_icon and self.pause_resume_action:
            self.pause_resume_action.setEnabled(False)
            self.pause_resume_action.setText("Pausar")
        
        # Envia relatório em background (P0-9)
        if self.logger:
            self.report_worker = ReportWorker(self.logger, summary, self.smtp_config)
            self.report_worker.finished.connect(self._on_report_finished)
            self.report_worker.start()
        
        # Notificação na bandeja (Parte 3B)
        if self.tray_icon and self.isHidden():
            self.tray_icon.showMessage(
                APP_TITLE,
                f"Disparo finalizado.\nEnviados: {summary['sent']} | Falhas: {summary['failed']}",
                QSystemTrayIcon.Information,
                5000
            )
            # Reabre a janela na aba Log
            self.show_from_tray()
            self.tabs.setCurrentIndex(4)  # Aba Log
        else:
            QMessageBox.information(
                self, "Disparo Finalizado",
                f"Total: {summary['total']}\n"
                f"Enviados: {summary['sent']}\n"
                f"Falhas: {summary['failed']}\n"
                f"Restantes: {summary['remaining']}"
            )

    def _on_report_finished(self, success: bool, message: str):
        """Callback do envio do relatório."""
        if success:
            self.status_bar.showMessage("Relatório enviado para o TI com sucesso.")
        else:
            self.status_bar.showMessage(f"Falha ao enviar relatório: {message}")

    def _on_error_occurred(self, error: str):
        if self.isHidden() and self.tray_icon:
            self.tray_icon.showMessage(
                APP_TITLE,
                f"Erro no disparo: {error}",
                QSystemTrayIcon.Warning,
                5000
            )
            self.show_from_tray()
            self.tabs.setCurrentIndex(4)
        else:
            QMessageBox.critical(self, "Erro de Envio", error)

    # ==========================================================================
    # ABA 5: LOG (P1-5)
    # ==========================================================================
    def _create_log_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Botão para abrir pasta de logs
        btn_layout = QHBoxLayout()
        btn_open_logs = QPushButton("Abrir pasta de logs")
        btn_open_logs.clicked.connect(self._open_logs_folder)
        btn_layout.addWidget(btn_open_logs)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.log_table = QTableWidget()
        self.log_table.setColumnCount(6)
        self.log_table.setHorizontalHeaderLabels(["Data/Hora", "Código", "Destinatário", "Nome", "Status", "Erro"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.setAlternatingRowColors(True)
        layout.addWidget(self.log_table)

        return widget

    def _open_logs_folder(self):
        """Abre a pasta de logs no explorador de arquivos."""
        if os.path.exists(LOGS_DIR):
            os.startfile(LOGS_DIR)
        else:
            QMessageBox.information(self, "Aviso", "A pasta de logs ainda não existe.")

    # ==========================================================================
    # ATUALIZAÇÃO (Parte 4E)
    # ==========================================================================
    def _manual_check_update(self):
        """Verificação manual de atualização."""
        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("Verificando...")
        self.status_bar.showMessage("Verificando atualização...")
        
        if self.update_manager:
            self.update_manager.start_check()
            # Conecta temporariamente para mostrar resultado
            if self.update_manager.checker:
                self.update_manager.checker.no_update.connect(self._show_no_update_message)
                self.update_manager.checker.check_failed.connect(self._show_check_failed_message)

    def _show_no_update_message(self, remote_version: str):
        """Mostra mensagem de que está atualizado."""
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("Verificar atualização")
        self.status_bar.showMessage("Verificação concluída.")
        QMessageBox.information(self, "Atualização", f"Você já está na versão mais recente ({remote_version}).")

    def _show_check_failed_message(self, reason: str):
        """Mostra mensagem de falha na verificação."""
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("Verificar atualização")
        self.status_bar.showMessage("Falha na verificação de atualização.")
        QMessageBox.warning(self, "Atualização", f"Não foi possível verificar atualizações:\n{reason}")

    def _on_update_available(self, remote: str, local: str):
        """Mostra a faixa de atualização (Parte 4E)."""
        self.update_label.setText(f"Nova versão {remote} disponível (instalada: {local})")
        self.update_banner.setVisible(True)
        self.update_manager.on_update_available(remote, local)
        
        # Desconecta sinais temporários de verificação manual
        if self.update_manager.checker:
            try:
                self.update_manager.checker.no_update.disconnect(self._show_no_update_message)
                self.update_manager.checker.check_failed.disconnect(self._show_check_failed_message)
            except Exception:
                pass

    def _on_no_update(self, remote: str):
        """Esconde a faixa de atualização."""
        self.update_banner.setVisible(False)
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("Verificar atualização")

    def _on_update_now(self):
        """Inicia a atualização (Parte 4E)."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(
                self, "Atualização",
                "Há um envio em andamento. A atualização será oferecida novamente ao final do disparo."
            )
            return
        
        reply = QMessageBox.question(
            self, "Confirmar atualização",
            f"O aplicativo será fechado e a pasta de instalação será atualizada.\n"
            f"Seus dados (logs, templates, estado e credenciais) serão preservados.\n\n"
            f"Deseja continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.update_manager.apply_update()
            if success:
                QMessageBox.information(self, "Atualização", message)
                QApplication.quit()
            else:
                QMessageBox.critical(self, "Erro", message)

    def _on_update_later(self):
        """Adia a atualização."""
        self.update_banner.setVisible(False)
        self.update_manager.clear_pending()