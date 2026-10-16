# ==============================================================================
# ESTILOS (QSS) - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Centraliza todo o tema visual da aplicação.
# Paleta baseada em verde institucional, com hierarquia clara de botões e
# feedback visual para estados (hover, disabled, erro).
# Para alterar o tema, basta modificar as constantes de cor abaixo.

# ------------------------------------------------------------------------------
# PALETA DE CORES (fácil de trocar)
# ------------------------------------------------------------------------------
COLOR_PRIMARY = "#2E7D32"        # Verde institucional (botão primário, abas ativas)
COLOR_PRIMARY_HOVER = "#1B5E20"  # Verde mais escuro para hover
COLOR_PRIMARY_DISABLED = "#A5D6A7"
COLOR_DESTRUCTIVE = "#D32F2F"    # Vermelho para ações destrutivas (Parar)
COLOR_DESTRUCTIVE_HOVER = "#B71C1C"
COLOR_SECONDARY = "#455A64"      # Cinza azulado para botões secundários
COLOR_SECONDARY_HOVER = "#263238"
COLOR_BG = "#F5F5F5"             # Fundo geral
COLOR_SURFACE = "#FFFFFF"        # Fundo de cartões, tabelas, inputs
COLOR_BORDER = "#E0E0E0"         # Bordas sutis
COLOR_TEXT = "#212121"           # Texto principal
COLOR_TEXT_SECONDARY = "#757575" # Texto secundário
COLOR_ERROR = "#D32F2F"          # Borda de erro / texto de erro
COLOR_SUCCESS = "#2E7D32"        # Status sucesso na tabela
COLOR_WARNING = "#F57C00"        # Status aviso

