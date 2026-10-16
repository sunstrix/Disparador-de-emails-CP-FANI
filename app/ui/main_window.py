# ==============================================================================
# JANELA PRINCIPAL - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Interface gráfica principal com abas para configuração SMTP, importação de
# contatos, editor de mensagens, controle de envio e visualização de logs.

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, QFileDialog,
    QMessageBox, QSpinBox, QProgressBar, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QGroupBox, QFormLayout,
    QMenu, QStatusBar, QApplication
)
from PySide6.QtGui import QPixmap, QIcon, QAction, QFont
from PySide6.QtCore import Qt, QTimer

import keyring

from app.config import (
    APP_TITLE, APP_VERSION, MAX_DAILY_LIMIT, DEFAULT_DAILY_LIMIT,
    MIN_INTERVAL_SECONDS, MAX_INTERVAL_SECONDS, SMTP_SERVERS,
    REPORT_EMAIL, LOGO_FILE, FALLBACK_NOME
)
from app.core.importer import load_contacts, process_contacts
from app.core.template_engine import render_template, validate_variables
from app.core.smtp_client import SMTPClient
from app.core.sender_worker import SenderWorker
from app.core.logger import CampaignLogger
from app.ui.components import RichTextEditor, ContactsTableView

KEYRING_SERVICE = "DisparadorCPFani"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} v{APP_VERSION}")
        self.resize(1100, 750)

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

        self._init_ui()
        self._load_smtp_credentials()

    # ==========================================================================
    # INICIALIZAÇÃO DA INTERFACE
    # ==========================================================================
    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Cabeçalho com Logo
        header_layout = QHBoxLayout()
        self.logo_label = QLabel()
        self.logo_label.setFixedHeight(60)
        self.logo_label.setAlignment(Qt.AlignCenter)
        self._load_logo()
        header_layout.addWidget(self.logo_label)

        self.title_label = QLabel(APP_TITLE)
        self.title_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.title_label)
        main_layout.addLayout(header_layout)

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

        main_layout.addWidget(self.tabs)

        # Barra de status
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Pronto. Configure o SMTP para começar.")

    def _load_logo(self):
        if os.path.exists(LOGO_FILE):
            pixmap = QPixmap(LOGO_FILE)
            if not pixmap.isNull():
                self.logo_label.setPixmap(pixmap.scaledToHeight(60, Qt.SmoothTransformation))
                return
        self.logo_label.setText("CP FANI")
        self.logo_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.logo_label.setStyleSheet("color: #2e7d32;")

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
        saved_email = keyring.get_password(KEYRING_SERVICE, "email")
        if saved_email:
            self.input_email.setText(saved_email)
            self.chk_remember.setChecked(True)

    def _save_smtp_credentials(self):
        if self.chk_remember.isChecked():
            keyring.set_password(KEYRING_SERVICE, "email", self.input_email.text())
            keyring.set_password(KEYRING_SERVICE, "password", self.input_password.text())
        else:
            keyring.delete_password(KEYRING_SERVICE, "email")
            keyring.delete_password(KEYRING_SERVICE, "password")

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
        config = self._get_smtp_config()
        if not config["email"] or not config["password"]:
            QMessageBox.warning(self, "Atenção", "Preencha o e-mail e a senha.")
            return

        self.btn_test_connection.setEnabled(False)
        self.btn_test_connection.setText("Testando...")
        QApplication.processEvents()

        try:
            client = SMTPClient(
                provider=config["provider"],
                email=config["email"],
                password=config["password"],
                port=config["port"],
                security=config["security"]
            )
            success, message = client.test_connection()
            if success:
                QMessageBox.information(self, "Sucesso", message)
                self._save_smtp_credentials()
                self.smtp_config = config
            else:
                QMessageBox.critical(self, "Falha", message)
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
        finally:
            self.btn_test_connection.setEnabled(True)
            self.btn_test_connection.setText("Testar Conexão")

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
        self.btn_process.clicked.connect(self._process_contacts)
        map_layout.addRow("", self.btn_process)

        map_group.setLayout(map_layout)
        layout.addWidget(map_group)

        # Tabela de pré-visualização
        self.contacts_table = ContactsTableView()
        layout.addWidget(self.contacts_table, 1)

        return widget

    def _import_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Planilha", "",
            "Planilhas (*.xlsx *.xls *.csv);;Todos os arquivos (*)"
        )
        if not file_path:
            return

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
        self.status_bar.showMessage(f"Arquivo carregado: {os.path.basename(file_path)}")

    def _on_sheet_changed(self, sheet_name: str):
        if not self.current_file_path or not sheet_name:
            return
        df, result = load_contacts(self.current_file_path, sheet_name)
        if result["success"]:
            self.df_raw = df
            self.detected_columns = result["detected_columns"]
            self._update_column_combos()

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
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Salvar Modelo", "Nome do modelo:")
        if ok and name:
            templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
            os.makedirs(templates_dir, exist_ok=True)
            data = {
                "subject": self.input_subject.text(),
                "html": self.editor.to_html()
            }
            filepath = os.path.join(templates_dir, f"{name}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Sucesso", f"Modelo '{name}' salvo.")

    def _load_template(self):
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
        if not os.path.exists(templates_dir):
            QMessageBox.information(self, "Aviso", "Nenhum modelo salvo ainda.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Carregar Modelo", templates_dir, "Modelos (*.json)"
        )
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.input_subject.setText(data.get("subject", ""))
            self.editor.from_html(data.get("html", ""))

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

        try:
            client = SMTPClient(
                provider=config["provider"],
                email=config["email"],
                password=config["password"],
                port=config["port"],
                security=config["security"]
            )
            success, message = client.send_email(test_email, "Teste", subject, html, text)
            if success:
                QMessageBox.information(self, "Sucesso", f"E-mail de teste enviado para {test_email}")
            else:
                QMessageBox.critical(self, "Falha", message)
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

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
            QMessageBox.warning(
                self, "Variáveis inválidas",
                f"As seguintes variáveis não existem na planilha:\n{', '.join(missing)}\n\nElas serão substituídas pelo fallback."
            )

        config = self._get_smtp_config()
        if not config["email"] or not config["password"]:
            QMessageBox.warning(self, "Atenção", "Configure e teste o SMTP primeiro.")
            return

        self.smtp_config = config
        self.logger = CampaignLogger()

        contacts_list = self.df_clean.to_dict(orient="records")

        self.worker = SenderWorker(
            contacts=contacts_list,
            subject=self.input_subject.text(),
            html_body=self.editor.to_html(),
            text_body=self.editor.to_plain_text(),
            smtp_config=self.smtp_config
        )

        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.log_updated.connect(self._on_log_updated)
        self.worker.status_changed.connect(self._on_status_changed)
        self.worker.finished_sending.connect(self._on_finished_sending)
        self.worker.error_occurred.connect(self._on_error_occurred)

        self._set_sending_ui_state(True)
        self.worker.start()

    def _pause_sending(self):
        if self.worker:
            self.worker.pause()
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(True)

    def _resume_sending(self):
        if self.worker:
            self.worker.resume()
            self.btn_pause.setEnabled(True)
            self.btn_resume.setEnabled(False)

    def _stop_sending(self):
        if self.worker:
            self.worker.stop()

    def _set_sending_ui_state(self, sending: bool):
        self.btn_start.setEnabled(not sending)
        self.btn_pause.setEnabled(sending)
        self.btn_resume.setEnabled(False)
        self.btn_stop.setEnabled(sending)

    def _on_progress_updated(self, sent: int, failed: int, remaining: int):
        total = sent + failed + remaining
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(sent + failed)
        self.label_progress.setText(
            f"Enviados: {sent} | Falhas: {failed} | Restantes: {remaining}"
        )

    def _on_log_updated(self, entry: dict):
        if self.logger:
            self.logger.log_entry(entry)

        # Atualiza tabela de log na UI
        row_count = self.log_table.rowCount()
        self.log_table.insertRow(row_count)
        self.log_table.setItem(row_count, 0, QTableWidgetItem(entry.get("data_hora", "")))
        self.log_table.setItem(row_count, 1, QTableWidgetItem(entry.get("codigo", "")))
        self.log_table.setItem(row_count, 2, QTableWidgetItem(entry.get("destinatario", "")))
        self.log_table.setItem(row_count, 3, QTableWidgetItem(entry.get("status", "")))
        self.log_table.scrollToBottom()

    def _on_status_changed(self, status: str):
        self.status_bar.showMessage(status)

    def _on_finished_sending(self, summary: dict):
        self._set_sending_ui_state(False)
        self.progress_bar.setValue(self.progress_bar.maximum())

        QMessageBox.information(
            self, "Disparo Finalizado",
            f"Total: {summary['total']}\n"
            f"Enviados: {summary['sent']}\n"
            f"Falhas: {summary['failed']}\n"
            f"Restantes: {summary['remaining']}"
        )

        # Envia relatório para o TI
        if self.logger:
            success, msg = self.logger.send_final_report(summary, self.smtp_config)
            if success:
                self.status_bar.showMessage("Relatório enviado para o TI com sucesso.")
            else:
                self.status_bar.showMessage(f"Falha ao enviar relatório: {msg}")

    def _on_error_occurred(self, error: str):
        QMessageBox.critical(self, "Erro de Envio", error)

    # ==========================================================================
    # ABA 5: LOG
    # ==========================================================================
    def _create_log_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.log_table = QTableWidget()
        self.log_table.setColumnCount(4)
        self.log_table.setHorizontalHeaderLabels(["Data/Hora", "Código", "Destinatário", "Status"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.setAlternatingRowColors(True)

        layout.addWidget(self.log_table)
        return widget