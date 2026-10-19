# ==============================================================================
# COMPONENTES DE INTERFACE - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Widgets customizados para a interface gráfica, incluindo o Editor de Texto Rico
# com suporte a imagens inline (via arquivo local e colar) e a Tabela de
# Pré-visualização de Contatos.

import os
import re
import json
import time
import shutil
from typing import Tuple, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QToolBar, QTableView,
    QLabel, QFileDialog, QPushButton, QComboBox, QFontComboBox, QSpinBox,
    QColorDialog, QHeaderView, QAbstractItemView, QMessageBox, QInputDialog
)
from PySide6.QtGui import (
    QAction, QIcon, QFont, QTextCursor, QImage, QClipboard, QKeySequence,
    QTextCharFormat, QColor, QBrush, QTextBlockFormat, QDesktopServices,
)
from PySide6.QtCore import Qt, QUrl, QAbstractTableModel, QModelIndex, QMimeData

from app.config import ASSETS_DIR, LOGO_FILE, TEMPLATES_DIR


# ==============================================================================
# 1. EDITOR DE TEXTO RICO COM SUPORTE A IMAGENS
# ==============================================================================

class ImageTextEdit(QTextEdit):
    """
    QTextEdit customizado que suporta colar imagens via Ctrl+V.
    As imagens coladas são salvas em uma pasta temporária e referenciadas
    como arquivos locais para o fluxo de CID do SMTPClient.
    """
    def __init__(self, temp_images_dir: str, parent=None):
        super().__init__(parent)
        self.temp_images_dir = temp_images_dir
        os.makedirs(temp_images_dir, exist_ok=True)

    def canInsertFromMimeData(self, source: QMimeData) -> bool:
        """Verifica se o MIME data contém uma imagem."""
        if source.hasImage():
            return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source: QMimeData):
        """Insere a imagem do clipboard, salvando-a temporariamente."""
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage):
                # Gerar nome único baseado em timestamp
                timestamp = int(time.time() * 1000)
                filename = f"pasted_{timestamp}.png"
                filepath = os.path.join(self.temp_images_dir, filename)
                
                # Salvar imagem como PNG
                if image.save(filepath, "PNG"):
                    # Inserir no editor com caminho file://
                    abs_path = os.path.abspath(filepath).replace("\\", "/")
                    if not abs_path.startswith("/"):
                        abs_path = "/" + abs_path
                    
                    cursor = self.textCursor()
                    cursor.insertHtml(
                        f'<img src="file://{abs_path}" alt="imagem" '
                        f'style="max-width:100%; height:auto;"><br>'
                    )
                    return
        
        # Se não for imagem, comporta-se normalmente
        super().insertFromMimeData(source)


