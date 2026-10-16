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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.header import Header
from email.utils import formataddr
from typing import Dict, Tuple

from app.config import SMTP_SERVERS

class SMTPClient:
    def __init__(self, provider: str, email: str, password: str, port: int, security: str):
        self.provider = provider
        self.email = email
        self.password = password
        self.port = port
        self.security = security
        self.server_config = SMTP_SERVERS.get(provider)
        
        if not self.server_config:
            raise ValueError(f"Provedor '{provider}' não suportado.")

    def test_connection(self) -> Tuple[bool, str]:
        """
        Testa a conexão e autenticação com o servidor SMTP.
        Retorna (Sucesso: bool, Mensagem: str).
        """
        try:
            server = self._create_server()
            server.quit()
            return True, "Conexão e autenticação bem-sucedidas!"
        except smtplib.SMTPAuthenticationError:
            return False, "Falha na autenticação. Verifique seu e-mail e senha (Gmail exige 'Senha de App')."
        except smtplib.SMTPConnectError as e:
            return False, f"Falha ao conectar ao servidor: {e}"
        except Exception as e:
            return False, f"Erro inesperado: {str(e)}"

    def _create_server(self) -> smtplib.SMTP:
        """Cria e autentica a conexão com o servidor SMTP."""
        host = self.server_config["host"]
        
        if self.security == "SSL":
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, self.port, context=context, timeout=15)
        else:  # STARTTLS
            server = smtplib.SMTP(host, self.port, timeout=15)
            server.starttls(context=ssl.create_default_context())
            
        server.login(self.email, self.password)
        return server

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
        Implementa retry automático em caso de falhas de rede transitórias.
        """
        last_error = ""
        for attempt in range(retry_count):
            try:
                msg = self._build_message(to_email, to_name, subject, html_body, text_body)
                server = self._create_server()
                server.send_message(msg)
                server.quit()
                return True, "Enviado com sucesso"
            except smtplib.SMTPServerDisconnected:
                last_error = "Conexão perdida com o servidor. Tentando reconectar..."
            except smtplib.SMTPRecipientsRefused:
                return False, "E-mail do destinatário recusado pelo servidor."
            except Exception as e:
                last_error = str(e)
                
        return False, f"Falha após {retry_count} tentativas: {last_error}"

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
        # Multipart related permite HTML + Imagens inline
        msg = MIMEMultipart("related")
        # Codificação UTF-8 explícita para o assunto (suporta emojis e acentos)
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = formataddr(("CP Fani", self.email))
        msg["To"] = formataddr((to_name, to_email))

        # Multipart alternative para fallback texto puro
        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(text_body, "plain", "utf-8"))
        
        # Processar HTML para encontrar e substituir imagens locais por CIDs
        html_processed, images = self._process_inline_images(html_body)
        alt_part.attach(MIMEText(html_processed, "html", "utf-8"))
        
        msg.attach(alt_part)

        # Anexar imagens como inline
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
        retornando o HTML modificado e o dicionário de imagens.
        """
        images = {}
        # Regex para encontrar src="..." ou src='...'
        pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
        
        def replacer(match: re.Match) -> str:
            original_tag = match.group(0)
            src = match.group(1)
            
            # Ignorar URLs externas (http, https, data:)
            if src.startswith(("http://", "https://", "data:")):
                return original_tag
                
            # Limpar prefixo file:// se existir (comum ao colar no QTextEdit)
            if src.startswith("file:///"):
                src = src[8:]
            elif src.startswith("file://"):
                src = src[7:]
                
            # Gerar um CID único
            cid = f"img_{len(images) + 1}@cp-fani.local"
            images[cid] = src
            
            # Substituir o src no HTML
            return original_tag.replace(f'src="{src}"', f'src="cid:{cid}"').replace(f"src='{src}'", f"src='cid:{cid}'")

        html_processed = pattern.sub(replacer, html_body)
        return html_processed, images