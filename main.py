# ==============================================================================
# PONTO DE ENTRADA - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Inicializa a aplicação Qt, configura metadados e exibe a janela principal.
# Este arquivo é compatível com execução direta (python main.py) e com
# empacotamento futuro via PyInstaller.

import sys
import os

# Garante que o diretório raiz do projeto esteja no PYTHONPATH
# Isso é necessário para que os imports relativos funcionem corretamente
# quando o app é executado de qualquer diretório ou empacotado.
if getattr(sys, 'frozen', False):
    # Se estiver rodando como executável (PyInstaller)
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Se estiver rodando como script Python
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.config import APP_TITLE, APP_VERSION
from app.ui.main_window import MainWindow

def main():
    """Função principal que inicializa e executa a aplicação."""
    
    # Habilita alto DPI para telas de alta resolução
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Cria a aplicação Qt
    app = QApplication(sys.argv)
    
    # Configura metadados da aplicação
    app.setApplicationName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("CP Fani")
    app.setOrganizationDomain("cpfani.com.br")
    
    # Cria e exibe a janela principal
    window = MainWindow()
    window.show()
    
    # Inicia o loop de eventos
    sys.exit(app.exec())

if __name__ == "__main__":
    main()