class RichTextEditor(QWidget):
    """
    Editor de texto rico com barra de ferramentas e suporte a imagens inline.
    Suporta colar imagens (Ctrl+V), inserir via botão, e salvar/carregar
    modelos com cópia automática de imagens para pasta dedicada.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # Pasta temporária para imagens coladas/inseridas durante edição
        self.temp_images_dir = os.path.join(TEMPLATES_DIR, "_temp_editor_imgs")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Barra de ferramentas de formatação
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(self.toolbar.iconSize())

        # Fonte e tamanho
        self.font_combo = QFontComboBox()
        self.font_combo.setToolTip("Família da fonte")
        self.font_combo.currentFontChanged.connect(self._change_font)
        self.toolbar.addWidget(self.font_combo)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 72)
        self.size_spin.setValue(12)
        self.size_spin.setToolTip("Tamanho da fonte")
        self.size_spin.valueChanged.connect(self._change_font_size)
        self.toolbar.addWidget(self.size_spin)

        self.toolbar.addSeparator()

        # Formatação de texto
        self._add_action("Negrito", self._toggle_bold, QKeySequence.Bold, checkable=True, tooltip="Negrito (Ctrl+B)")
        self._add_action("Itálico", self._toggle_italic, QKeySequence.Italic, checkable=True, tooltip="Itálico (Ctrl+I)")
        self._add_action("Sublinhado", self._toggle_underline, QKeySequence.Underline, checkable=True, tooltip="Sublinhado (Ctrl+U)")
        
        self.toolbar.addSeparator()

        # Cor do texto
        self.color_action = QAction("Cor do Texto", self)
        self.color_action.setToolTip("Alterar cor do texto")
        self.color_action.triggered.connect(self._change_text_color)
        self.toolbar.addAction(self.color_action)

        self.toolbar.addSeparator()

        # Alinhamento
        self._add_action("Esquerda", lambda: self._set_alignment(Qt.AlignLeft), tooltip="Alinhar à esquerda")
        self._add_action("Centro", lambda: self._set_alignment(Qt.AlignCenter), tooltip="Centralizar")
        self._add_action("Direita", lambda: self._set_alignment(Qt.AlignRight), tooltip="Alinhar à direita")
        self._add_action("Justificado", lambda: self._set_alignment(Qt.AlignJustify), tooltip="Justificar")

        self.toolbar.addSeparator()

        # Links e Imagens
        self._add_action("Inserir Link", self._insert_link, tooltip="Inserir hyperlink")
        self._add_action("Inserir Imagem", self._insert_image, tooltip="Inserir imagem do arquivo")

        layout.addWidget(self.toolbar)

        # Área de edição de texto (usando ImageTextEdit para suporte a colar)
        self.text_edit = ImageTextEdit(self.temp_images_dir)
        self.text_edit.setAcceptRichText(True)
        self.text_edit.setPlaceholderText(
            "Digite o corpo do e-mail aqui...\n\n"
            "Use {{primeiro_nome}} para personalizar.\n"
            "Você pode colar imagens diretamente com Ctrl+V."
        )
        
        layout.addWidget(self.text_edit)

    def _add_action(self, text: str, callback, shortcut=None, checkable=False, tooltip=""):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.setCheckable(checkable)
        if tooltip:
            action.setToolTip(tooltip)
        action.triggered.connect(callback)
        self.toolbar.addAction(action)
        return action

    def _change_font(self, font: QFont):
        self.text_edit.setFontFamily(font.family())

    def _change_font_size(self, size: int):
        self.text_edit.setFontPointSize(size)

    def _toggle_bold(self, checked):
        self.text_edit.setFontWeight(QFont.Bold if checked else QFont.Normal)

    def _toggle_italic(self, checked):
        self.text_edit.setFontItalic(checked)

    def _toggle_underline(self, checked):
        self.text_edit.setFontUnderline(checked)

    def _change_text_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.text_edit.setTextColor(color)

    def _set_alignment(self, alignment):
        self.text_edit.setAlignment(alignment)

    def _insert_link(self):
        cursor = self.text_edit.textCursor()
        selection = cursor.selectedText()
        url, ok = QInputDialog.getText(self, "Inserir Link", "URL (ex: https://exemplo.com):")
        if ok and url:
            if selection:
                cursor.insertHtml(f'<a href="{url}">{selection}</a>')
            else:
                cursor.insertHtml(f'<a href="{url}">{url}</a>')

    def _insert_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Imagem", "", 
            "Imagens (*.png *.jpg *.jpeg *.gif *.bmp);;Todos os arquivos (*)"
        )
        if file_path:
            self._add_image_to_editor(file_path)

    def _add_image_to_editor(self, file_path: str):
        """Insere a imagem no editor usando um caminho local absoluto."""
        abs_path = os.path.abspath(file_path).replace("\\", "/")
        if not abs_path.startswith("/"):
            abs_path = "/" + abs_path
        
        cursor = self.text_edit.textCursor()
        cursor.insertHtml(
            f'<img src="file://{abs_path}" alt="imagem" '
            f'style="max-width:100%; height:auto;"><br>'
        )

    def to_html(self) -> str:
        """Retorna o conteúdo do editor como HTML."""
        return self.text_edit.toHtml()

    def from_html(self, html: str):
        """Carrega HTML no editor."""
        self.text_edit.setHtml(html)

    def to_plain_text(self) -> str:
        """Retorna o conteúdo como texto puro (para fallback de e-mail)."""
        return self.text_edit.toPlainText()

    # -------------------------------------------------------------------------
    # MÉTODOS DE SALVAR/CARREGAR MODELOS (P1-7)
    # -------------------------------------------------------------------------

    def _sanitize_template_name(self, name: str) -> str:
        """
        Sanitiza o nome do modelo para uso em arquivos/pastas.
        Remove caracteres inválidos e substitui por underscore.
        """
        safe_name = re.sub(r'[^\w\-]', '_', name)
        safe_name = re.sub(r'_+', '_', safe_name)  # Remove underscores duplicados
        safe_name = safe_name.strip('_')
        return safe_name or "modelo_sem_nome"

    def _copy_images_to_template_dir(self, html_content: str, template_imgs_dir: str) -> str:
        """
        Extrai imagens do HTML (src="file://..."), copia para a pasta do template
        e reescreve os caminhos como relativos.
        Retorna o HTML modificado.
        """
        os.makedirs(template_imgs_dir, exist_ok=True)
        
        # Regex para encontrar src="file://..." ou src='file://...'
        pattern = re.compile(r'(<img[^>]*?\bsrc=["\'])(file://[^"\']+)(["\'][^>]*>)', re.IGNORECASE)

        def replacer(match):
            prefix = match.group(1)
            file_url = match.group(2)
            suffix = match.group(3)
            
            # Extrair caminho do file://
            file_path = file_url[7:]  # Remove "file://"
            if file_path.startswith("/"):
                file_path = file_path[1:]
            
            # Normalizar para o sistema operacional
            file_path = os.path.normpath(file_path)
            
            if os.path.exists(file_path):
                # Copiar imagem para pasta do template
                filename = os.path.basename(file_path)
                dest_path = os.path.join(template_imgs_dir, filename)
                
                # Se já existir, adicionar timestamp
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(filename)
                    timestamp = int(time.time() * 1000)
                    filename = f"{base}_{timestamp}{ext}"
                    dest_path = os.path.join(template_imgs_dir, filename)
                
                try:
                    shutil.copy2(file_path, dest_path)
                    # Reescrever como caminho relativo
                    return f'{prefix}imgs/{filename}{suffix}'
                except Exception:
                    pass  # Se falhar, mantém o caminho original
            
            return match.group(0)

        return pattern.sub(replacer, html_content)

    def _rewrite_relative_paths_to_absolute(self, html_content: str, template_imgs_dir: str) -> str:
        """
        Reescreve caminhos relativos (imgs/...) para absolutos (file://...).
        Usado ao carregar um modelo.
        """
        pattern = re.compile(r'(<img[^>]*?\bsrc=["\'])(imgs/[^"\']+)(["\'][^>]*>)', re.IGNORECASE)

        def replacer(match):
            prefix = match.group(1)
            relative_path = match.group(2)
            suffix = match.group(3)
            
            # Construir caminho absoluto
            filename = relative_path[5:]  # Remove "imgs/"
            abs_path = os.path.join(template_imgs_dir, filename)
            
            if os.path.exists(abs_path):
                abs_path_normalized = os.path.abspath(abs_path).replace("\\", "/")
                if not abs_path_normalized.startswith("/"):
                    abs_path_normalized = "/" + abs_path_normalized
                return f'{prefix}file://{abs_path_normalized}{suffix}'
            
            return match.group(0)

        return pattern.sub(replacer, html_content)

    def save_template(self, template_name: str, subject: str) -> Tuple[bool, str]:
        """
        Salva o modelo atual, copiando imagens para pasta dedicada.
        Retorna (Sucesso, Mensagem).
        """
        if not template_name:
            return False, "Nome do modelo não pode ser vazio."
        
        safe_name = self._sanitize_template_name(template_name)
        
        # Criar pasta de imagens do template
        template_imgs_dir = os.path.join(TEMPLATES_DIR, f"{safe_name}_imgs")
        
        # Copiar imagens e reescrever HTML
        html_content = self.to_html()
        html_with_relative = self._copy_images_to_template_dir(html_content, template_imgs_dir)
        
        # Salvar JSON
        data = {
            "subject": subject,
            "html": html_with_relative
        }
        
        filepath = os.path.join(TEMPLATES_DIR, f"{safe_name}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True, f"Modelo '{template_name}' salvo com sucesso."
        except Exception as e:
            return False, f"Erro ao salvar modelo: {str(e)}"

    def load_template(self, template_name: str) -> Tuple[bool, str, str]:
        """
        Carrega o modelo, reescrevendo caminhos relativos para absolutos.
        Retorna (Sucesso, Assunto, HTML).
        """
        safe_name = self._sanitize_template_name(template_name)
        filepath = os.path.join(TEMPLATES_DIR, f"{safe_name}.json")
        
        if not os.path.exists(filepath):
            return False, "", ""
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            subject = data.get("subject", "")
            html = data.get("html", "")
            
            # Reescrever caminhos relativos para absolutos
            template_imgs_dir = os.path.join(TEMPLATES_DIR, f"{safe_name}_imgs")
            html_absolute = self._rewrite_relative_paths_to_absolute(html, template_imgs_dir)
            
            return True, subject, html_absolute
        except Exception as e:
            return False, "", ""

    def list_templates(self) -> list:
        """Lista todos os modelos salvos (nomes sem extensão)."""
        if not os.path.exists(TEMPLATES_DIR):
            return []
        
        templates = []
        for filename in os.listdir(TEMPLATES_DIR):
            if filename.endswith(".json"):
                templates.append(filename[:-5])  # Remove ".json"
        
        return sorted(templates)


# ==============================================================================
# 2. TABELA DE PRÉ-VISUALIZAÇÃO DE CONTATOS
# ==============================================================================

class ContactsTableModel(QAbstractTableModel):
    """Modelo de dados para a tabela de contatos."""
    def __init__(self, df=None):
        super().__init__()
        self.df = df
        self.headers = []
        if df is not None:
            self.headers = list(df.columns)

    def rowCount(self, parent=QModelIndex()):
        return len(self.df) if self.df is not None else 0

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or self.df is None:
            return None
        
        if role == Qt.DisplayRole:
            value = self.df.iloc[index.row(), index.column()]
            return str(value) if value is not None else ""
        
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return None

    def update_data(self, df):
        self.beginResetModel()
        self.df = df
        self.headers = list(df.columns) if df is not None else []
        self.endResetModel()


class ContactsTableView(QWidget):
    """Widget com tabela de contatos e estatísticas."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Labels de estatísticas
        self.stats_label = QLabel("Nenhum dado carregado.")
        self.stats_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(self.stats_label)

        # Tabela
        self.table_view = QTableView()
        self.table_model = ContactsTableModel()
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.table_view)

    def load_data(self, df, stats: dict):
        """Carrega o DataFrame e atualiza as estatísticas."""
        self.table_model.update_data(df)
        
        # Ajusta o tamanho das colunas ao conteúdo
        self.table_view.resizeColumnsToContents()
        
        # Atualiza o label de estatísticas
        if stats:
            total = stats.get('total_linhas', 0)
            validos = stats.get('validos', 0)
            sem_email = stats.get('sem_email', 0)
            invalidos = stats.get('email_invalido', 0)
            duplicados = stats.get('duplicados', 0)
            
            self.stats_label.setText(
                f"Total de linhas: {total} | Válidos: {validos} | "
                f"Sem e-mail: {sem_email} | Inválidos: {invalidos} | "
                f"Duplicados: {duplicados}"
            )
        else:
            self.stats_label.setText("Nenhum dado carregado.")

    def clear(self):
        """Limpa a tabela e as estatísticas."""
        self.table_model.update_data(None)
        self.stats_label.setText("Nenhum dado carregado.")