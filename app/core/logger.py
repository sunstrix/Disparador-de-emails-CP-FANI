# ==============================================================================
# LOGGER E RELATÓRIOS - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Responsável por registrar os logs de envio em CSV em tempo real e gerar
# o relatório final com anexo para o TI ao término do processo.

import os
import csv
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from email.utils import formataddr, formatdate, make_msgid

from app.config import LOGS_DIR, REPORT_EMAIL
from app.core.smtp_client import SMTPClient

class CampaignLogger:
    def __init__(self):
        # Garante que a pasta de logs exista
        os.makedirs(LOGS_DIR, exist_ok=True)
        
        # Gera o nome do arquivo de log com base na data e hora de início
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = f"disparo_{timestamp}.csv"
        self.log_filepath = os.path.join(LOGS_DIR, self.log_filename)
        
        # Inicializa o arquivo CSV com o cabeçalho
        self._init_csv()
        
        self.start_time = datetime.now()

    def _init_csv(self):
        """Cria o arquivo CSV e escreve o cabeçalho usando utf-8-sig para compatibilidade com Excel."""
        headers = ["Data/Hora", "CodigoRevendedor", "Destinatario", "Nome", "Status", "Erro"]
        with open(self.log_filepath, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(headers)

    def log_entry(self, entry: dict):
        """
        Adiciona uma linha ao arquivo de log.
        Espera um dicionário com as chaves: data_hora, codigo, destinatario, nome, status, erro.
        """
        row = [
            entry.get("data_hora", ""),
            entry.get("codigo", ""),
            entry.get("destinatario", ""),
            entry.get("nome", ""),
            entry.get("status", ""),
            entry.get("erro", "")
        ]
        with open(self.log_filepath, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(row)

    def send_final_report(self, summary: dict, smtp_config: dict):
        """
        Envia o e-mail de relatório final para o TI com o CSV em anexo.
        Utiliza a conexão SMTP reutilizável (connect/close) e adiciona cabeçalhos RFC.
        Este método é seguro para ser chamado de uma thread separada (P0-9).
        """
        end_time = datetime.now()
        
        subject = f"[CP Fani] Relatório de Disparo - {self.start_time.strftime('%d/%m/%Y %H:%M')}"
        
        body_text = f"""
        Olá, TI.
        
        O processo de disparo de e-mails foi finalizado (ou interrompido).
        
        Resumo:
        - Início: {summary.get('start_time', 'N/A')}
        - Fim: {summary.get('end_time', end_time.strftime('%Y-%m-%d %H:%M:%S'))}
        - Total de contatos: {summary.get('total', 0)}
        - Enviados com sucesso: {summary.get('sent', 0)}
        - Falhas: {summary.get('failed', 0)}
        - Restantes: {summary.get('remaining', 0)}
        
        O arquivo de log detalhado está em anexo.
        
        Atenciosamente,
        Disparador de E-mails CP Fani
        """
        
        # Monta a mensagem
        msg = MIMEMultipart()
        msg["From"] = formataddr(("CP Fani", smtp_config.get("email", "")))
        msg["To"] = REPORT_EMAIL
        msg["Subject"] = Header(subject, "utf-8")
        
        # Cabeçalhos RFC (P1-6)
        msg["Date"] = formatdate(localtime=True)
        domain = smtp_config.get("email", "").split('@')[1] if '@' in smtp_config.get("email", "") else "cp-fani.local"
        msg["Message-ID"] = make_msgid(domain=domain)
        
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        
        # Anexa o arquivo CSV
        if os.path.exists(self.log_filepath):
            with open(self.log_filepath, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={self.log_filename}",
            )
            msg.attach(part)
            
        # Envia o e-mail usando a conexão reutilizável (P0-4)
        client = None
        try:
            client = SMTPClient(
                provider=smtp_config['provider'],
                email=smtp_config['email'],
                password=smtp_config['password'],
                port=smtp_config['port'],
                security=smtp_config['security']
            )
            # Conecta (reutiliza se já estiver conectado, senão cria nova conexão)
            success, msg_conn = client.connect()
            if not success:
                return False, f"Falha ao conectar para enviar relatório: {msg_conn}"
            
            # Envia a mensagem
            client.server.send_message(msg)
            
            return True, "Relatório enviado com sucesso."
        except Exception as e:
            return False, f"Falha ao enviar relatório: {str(e)}"
        finally:
            # Fecha a conexão de forma segura
            if client:
                client.close()