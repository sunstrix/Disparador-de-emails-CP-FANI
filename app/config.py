# ==============================================================================
# CONFIGURAÇÕES GLOBAIS - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Este arquivo centraliza todas as constantes, limites e configurações do sistema.
# Altere os valores aqui para refletir em todo o aplicativo.

import os
import sys

def resource_path(relative_path):
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

# Diretório do código (para verificação de permissão de escrita)
if getattr(sys, 'frozen', False):
    CODE_DIR = os.path.dirname(sys.executable)
else:
    CODE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Lógica para DATA_DIR (dados graváveis: logs, templates, app_state.json)
# Se estiver empacotado (frozen) ou se o diretório de código não for gravável, usa LOCALAPPDATA
if getattr(sys, 'frozen', False) or not os.access(CODE_DIR, os.W_OK):
    local_app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~/.local/share'))
    DATA_DIR = os.path.join(local_app_data, 'CPFani')
else:
    DATA_DIR = CODE_DIR

# Garantir que o diretório de dados exista
os.makedirs(DATA_DIR, exist_ok=True)

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
# Recursos somente leitura (usando resource_path para compatibilidade com PyInstaller)
LOGO_FILE = resource_path(os.path.join("logo", "logo.png"))
ICON_FILE = resource_path(os.path.join("ico", "icone.ico"))
VERSION_FILE = resource_path("version.txt")

# Dados graváveis (apontam para DATA_DIR, protegido contra PermissionError em C:\)
LOGS_DIR = os.path.join(DATA_DIR, "logs")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")
APP_STATE_FILE = os.path.join(DATA_DIR, "app_state.json")

# Garantir existência das subpastas de dados
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

def get_app_version():
    """Lê a versão do arquivo version.txt, com fallback para '1.0.0'."""
    try:
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                version = f.read().strip()
                if version:
                    return version
    except Exception:
        pass
    return "1.0.0"

APP_VERSION = get_app_version()