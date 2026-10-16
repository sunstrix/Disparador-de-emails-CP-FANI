# ==============================================================================
# ATUALIZADOR AUTOMÁTICO - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Responsável por:
#   1) Verificar silenciosamente se existe nova versão no repositório (sem
#      bloquear a abertura do aplicativo - sempre executado em QThread).
#   2) Lançar o instalar_completo.bat com o argumento /atualizar, de forma
#      ELEVADA (UAC), sempre a partir da pasta de instalação travada.
#
# SEGURANÇA:
#   - Apenas HTTPS e apenas o repositório fixo abaixo.
#   - Payload limitado em tamanho e validado por regex estrita de versão.
#   - Nunca executa nada baixado: apenas lê um número de versão.
#   - A atualização NUNCA é aplicada sem confirmação explícita do usuário e
#     NUNCA enquanto houver envio em andamento (bloqueio programático).

import os
import re
import sys
import subprocess
from datetime import datetime
from typing import Optional, Tuple
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from PySide6.QtCore import QThread, Signal

from app.config import APP_VERSION, CODE_DIR, DATA_DIR

# ------------------------------------------------------------------------------
# CONSTANTES
# ------------------------------------------------------------------------------
# Fonte única e fixa da versão remota (HTTPS obrigatório).
UPDATE_CHECK_URL = (
    "https://raw.githubusercontent.com/"
    "sunstrix/Disparador-de-emails-CP-FANI/main/version.txt"
)

# Timeout curto: a verificação nunca pode travar a abertura do app.
NETWORK_TIMEOUT_SECONDS = 5

# Limite de tamanho do payload lido (512 bytes são mais que suficientes para
# uma string de versão; protege contra respostas abusivas).
MAX_VERSION_BYTES = 512

# Arquivo de log do updater (fica em DATA_DIR, fora da pasta travada).
UPDATER_LOG_FILE = os.path.join(DATA_DIR, "updater.log")

# Instalador completo (Parte 4-D) e seu argumento de atualização.
INSTALLER_FILENAME = "instalar_completo.bat"
UPDATE_ARGUMENT = "/atualizar"

# Formato aceito: 1 | 1.0 | 1.0.0 | 1.0.0.0 (somente dígitos e pontos).
VERSION_PATTERN = re.compile(r"^\d+(?:\.\d+){0,3}$")


# ------------------------------------------------------------------------------
# FUNÇÕES UTILITÁRIAS (testáveis isoladamente, sem Qt e sem rede)
# ------------------------------------------------------------------------------
def parse_version(raw: str) -> Optional[Tuple[int, ...]]:
    """
    Converte uma string de versão em tupla de inteiros para comparação correta.
    Ex: "1.10.0" -> (1, 10, 0)  e  "1.9.0" -> (1, 9, 0)
    Retorna None se o formato for inválido/malformado.
    """
    if not raw or not isinstance(raw, str):
        return None

    cleaned = raw.strip()
    if not VERSION_PATTERN.match(cleaned):
        return None

    try:
        return tuple(int(part) for part in cleaned.split("."))
    except (ValueError, TypeError):
        return None


def compare_versions(remote: str, local: str) -> Optional[int]:
    """
    Compara duas versões como tuplas de inteiros (nunca como string).
    Retorna:  1  se remote > local
               -1 se remote < local
                0 se iguais
               None se qualquer uma for malformada.
    """
    remote_t = parse_version(remote)
    local_t = parse_version(local)

    if remote_t is None or local_t is None:
        return None

    # Igualita os tamanhos para que "1.0" e "1.0.0" sejam considerados iguais.
    size = max(len(remote_t), len(local_t))
    remote_t = remote_t + (0,) * (size - len(remote_t))
    local_t = local_t + (0,) * (size - len(local_t))

    if remote_t > local_t:
        return 1
    if remote_t < local_t:
        return -1
    return 0


def is_newer(remote: str, local: str) -> bool:
    """
    True apenas se a versão remota for estritamente maior que a local.
    Versão malformada (de qualquer lado) é sempre tratada como "sem atualização".
    """
    result = compare_versions(remote, local)
    return result == 1


