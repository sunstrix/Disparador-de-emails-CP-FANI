# ==============================================================================
# CLIENTE SMTP - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Responsável pela conexão segura, montagem de mensagens MIME multipart/related
# (com suporte a imagens inline via CID) e tratamento de erros de rede.

import smtplib
import ssl
import os
import re
import mimetypes
import time
import urllib.parse
from typing import Dict, Tuple, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.header import Header
from email.utils import formataddr, formatdate, make_msgid

from app.config import SMTP_SERVERS


class SMTPClient:
    def __init__(
        self, 
        provider: str, 
        email: str, 
        password: str, 
        port: int, 
        security: str,
        reply_to: Optional[str] = None,
        list_unsubscribe: Optional[str] = None
    ):
        self.provider = provider
        self.email = email
        self.password = password
        self.port = port
        self.security = security
        self.reply_to = reply_to
        self.list_unsubscribe = list_unsubscribe
        self.server_config = SMTP_SERVERS.get(provider)
        
        if not self.server_config:
            raise ValueError(f"Provedor '{provider}' não suportado.")
            
        self.server: Optional[smtplib.SMTP] = None

    def connect(self) -> Tuple[bool, str]:
        """
        Estabelece a conexão com o servidor SMTP.
        Se já estiver conectado, verifica se a conexão está ativa (noop).
        Retorna (Sucesso: bool, Mensagem: str).
        """
        if self.server is not None:
            try:
                self.server.noop()
                return True, "Conexão já estabelecida e ativa."
            except Exception:
                # Conexão caiu, limpa para forçar reconexão
                self.server = None

        try:
            self.server = self._create_server()
            return True, "Conexão e autenticação bem-sucedidas!"
        except smtplib.SMTPAuthenticationError as e:
            code = getattr(e, 'smtp_code', 535)
            return False, f"Falha na autenticação (código {code}). Verifique seu e-mail e senha (Gmail exige 'Senha de App')."
        except smtplib.SMTPConnectError as e:
            return False, f"Falha ao conectar ao servidor: {e}"
        except Exception as e:
            return False, f"Erro inesperado: {str(e)}"

    def close(self):
        """Encerra a conexão com o servidor SMTP de forma segura."""
        if self.server is not None:
            try:
                self.server.quit()
            except Exception:
                pass  # Ignora erros ao fechar (ex: conexão já caída)
            finally:
                self.server = None

    def test_connection(self) -> Tuple[bool, str]:
        """Testa a conexão e autenticação com o servidor SMTP."""
        success, msg = self.connect()
        if success:
            self.close()
        return success, msg

    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_body: str,
        text_body: str,
        retry_count: int = 3
    ) -> Tuple[bool, str]:
        """
        Envia um e-mail com suporte a HTML, texto plano e imagens inline.
        Reutiliza a conexão ativa. Reconecta automaticamente em caso de queda.
        Classifica exceções por tipo/código SMTP (5xx permanente vs 4xx transitório).
        """
        last_error = ""
        for attempt in range(retry_count):
            try:
                # Garante que estamos conectados
                success, msg = self.connect()
                if not success:
                    last_error = msg
                    if "autenticação" in msg.lower() or "535" in msg:
                        return False, msg
                    
                    if attempt < retry_count - 1:
                        self._backoff_sleep(2 ** attempt)
                    continue

                # Monta e envia a mensagem
                msg_obj = self._build_message(to_email, to_name, subject, html_body, text_body)
                self.server.send_message(msg_obj)
                
                return True, "Enviado com sucesso"

            except smtplib.SMTPAuthenticationError as e:
                code = getattr(e, 'smtp_code', 535)
                msg_text = e.smtp_error.decode('utf-8', errors='replace') if isinstance(getattr(e, 'smtp_error', ''), bytes) else str(e)
                return False, f"Falha de autenticação ({code}): {msg_text}"

            except smtplib.SMTPRecipientsRefused as e:
                return False, f"E-mail do destinatário recusado pelo servidor: {e}"

            except smtplib.SMTPSenderRefused as e:
                return False, f"Endereço do remetente recusado pelo servidor: {e}"

            except smtplib.SMTPDataError as e:
                code = getattr(e, 'smtp_code', 500)
                msg_text = e.smtp_error.decode('utf-8', errors='replace') if isinstance(getattr(e, 'smtp_error', ''), bytes) else str(e)
                if 500 <= code < 600:
                    return False, f"Erro permanente do servidor ({code}): {msg_text}"
                last_error = f"Erro temporário do servidor ({code}): {msg_text}"
                self.server = None

            except smtplib.SMTPResponseException as e:
                code = getattr(e, 'smtp_code', 500)
                msg_text = e.smtp_error.decode('utf-8', errors='replace') if isinstance(getattr(e, 'smtp_error', ''), bytes) else str(e)
                if 500 <= code < 600:
                    return False, f"Erro permanente no servidor ({code}): {msg_text}"
                last_error = f"Erro no servidor ({code}): {msg_text}"
                self.server = None

            except (smtplib.SMTPServerDisconnected, OSError, ssl.SSLError, TimeoutError) as e:
                last_error = f"Falha na conexão SMTP: {str(e)}"
                self.server = None

            except Exception as e:
                last_error = f"Erro inesperado: {str(e)}"
                self.server = None

            if attempt < retry_count - 1:
                self._backoff_sleep(2 ** attempt)

        return False, f"Falha após {retry_count} tentativas: {last_error}"

    def _backoff_sleep(self, seconds: float):
        """Dorme em intervalos fracionados para evitar bloqueio estático prolongado."""
        steps = int(seconds * 10)
        for _ in range(steps):
            time.sleep(0.1)

    def _create_server(self) -> smtplib.SMTP:
        """Cria e autentica a conexão com o servidor SMTP com timeout estipulado em 30 segundos."""
        host = self.server_config["host"]
        
        if self.security == "SSL":
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, self.port, context=context, timeout=30)
        else:  # STARTTLS
            server = smtplib.SMTP(host, self.port, timeout=30)
            server.starttls(context=ssl.create_default_context())
            
        server.login(self.email, self.password)
        return server

    def _build_message(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> MIMEMultipart:
        """
        Monta a mensagem MIME multipart/related com fallback multipart/alternative.
        Extrai imagens do HTML e as anexa como inline (CID).
        """
        msg = MIMEMultipart("related")
        
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = formataddr(("CP Fani", self.email))
        msg["To"] = formataddr((to_name, to_email))
        msg["Date"] = formatdate(localtime=True)
        
        domain = self.email.split('@')[1] if '@' in self.email else "cp-fani.local"
        msg["Message-ID"] = make_msgid(domain=domain)
        
        if self.reply_to:
            msg["Reply-To"] = self.reply_to
        if self.list_unsubscribe:
            msg["List-Unsubscribe"] = f"<{self.list_unsubscribe}>"

        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(text_body, "plain", "utf-8"))
        
        html_processed, images = self._process_inline_images(html_body)
        alt_part.attach(MIMEText(html_processed, "html", "utf-8"))
        
        msg.attach(alt_part)

        for cid, img_path in images.items():
            if os.path.exists(img_path):
                with open(img_path, "rb") as f:
                    mime_type, _ = mimetypes.guess_type(img_path)
                    mime_type = mime_type or "application/octet-stream"
                    maintype, subtype = mime_type.split("/", 1)
                    
                    if maintype == "image":
                        img = MIMEImage(f.read(), _subtype=subtype)
                    else:
                        img = MIMEBase(maintype, subtype)
                        img.set_payload(f.read())
                        
                    img.add_header("Content-ID", f"<{cid}>")
                    img.add_header("Content-Disposition", "inline", filename=os.path.basename(img_path))
                    msg.attach(img)

        return msg

    def _process_inline_images(self, html_body: str) -> Tuple[str, Dict[str, str]]:
        """
        Procura por tags <img> com src local e as substitui por referências CID,
        ajustando a sintaxe da tag HTML e adicionando compatibilidade com Outlook.
        """
        path_to_cid = {}
        cid_to_path = {}
        
        pattern = re.compile(r'(<img[^>]*?\bsrc=["\'])([^"\']+)(["\'][^>]*>)', re.IGNORECASE)
        
        def replacer(match: re.Match) -> str:
            prefix = match.group(1)
            src = match.group(2)
            suffix = match.group(3)
            
            if src.startswith(("http://", "https://", "data:")):
                return match.group(0)
                
            clean_src = urllib.parse.unquote(src)
            
            if clean_src.startswith("file:///"):
                clean_src = clean_src[8:]
            elif clean_src.startswith("file://"):
                clean_src = clean_src[7:]
                
            clean_src = os.path.normpath(clean_src)
            
            if clean_src in path_to_cid:
                cid = path_to_cid[clean_src]
            else:
                cid = f"img_{len(path_to_cid) + 1}@cp-fani.local"
                path_to_cid[clean_src] = cid
                cid_to_path[cid] = clean_src

            if suffix.endswith("/>"):
                closing = "/>"
                attrs = suffix[:-2]
            elif suffix.endswith(">"):
                closing = ">"
                attrs = suffix[:-1]
            else:
                closing = ">"
                attrs = suffix

            attrs_lower = attrs.lower()
            extra_attrs = ""
            
            if "width=" not in attrs_lower:
                extra_attrs += ' width="100%"'
                
            if "style=" not in attrs_lower:
                extra_attrs += ' style="max-width: 100%; height: auto;"'
                
            new_suffix = f"{attrs}{extra_attrs}{closing}"
            return f'{prefix}cid:{cid}{new_suffix}'
        
        html_processed = pattern.sub(replacer, html_body)
        return html_processed, cid_to_path