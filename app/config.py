# ==============================================================================
# CONFIGURAÇÕES GLOBAIS - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Este arquivo centraliza todas as constantes, limites e configurações do sistema.
# Altere os valores aqui para refletir em todo o aplicativo.

import os
import sys
import shutil

def resource_path(relative_path: str) -> str:
    """
    Obtém o caminho absoluto para o recurso.
    Funciona tanto em desenvolvimento quanto empacotado com PyInstaller.
    """
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em sys._MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Diretório do código
if getattr(sys, 'frozen', False):
    CODE_DIR = os.path.dirname(sys.executable)
else:
    CODE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Modo Desenvolvimento: ativado somente via variável CPFANI_DEV=1 ou presença da pasta .git
IS_DEV = os.environ.get("CPFANI_DEV") == "1" or os.path.exists(os.path.join(CODE_DIR, ".git"))

# Lógica para DATA_DIR (dados graváveis do usuário: logs, templates, app_state.json)
# Em ambiente de produção/instalação, armazena SEMPRE em %LOCALAPPDATA%\CPFani
if IS_DEV:
    DATA_DIR = CODE_DIR
else:
    local_app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~/.local/share'))
    DATA_DIR = os.path.join(local_app_data, 'CPFani')

# ==============================================================================
# 1. LIMITES E SEGURANÇA (ANTI-BLOQUEIO DE SMTP)
# ==============================================================================
# Limite rígido de e-mails por dia por conta de remetente.
MAX_DAILY_LIMIT = 200

# Limite padrão sugerido para o campo de entrada na interface.
DEFAULT_DAILY_LIMIT = 200

# Intervalo padrão entre envios (em segundos) para evitar bloqueio por spam.
MIN_INTERVAL_SECONDS = 10
MAX_INTERVAL_SECONDS = 30

# ==============================================================================
# 2. SERVIDORES SMTP SUPORTADOS
# ==============================================================================
SMTP_SERVERS = {
    "Gmail": {
        "host": "smtp.gmail.com",
        "ports": {
            "STARTTLS (587)": {"port": 587, "security": "STARTTLS"},
            "SSL (465)": {"port": 465, "security": "SSL"}
        },
        "warning": "Atenção: O Gmail exige o uso de 'Senha de App' (gerada nas configurações de segurança da sua conta Google). A senha normal não funcionará."
    },
    "GoDaddy": {
        "host": "smtpout.secureserver.net",
        "ports": {
            "SSL (465)": {"port": 465, "security": "SSL"},
            "STARTTLS (587)": {"port": 587, "security": "STARTTLS"}
        },
        "warning": "O GoDaddy possui limites de envio diário mais restritivos que o Gmail. Verifique o limite do seu plano específico."
    }
}

# ==============================================================================
# 3. RELATÓRIO E LOGS
# ==============================================================================
REPORT_EMAIL = "ti@didier.com.br"

# ==============================================================================
# 4. CAMINHOS DE DIRETÓRIOS E ARQUIVOS
# ==============================================================================
# Recursos somente leitura
LOGO_FILE = resource_path(os.path.join("logo", "logo.png"))
ICON_FILE = resource_path(os.path.join("ico", "icone.ico"))
ASSETS_DIR = os.path.dirname(LOGO_FILE)
VERSION_FILE = resource_path("version.txt")

# Dados graváveis (apontam para DATA_DIR em %LOCALAPPDATA%\CPFani)
LOGS_DIR = os.path.join(DATA_DIR, "logs")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")
APP_STATE_FILE = os.path.join(DATA_DIR, "app_state.json")

def _migrate_old_data():
    """
    Migração única: se existirem logs, templates ou app_state.json dentro da pasta de
    instalação (de versões anteriores), move os arquivos para %LOCALAPPDATA%\CPFani
    sem sobrescrever o que já existir lá.
    """
    if IS_DEV or CODE_DIR == DATA_DIR:
        return

    items_to_migrate = ["logs", "templates", "app_state.json"]
    for item in items_to_migrate:
        src = os.path.join(CODE_DIR, item)
        dst = os.path.join(DATA_DIR, item)

        if not os.path.exists(src):
            continue

        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            if os.path.isdir(src):
                os.makedirs(dst, exist_ok=True)
                for file_name in os.listdir(src):
                    src_file = os.path.join(src, file_name)
                    dst_file = os.path.join(dst, file_name)
                    if os.path.isfile(src_file) and not os.path.exists(dst_file):
                        shutil.move(src_file, dst_file)
                if not os.listdir(src):
                    os.rmdir(src)
            elif os.path.isfile(src) and not os.path.exists(dst):
                shutil.move(src, dst)
        except Exception:
            pass

def init_data_dir():
    """
    Inicializa a estrutura de diretórios graváveis sob demanda ou no startup,
    evitando efeitos colaterais de I/O na simples importação do módulo.
    """
    _migrate_old_data()
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)

# ==============================================================================
# 5. VARIÁVEIS DE SUBSTITUIÇÃO (TEMPLATES)
# ==============================================================================
FALLBACK_NOME = "Revendedor(a)"

SPECIAL_VARIABLES = {
    "primeiro_nome": "primeiro_nome",
    "nome_completo": "nome_completo",
    "email": "email",
    "codigorevendedor": "codigorevendedor"
}

# ==============================================================================
# 6. INFORMAÇÕES DA INTERFACE
# ==============================================================================
APP_TITLE = "Disparador de E-mails CP Fani"

def get_app_version() -> str:
    """Lê a versão do arquivo version.txt, com suporte a utf-8-sig e fallback '1.0.0'."""
    try:
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, 'r', encoding='utf-8-sig') as f:
                version = f.read().replace('\ufeff', '').strip()
                if version:
                    return version
    except Exception:
        pass
    return "1.0.0"

APP_VERSION = get_app_version()