def fetch_remote_version(url: str = UPDATE_CHECK_URL) -> Tuple[bool, str]:
    """
    Baixa o conteúdo de version.txt do repositório fixo.
    Retorna (Sucesso: bool, Versão_ou_Motivo: str).
    Nunca lança exceção para fora: erros de rede viram (False, motivo).
    """
    # Garantia de segurança: apenas HTTPS no repositório oficial.
    if not url.startswith("https://raw.githubusercontent.com/sunstrix/"):
        return False, "URL de verificação não permitida."

    try:
        req = urlrequest.Request(
            url,
            headers={"User-Agent": "DisparadorCPFani-Updater/1.0"}
        )
        with urlrequest.urlopen(req, timeout=NETWORK_TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_VERSION_BYTES)

        text = raw.decode("utf-8", errors="replace").strip()

        if not text:
            return False, "version.txt remoto está vazio."

        # Remove possível BOM residual e quebras de linha extras.
        text = text.lstrip("\ufeff").splitlines()[0].strip()

        if parse_version(text) is None:
            return False, f"Versão remota malformada: '{text[:64]}'"

        return True, text

    except HTTPError as exc:
        return False, f"HTTP {exc.code} ao verificar versão."
    except URLError as exc:
        return False, f"Sem conexão ou host inacessível: {exc.reason}"
    except TimeoutError:
        return False, "Tempo esgotado ao verificar versão."
    except Exception as exc:
        return False, f"Erro inesperado na verificação: {exc}"


def write_log(message: str):
    """
    Registra eventos do updater em DATA_DIR/updater.log.
    Falha de escrita é silenciosa (log nunca pode quebrar o aplicativo).
    """
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(UPDATER_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {message}\n")
    except Exception:
        pass


def get_installer_path() -> str:
    """
    Retorna o caminho do instalar_completo.bat DENTRO da pasta de instalação
    (CODE_DIR). Por segurança, o app nunca executa instalador de outro local.
    """
    return os.path.join(CODE_DIR, INSTALLER_FILENAME)


def launch_self_update() -> Tuple[bool, str]:
    """
    Dispara o instalar_completo.bat com /atualizar de forma ELEVADA (UAC),
    usando a cópia travada dentro da pasta de instalação.

    Pré-condições (exigidas pela Parte 4-E):
      - O aplicativo deve ter confirmado a ação com o usuário.
      - Nenhum envio pode estar em andamento (verificado pelo chamador e
        também bloqueado programaticamente em UpdateManager).

    Retorna (Sucesso: bool, Mensagem: str).
    """
    if sys.platform != "win32":
        return False, "Atualização automática é suportada apenas no Windows."

    installer_path = get_installer_path()

    if not os.path.isfile(installer_path):
        write_log(f"Instalador não encontrado: {installer_path}")
        return False, (
            f"Instalador não encontrado em:\n{installer_path}\n\n"
            "Execute o instalar_completo.bat manualmente como administrador."
        )

    # Escape de aspas simples para o parser do PowerShell.
    ps_installer = installer_path.replace("'", "''")
    ps_workdir = CODE_DIR.replace("'", "''")
    ps_argument = UPDATE_ARGUMENT.replace("'", "''")

    ps_command = (
        f"Start-Process -FilePath '{ps_installer}' "
        f"-ArgumentList '{ps_argument}' "
        f"-Verb RunAs "
        f"-WorkingDirectory '{ps_workdir}'"
    )

    creation_flags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creation_flags = subprocess.CREATE_NO_WINDOW

    try:
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps_command,
            ],
            creationflags=creation_flags,
            close_fds=True,
        )
        write_log("Atualização solicitada: instalador elevado iniciado.")
        return True, (
            "Atualizador iniciado. O aplicativo será fechado e a pasta será "
            "atualizada. Seus dados (logs, templates, estado e credenciais) "
            "serão preservados."
        )
    except Exception as exc:
        write_log(f"Falha ao iniciar instalador: {exc}")
        return False, f"Falha ao iniciar o atualizador: {exc}"


