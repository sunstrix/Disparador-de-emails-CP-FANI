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
        except smtplib.SMTPAuthenticationError:
            return False, "Falha na autenticação. Verifique seu e-mail e senha (Gmail exige 'Senha de App')."
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
        Implementa retry com backoff para falhas transitórias.
        """
        last_error = ""
        for attempt in range(retry_count):
            try:
                # Garante que estamos conectados
                success, msg = self.connect()
                if not success:
                    # Falhas permanentes (autenticação) não devem ser repetidas
                    if "autenticação" in msg.lower() or "refused" in msg.lower():
                        return False, msg
                    
                    last_error = msg
                    time.sleep(2 ** attempt)  # Backoff exponencial simples
                    continue

                # Monta e envia a mensagem
                msg_obj = self._build_message(to_email, to_name, subject, html_body, text_body)
                self.server.send_message(msg_obj)
                
                # Se chegou aqui, o envio foi bem-sucedido.
                # NÃO chamamos quit() aqui para permitir a reutilização da conexão (P0-4).
                # O método close() deve ser chamado ao final do lote pelo chamador.
                return True, "Enviado com sucesso"

            except smtplib.SMTPServerDisconnected:
                last_error = "Conexão perdida com o servidor. Tentando reconectar..."
                self.server = None  # Força reconexão no próximo loop
            except smtplib.SMTPRecipientsRefused:
                return False, "E-mail do destinatário recusado pelo servidor."
            except Exception as e:
                last_error = str(e)
                self.server = None  # Força reconexão em erros genéricos de rede
                
            # Backoff antes da próxima tentativa
            time.sleep(2 ** attempt)
            
        return False, f"Falha após {retry_count} tentativas: {last_error}"

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
        
        # Cabeçalhos obrigatórios e de boa prática (P1-6)
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = formataddr(("CP Fani", self.email))
        msg["To"] = formataddr((to_name, to_email))
        msg["Date"] = formatdate(localtime=True)
        
        # Message-ID único baseado no domínio do remetente
        domain = self.email.split('@')[1] if '@' in self.email else "cp-fani.local"
        msg["Message-ID"] = make_msgid(domain=domain)
        
        if self.reply_to:
            msg["Reply-To"] = self.reply_to
        if self.list_unsubscribe:
            msg["List-Unsubscribe"] = f"<{self.list_unsubscribe}>"

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
        retornando o HTML modificado e o dicionário de imagens {cid: caminho_limpo}.
        """
        path_to_cid = {}
        cid_to_path = {}
        
        # Regex que captura o prefixo, o src exato e o sufixo da tag
        pattern = re.compile(r'(<img[^>]*?\bsrc=["\'])([^"\']+)(["\'][^>]*>)', re.IGNORECASE)
        
        def replacer(match: re.Match) -> str:
            prefix = match.group(1)
            src = match.group(2)
            suffix = match.group(3)
            
            # Ignorar URLs externas
            if src.startswith(("http://", "https://", "data:")):
                return match.group(0)
                
            # Decodificar URL (ex: %20 para espaço)
            clean_src = urllib.parse.unquote(src)
            
            # Tratar prefixos de arquivo local (Windows e Unix)
            if clean_src.startswith("file:///"):
                clean_src = clean_src[8:]
            elif clean_src.startswith("file://"):
                clean_src = clean_src[7:]
                
            # Normalizar o caminho para o sistema operacional atual
            clean_src = os.path.normpath(clean_src)
            
            # Deduplicação: reutilizar o mesmo CID para o mesmo arquivo
            if clean_src in path_to_cid:
                cid = path_to_cid[clean_src]
            else:
                cid = f"img_{len(path_to_cid) + 1}@cp-fani.local"
                path_to_cid[clean_src] = cid
                cid_to_path[cid] = clean_src
                
            # Garantir estilo de redimensionamento se a tag não tiver width ou style
            # (O Qt às vezes descarta max-width no toHtml)
            if 'style=' not in suffix.lower() and 'width=' not in suffix.lower():
                # Insere o style antes do fechamento da tag (ex: ">" ou "/>")
                suffix = suffix[:-1] + ' style="max-width: 100%; height: auto;"' + suffix[-1]
                
            return f'{prefix}cid:{cid}{suffix}'
        
        html_processed = pattern.sub(replacer, html_body)
        return html_processed, cid_to_path