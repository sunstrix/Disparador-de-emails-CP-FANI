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
# Isso é necessário para que os imports relativos funcionem corretamente
# quando o app é executado de qualquer diretório ou empacotado.
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

from app.config import APP_TITLE, APP_VERSION, ICON_FILE, DATA_DIR

def exception_hook(exc_type, exc_value, exc_tb):
    """
    Hook global para capturar exceções não tratadas.
    Loga o erro em DATA_DIR/crash.log e mostra diálogo de erro (se possível).
    """
    # Formata a mensagem de erro
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Loga em arquivo
    try:
        crash_log = os.path.join(DATA_DIR, "crash.log")
        with open(crash_log, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"[{timestamp}] Exceção não tratada:\n")
            f.write(error_msg)
            f.write(f"{'='*80}\n")
    except Exception:
        pass  # Se falhar ao logar, não pode fazer nada
    
    # Mostra diálogo de erro (apenas se QApplication ainda existir)
    app = QApplication.instance()
    if app and not getattr(app, '_is_closing', False):
        try:
            QMessageBox.critical(
                None,
                "Erro Crítico",
                f"Ocorreu um erro inesperado:\n\n{exc_value}\n\n"
                f"O detalhe foi salvo em:\n{crash_log if 'crash_log' in locals() else 'crash.log'}"
            )
        except Exception:
            pass  # Se falhar ao mostrar diálogo, continua
    
    # Chama o hook padrão (encerra o app)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

def main():
    """Função principal que inicializa e executa a aplicação."""
    
    # Instala o hook global de exceções (P1-11)
    sys.excepthook = exception_hook
    
    # Habilita alto DPI para telas de alta resolução
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Cria a aplicação Qt
    app = QApplication(sys.argv)
    
    # Instância única via QLockFile (P1-11)
    lock_file_path = os.path.join(DATA_DIR, "app.lock")
    lock_file = QLockFile(lock_file_path)
    lock_file.setStaleLockTime(0)  # Não remove lock antigo automaticamente
    
    if not lock_file.tryLock(100):
        # Já existe uma instância rodando
        QMessageBox.warning(
            None,
            "Aplicativo já em execução",
            f"O {APP_TITLE} já está em execução.\n\n"
            "Verifique a bandeja do sistema (perto do relógio) ou feche a instância anterior."
        )
        sys.exit(0)
    
    # Configura metadados da aplicação
    app.setApplicationName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("CP Fani")
    # setOrganizationDomain removido conforme confirmado (não usamos QSettings)
    
    # Define ícone da aplicação (P1-11)
    if os.path.exists(ICON_FILE):
        app_icon = QIcon(ICON_FILE)
        app.setWindowIcon(app_icon)
    
    # Cria e exibe a janela principal
    window = MainWindow()
    window.show()
    
    # Marca que o app está fechando (para evitar diálogos no excepthook durante shutdown)
    def on_about_to_quit():
        app._is_closing = True
        # Remove o lock file ao sair
        lock_file.unlock()
    
    app.aboutToQuit.connect(on_about_to_quit)
    
    # Inicia o loop de eventos
    sys.exit(app.exec())

if __name__ == "__main__":
    # Importa aqui para evitar circular import se main.py for importado
    from app.ui.main_window import MainWindow
    main()