# ------------------------------------------------------------------------------
# WORKER DE VERIFICAÇÃO (QThread) - NUNCA bloqueia a UI
# ------------------------------------------------------------------------------
class UpdateChecker(QThread):
    """
    Verifica a versão remota em segundo plano.
    Sinais:
      update_available(remote, local) -> há versão nova (UI mostra a FAIXA,
                                          nunca QMessageBox modal)
      no_update(remote)               -> já está atualizado
      check_failed(reason)            -> offline/erro (UI ignora em silêncio,
                                         apenas registra em updater.log)
    """

    update_available = Signal(str, str)
    no_update = Signal(str)
    check_failed = Signal(str)

    def __init__(self, local_version: str = APP_VERSION, parent=None):
        super().__init__(parent)
        self.local_version = local_version or "0.0.0"
        self._cancelled = False

    def cancel(self):
        """Solicita o cancelamento (ex: janela fechando)."""
        self._cancelled = True

    def run(self):
        try:
            success, payload = fetch_remote_version()

            if self._cancelled:
                return

            if not success:
                # Offline ou erro: comportamento é IGNORAR silenciosamente.
                write_log(f"Verificação ignorada: {payload}")
                self.check_failed.emit(payload)
                return

            if is_newer(payload, self.local_version):
                write_log(
                    f"Nova versão disponível: {payload} "
                    f"(instalada: {self.local_version})"
                )
                self.update_available.emit(payload, self.local_version)
            else:
                write_log(
                    f"Sem atualização. Remota: {payload} | "
                    f"Local: {self.local_version}"
                )
                self.no_update.emit(payload)

        except Exception as exc:
            write_log(f"Exceção no UpdateChecker: {exc}")
            self.check_failed.emit(str(exc))


# ------------------------------------------------------------------------------
# GERENCIADOR DE ATUALIZAÇÃO (regra de segurança: nunca durante envio)
# ------------------------------------------------------------------------------
class UpdateManager:
    """
    Coordena a verificação e o lançamento da atualização, garantindo a regra
    da Parte 4-E: NUNCA oferecer nem aplicar atualização com envio em
    andamento. O bloqueio é programático, não depende apenas da UI.
    """

    def __init__(self, local_version: str = APP_VERSION):
        self.local_version = local_version or "0.0.0"
        self.checker: Optional[UpdateChecker] = None
        self._sending_active = False
        self._pending_version: Optional[str] = None
        self._pending_local: Optional[str] = None

    # --- Controle de envio em andamento -------------------------------------
    def set_sending_active(self, active: bool):
        """
        Chamado pela UI ao iniciar/finalizar o disparo.
        Ao terminar um envio com atualização pendente, ela volta a ser oferecida.
        """
        self._sending_active = bool(active)

        if not self._sending_active and self._pending_version:
            write_log(
                f"Envio finalizado. Atualização pendente liberada: "
                f"{self._pending_version}"
            )

    @property
    def sending_active(self) -> bool:
        return self._sending_active

    # --- Verificação ---------------------------------------------------------
    def start_check(self):
        """Inicia a verificação assíncrona. Ignora se já estiver rodando."""
        if self.checker is not None and self.checker.isRunning():
            return

        self.checker = UpdateChecker(local_version=self.local_version)
        self.checker.start()

    def stop_check(self):
        """Cancela/encerra a verificação em andamento (usado no closeEvent)."""
        if self.checker is not None and self.checker.isRunning():
            self.checker.cancel()
            self.checker.wait(2000)

    def on_update_available(self, remote: str, local: str):
        """
        Registrado pela UI no sinal update_available.
        Guarda a versão pendente caso o envio esteja ativo (adiamento).
        """
        self._pending_version = remote
        self._pending_local = local

    def clear_pending(self):
        """Limpa a atualização pendente (usuário clicou em 'Depois')."""
        self._pending_version = None
        self._pending_local = None

    @property
    def pending_version(self) -> Optional[str]:
        return self._pending_version

    # --- Aplicação -----------------------------------------------------------
    def can_launch_update(self) -> Tuple[bool, str]:
        """
        Valida se a atualização pode ser aplicada agora.
        Retorna (Pode: bool, Motivo_se_nao_pode: str).
        """
        if self._sending_active:
            return False, (
                "Há um envio em andamento. A atualização será oferecida "
                "novamente ao final do disparo."
            )

        if not os.path.isfile(get_installer_path()):
            return False, (
                f"Instalador não encontrado em {get_installer_path()}. "
                "Atualize manualmente executando o instalar_completo.bat "
                "como administrador."
            )

        return True, ""

    def apply_update(self) -> Tuple[bool, str]:
        """
        Aplica a atualização. Deve ser chamada SOMENTE após confirmação
        explícita do usuário na interface.
        """
        allowed, reason = self.can_launch_update()
        if not allowed:
            write_log(f"Atualização bloqueada: {reason}")
            return False, reason

        success, message = launch_self_update()
        if success:
            self.clear_pending()
        return success, message