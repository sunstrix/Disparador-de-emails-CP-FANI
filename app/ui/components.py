# ==============================================================================
# COMPONENTES DE INTERFACE - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Widgets customizados para a interface gráfica, incluindo o Editor de Texto Rico
# com suporte a imagens inline e a Tabela de Pré-visualização de Contatos.

import os
import tempfile
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QToolBar, QTableView,
    QLabel, QFileDialog, QPushButton, QComboBox, QFontComboBox, QSpinBox,
    QColorDialog, QHeaderView, QAbstractItemView
)
from PySide6.QtGui import (
    QAction, QIcon, QFont, QTextCursor, QImage, QClipboard, QKeySequence,
    QTextCharFormat, QColor, QBrush, QTextBlockFormat, QDesktopServices
)
from PySide6.QtCore import Qt, QUrl, QAbstractTableModel, QModelIndex

from app.config import ASSETS_DIR, LOGO_FILE

# ==============================================================================
# 1. EDITOR DE TEXTO RICO COM SUPORTE A IMAGENS
# ==============================================================================
class RichTextEditor(QWidget):
    """Editor de texto rico com barra de ferramentas e suporte a imagens inline."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.temp_images_dir = tempfile.mkdtemp(prefix="cpfani_imgs_")
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
        self.font_combo.currentFontChanged.connect(self._change_font)
        self.toolbar.addWidget(self.font_combo)
        
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 72)
        self.size_spin.setValue(12)
        self.size_spin.valueChanged.connect(self._change_font_size)
        self.toolbar.addWidget(self.size_spin)
        
        self.toolbar.addSeparator()
        
        # Formatação de texto
        self._add_action("Negrito", self._toggle_bold, QKeySequence.Bold, checkable=True)
        self._add_action("Itálico", self._toggle_italic, QKeySequence.Italic, checkable=True)
        self._add_action("Sublinhado", self._toggle_underline, QKeySequence.Underline, checkable=True)
        
        self.toolbar.addSeparator()
        
        # Cor do texto
        self.color_action = QAction("Cor do Texto", self)
        self.color_action.triggered.connect(self._change_text_color)
        self.toolbar.addAction(self.color_action)
        
        self.toolbar.addSeparator()
        
        # Alinhamento
        self._add_action("Esquerda", lambda: self._set_alignment(Qt.AlignLeft))
        self._add_action("Centro", lambda: self._set_alignment(Qt.AlignCenter))
        self._add_action("Direita", lambda: self._set_alignment(Qt.AlignRight))
        self._add_action("Justificado", lambda: self._set_alignment(Qt.AlignJustify))
        
        self.toolbar.addSeparator()
        
        # Links e Imagens
        self._add_action("Inserir Link", self._insert_link)
        self._add_action("Inserir Imagem", self._insert_image)
        
        layout.addWidget(self.toolbar)
        
        # Área de edição de texto
        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(True)
        self.text_edit.setPlaceholderText("Digite o corpo do e-mail aqui... Use {{primeiro_nome}} para personalizar.")
        layout.addWidget(self.text_edit)
        
    def _add_action(self, text: str, callback, shortcut=None, checkable=False):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.setCheckable(checkable)
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
        from PySide6.QtWidgets import QInputDialog
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
        # Normaliza o caminho para formato file://
        abs_path = os.path.abspath(file_path).replace("\\", "/")
        if not abs_path.startswith("/"):
            abs_path = "/" + abs_path
            
        cursor = self.text_edit.textCursor()
        cursor.insertHtml(f'<img src="file://{abs_path}" alt="imagem" style="max-width:100%;"><br>')
        
    def to_html(self) -> str:
        """Retorna o conteúdo do editor como HTML."""
        return self.text_edit.toHtml()
        
    def from_html(self, html: str):
        """Carrega HTML no editor."""
        self.text_edit.setHtml(html)
        
    def to_plain_text(self) -> str:
        """Retorna o conteúdo como texto puro (para fallback de e-mail)."""
        return self.text_edit.toPlainText()

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