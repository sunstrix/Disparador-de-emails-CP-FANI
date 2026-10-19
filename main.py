# ==============================================================================
# PONTO DE ENTRADA - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Inicializa a aplicação Qt, configura metadados e exibe a janela principal.
# Este arquivo é compatível com execução direta (python main.py) e com
# empacotamento futuro via PyInstaller.

import sys
import os
import traceback
from datetime import datetime

# Garante que o diretório raiz do projeto esteja no PYTHONPATH
if getattr(sys, 'frozen', False):
    # Se estiver rodando como executável (PyInstaller)
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Se estiver rodando como script Python
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QLockFile
from PySide6.QtGui import QIcon
from app.config import APP_TITLE, APP_VERSION, LOGS_DIR, LOGO_FILE

def exception_hook(exc_type, exc_value, exc_tb):
    """
    Hook global para capturar exceções não tratadas.
    Loga o erro em LOGS_DIR/crash.log e mostra diálogo de erro (se possível).
    """
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    os.makedirs(LOGS_DIR, exist_ok=True)
    crash_log = os.path.join(LOGS_DIR, "crash.log")
    
    try:
        with open(crash_log, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"[{timestamp}] Exceção não tratada:\n")
            f.write(error_msg)
            f.write(f"{'='*80}\n")
    except Exception:
        pass
    
    app = QApplication.instance()
    if app and not getattr(app, '_is_closing', False):
        try:
            QMessageBox.critical(
                None,
                "Erro Crítico",
                f"Ocorreu um erro inesperado:\n\n{exc_value}\n\n"
                f"O detalhe foi salvo em:\n{crash_log}"
            )
        except Exception:
            pass
    
    sys.__excepthook__(exc_type, exc_value, exc_tb)

# Instala o hook global de exceções no nível do módulo
sys.excepthook = exception_hook

def main():
    """Função principal que inicializa e executa a aplicação."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Instância única via QLockFile
    lock_file_path = os.path.join(LOGS_DIR, "app.lock")
    lock_file = QLockFile(lock_file_path)
    lock_file.setStaleLockTime(0)
    
    if not lock_file.tryLock(100):
        QMessageBox.warning(
            None,
            "Aplicativo já em execução",
            f"O {APP_TITLE} já está em execução.\n\n"
            "Verifique a bandeja do sistema (perto do relógio) ou feche a instância anterior."
        )
        sys.exit(0)
    
    app.setApplicationName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("CP Fani")
    # REMOVIDO: app.setOrganizationDomain conforme regra de memória do projeto
    
    if os.path.exists(LOGO_FILE):
        app.setWindowIcon(QIcon(LOGO_FILE))
    
    from app.ui.main_window import MainWindow
    
    window = MainWindow()
    window.show()
    
    def on_about_to_quit():
        app._is_closing = True
        if lock_file.isLocked():
            lock_file.unlock()
    
    app.aboutToQuit.connect(on_about_to_quit)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()