def get_stylesheet() -> str:
    """Retorna o QSS completo da aplicação."""
    return f"""
    /* ======================================================================
       GERAL
       ====================================================================== */
    QMainWindow, QWidget {{
        background-color: {COLOR_BG};
        color: {COLOR_TEXT};
        font-family: "Segoe UI", "Inter", "Roboto", "Arial", sans-serif;
        font-size: 10pt;
    }}

    QLabel {{
        color: {COLOR_TEXT};
        background: transparent;
    }}

    QLabel#title_label {{
        font-size: 18pt;
        font-weight: bold;
        color: {COLOR_PRIMARY};
    }}

    QLabel#version_label {{
        font-size: 9pt;
        color: {COLOR_TEXT_SECONDARY};
    }}

    /* ======================================================================
       INPUTS (QLineEdit, QComboBox, QSpinBox, QTextEdit)
       ====================================================================== */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        padding: 6px 8px;
        min-height: 24px;
        selection-background-color: {COLOR_PRIMARY};
        selection-color: white;
    }}

    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border: 1px solid {COLOR_PRIMARY};
    }}

    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
        background-color: #EEEEEE;
        color: {COLOR_TEXT_SECONDARY};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {COLOR_TEXT_SECONDARY};
        margin-right: 8px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        selection-background-color: {COLOR_PRIMARY};
        selection-color: white;
        outline: none;
    }}

    QTextEdit {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        padding: 8px;
    }}

    QTextEdit:focus {{
        border: 1px solid {COLOR_PRIMARY};
    }}

    /* Validação visual de erro (aplicar via setProperty("error", True)) */
    QLineEdit[error="true"], QComboBox[error="true"] {{
        border: 1px solid {COLOR_ERROR};
        background-color: #FFEBEE;
    }}

    /* ======================================================================
       BOTÕES (Hierarquia: Primário, Secundário, Destrutivo)
       ====================================================================== */
    QPushButton {{
        background-color: {COLOR_SECONDARY};
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        min-height: 24px;
        font-weight: 500;
    }}

    QPushButton:hover {{
        background-color: {COLOR_SECONDARY_HOVER};
    }}

    QPushButton:pressed {{
        background-color: #1C313A;
    }}

    QPushButton:disabled {{
        background-color: #BDBDBD;
        color: #EEEEEE;
    }}

    /* Botão Primário (Iniciar, Salvar, Confirmar) */
    QPushButton#primary, QPushButton[primary="true"] {{
        background-color: {COLOR_PRIMARY};
    }}

    QPushButton#primary:hover, QPushButton[primary="true"]:hover {{
        background-color: {COLOR_PRIMARY_HOVER};
    }}

    QPushButton#primary:disabled, QPushButton[primary="true"]:disabled {{
        background-color: {COLOR_PRIMARY_DISABLED};
        color: white;
    }}

    /* Botão Destrutivo (Parar, Excluir) */
    QPushButton#destructive, QPushButton[destructive="true"] {{
        background-color: {COLOR_DESTRUCTIVE};
    }}

    QPushButton#destructive:hover, QPushButton[destructive="true"]:hover {{
        background-color: {COLOR_DESTRUCTIVE_HOVER};
    }}

    /* Botão Secundário Claro (outline) */
    QPushButton#outline {{
        background-color: transparent;
        color: {COLOR_PRIMARY};
        border: 1px solid {COLOR_PRIMARY};
    }}

    QPushButton#outline:hover {{
        background-color: #E8F5E9;
    }}

    /* ======================================================================
       ABAS (QTabWidget)
       ====================================================================== */
    QTabWidget::pane {{
        border: 1px solid {COLOR_BORDER};
        border-top: none;
        background-color: {COLOR_SURFACE};
        border-radius: 0 0 4px 4px;
    }}

    QTabBar::tab {{
        background-color: #EEEEEE;
        color: {COLOR_TEXT_SECONDARY};
        border: 1px solid {COLOR_BORDER};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 8px 20px;
        margin-right: 2px;
        font-weight: 500;
    }}

    QTabBar::tab:selected {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_PRIMARY};
        border-bottom: 2px solid {COLOR_PRIMARY};
    }}

    QTabBar::tab:hover:!selected {{
        background-color: #E0E0E0;
        color: {COLOR_TEXT};
    }}

    /* ======================================================================
       TABELAS (QTableWidget)
       ====================================================================== */
    QTableWidget {{
        background-color: {COLOR_SURFACE};
        alternate-background-color: #FAFAFA;
        gridline-color: {COLOR_BORDER};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        selection-background-color: #E8F5E9;
        selection-color: {COLOR_TEXT};
    }}

    QTableWidget::item {{
        padding: 4px 8px;
    }}

    QHeaderView::section {{
        background-color: #EEEEEE;
        color: {COLOR_TEXT};
        padding: 6px 8px;
        border: none;
        border-right: 1px solid {COLOR_BORDER};
        border-bottom: 1px solid {COLOR_BORDER};
        font-weight: bold;
    }}

    QHeaderView::section:last {{
        border-right: none;
    }}

    /* Células com status (aplicar via foregroundRole ou item.setForeground) */
    /* Verde para ENVIADO, Vermelho para FALHA (será aplicado via código) */

    /* ======================================================================
       BARRA DE PROGRESSO
       ====================================================================== */
    QProgressBar {{
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        background-color: #EEEEEE;
        text-align: center;
        color: {COLOR_TEXT};
        font-weight: bold;
        min-height: 20px;
    }}

    QProgressBar::chunk {{
        background-color: {COLOR_PRIMARY};
        border-radius: 3px;
    }}

    /* ======================================================================
       GRUPOS (QGroupBox)
       ====================================================================== */
    QGroupBox {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 16px;
        font-weight: bold;
        color: {COLOR_TEXT};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        background-color: {COLOR_SURFACE};
        color: {COLOR_PRIMARY};
    }}

    /* ======================================================================
       CHECKBOX E RADIO
       ====================================================================== */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        color: {COLOR_TEXT};
    }}

    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {COLOR_BORDER};
        border-radius: 3px;
        background-color: {COLOR_SURFACE};
    }}

    QRadioButton::indicator {{
        border-radius: 9px;
    }}

    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background-color: {COLOR_PRIMARY};
        border-color: {COLOR_PRIMARY};
        image: none;
    }}

    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
        border-color: {COLOR_PRIMARY};
    }}

    /* ======================================================================
       SCROLLBARS
       ====================================================================== */
    QScrollBar:vertical {{
        background-color: {COLOR_BG};
        width: 10px;
        margin: 0;
        border-radius: 5px;
    }}

    QScrollBar::handle:vertical {{
        background-color: #BDBDBD;
        min-height: 30px;
        border-radius: 5px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: #9E9E9E;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        background-color: {COLOR_BG};
        height: 10px;
        margin: 0;
        border-radius: 5px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: #BDBDBD;
        min-width: 30px;
        border-radius: 5px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: #9E9E9E;
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ======================================================================
       STATUS BAR
       ====================================================================== */
    QStatusBar {{
        background-color: {COLOR_SURFACE};
        border-top: 1px solid {COLOR_BORDER};
        color: {COLOR_TEXT_SECONDARY};
        font-size: 9pt;
    }}

    QStatusBar::item {{
        border: none;
    }}

    /* ======================================================================
       MENUS E TOOLTIPS
       ====================================================================== */
    QMenu {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 6px 24px;
        border-radius: 2px;
    }}

    QMenu::item:selected {{
        background-color: #E8F5E9;
        color: {COLOR_PRIMARY};
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {COLOR_BORDER};
        margin: 4px 8px;
    }}

    QToolTip {{
        background-color: #424242;
        color: white;
        border: none;
        border-radius: 3px;
        padding: 4px 8px;
        font-size: 9pt;
    }}

    /* ======================================================================
       SPLITER E LINHAS
       ====================================================================== */
    QSplitter::handle {{
        background-color: {COLOR_BORDER};
    }}

    QSplitter::handle:horizontal {{
        width: 1px;
    }}

    QSplitter::handle:vertical {{
        height: 1px;
    }}

    Line, QFrame[frameShape="4"], QFrame[frameShape="5"] {{
        color: {COLOR_BORDER};
        max-height: 1px;
    }}
    """