# ==============================================================================
# CONFIGURAÇÕES GLOBAIS - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Este arquivo centraliza todas as constantes, limites e configurações do sistema.
# Altere os valores aqui para refletir em todo o aplicativo.

import os
import sys

# ------------------------------------------------------------------------------
# 1. LIMITES E SEGURANÇA (ANTI-BLOQUEIO DE SMTP)
# ------------------------------------------------------------------------------
# Limite rígido de e-mails por dia por conta de remetente.
# O aplicativo bloqueará o botão "Iniciar" e exibirá aviso se este valor for
# excedido ou se o usuário tentar configurá-lo acima deste teto.
MAX_DAILY_LIMIT = 200

# Limite padrão sugerido para o campo de entrada na interface (caso o usuário
# queira enviar menos para aquecer a conta gradualmente).
DEFAULT_DAILY_LIMIT = 200

# Intervalo padrão entre envios (em segundos) para evitar bloqueio por spam.
# O sistema sorteará um valor aleatório entre MIN e MAX a cada e-mail.
MIN_INTERVAL_SECONDS = 10
MAX_INTERVAL_SECONDS = 30

# ------------------------------------------------------------------------------
# 2. SERVIDORES SMTP SUPORTADOS
# ------------------------------------------------------------------------------
# Dicionário com as configurações dos provedores.
# Chave: Nome amigável exibido na interface.
# Valor: Dicionário com host, portas e tipo de segurança.
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

# ------------------------------------------------------------------------------
# 3. RELATÓRIO E LOGS
# ------------------------------------------------------------------------------
# E-mail para onde o relatório final (com o CSV de logs em anexo) será enviado
# automaticamente ao final de cada disparo ou ao parar o processo.
REPORT_EMAIL = "ti@didier.com.br"

# ------------------------------------------------------------------------------
# 4. CAMINHOS DE DIRETÓRIOS E ARQUIVOS
# ------------------------------------------------------------------------------
# Obtém o diretório raiz do projeto (onde este arquivo está dentro de 'app/')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Caminhos das pastas principais
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Arquivo de estado persistente (controla o limite diário e o índice de retomada)
APP_STATE_FILE = os.path.join(BASE_DIR, "app_state.json")

# Arquivo de logo (usado na interface)
LOGO_FILE = os.path.join(ASSETS_DIR, "logo.png")

# Ícone do aplicativo (usado na bandeja e janelas)
ICON_FILE = os.path.join(ASSETS_DIR, "icon.ico")

# ------------------------------------------------------------------------------
# 5. VARIÁVEIS DE SUBSTITUIÇÃO (TEMPLATES)
# ------------------------------------------------------------------------------
# Fallback padrão quando uma variável (ex: {{primeiro_nome}}) não é encontrada
# ou está vazia na planilha.
FALLBACK_NOME = "Revendedor(a)"

# Mapeamento de variáveis especiais que não dependem apenas do nome da coluna
SPECIAL_VARIABLES = {
    "primeiro_nome": "primeiro_nome",
    "nome_completo": "nome_completo",
    "email": "email",
    "codigorevendedor": "codigorevendedor"
}

# ------------------------------------------------------------------------------
# 6. INFORMAÇÕES DA INTERFACE
# ------------------------------------------------------------------------------
APP_TITLE = "Disparador de E-mails CP Fani"
APP_VERSION = "1.0.0"