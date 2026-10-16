# ==============================================================================
# WORKER DE ENVIO - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Thread responsável por orquestrar o envio de e-mails em segundo plano,
# respeitando limites diários, intervalos aleatórios e permitindo pausa/retomada.

import json
import os
import time
import random
from datetime import datetime
from typing import List, Dict, Any

from PySide6.QtCore import QThread, Signal

from app.config import (
    MAX_DAILY_LIMIT, 
    MIN_INTERVAL_SECONDS, 
    MAX_INTERVAL_SECONDS, 
    APP_STATE_FILE
)
from app.core.smtp_client import SMTPClient
from app.core.template_engine import render_template

class SenderWorker(QThread):
    # Sinais para comunicação segura com a Interface Gráfica (UI)
    progress_updated = Signal(int, int, int)  # (enviados, falhas, restantes)
    log_updated = Signal(dict)                # Registro de log individual para o CSV e UI
    status_changed = Signal(str)              # Status atual do processo
    finished_sending = Signal(dict)           # Resumo final para o relatório
    error_occurred = Signal(str)              # Erros críticos do sistema

    def __init__(self, contacts: List[Dict[str, Any]], subject: str, html_body: str, text_body: str, smtp_config: Dict[str, Any]):
        super().__init__()
        self.contacts = contacts
        self.subject = subject
        self.html_body = html_body
        self.text_body = text_body
        self.smtp_config = smtp_config
        
        # Flags de controle de execução
        self._is_paused = False
        self._is_stopped = False
        
        # Carrega o estado persistente (limite diário e índice de retomada)
        self.state = self._load_state()
        
    def _load_state(self) -> Dict[str, Any]:
        """Carrega o estado do último envio do arquivo JSON. Reseta o contador se mudou o dia."""
        today = datetime.now().strftime("%Y-%m-%d")
        default_state = {
            "last_date": today,
            "sent_today": 0,
            "last_index": 0,
            "sent_emails": []
        }
        
        if os.path.exists(APP_STATE_FILE):
            try:
                with open(APP_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    # Se mudou o dia, reseta o contador diário e a lista de enviados do dia
                    if state.get("last_date") != today:
                        state["sent_today"] = 0
                        state["last_date"] = today
                        state["sent_emails"] = []
                    return state
            except Exception:
                pass # Se o arquivo estiver corrompido, usa o padrão
                
        return default_state

    def _save_state(self):
        """Salva o estado atual no arquivo JSON de forma segura."""
        try:
            with open(APP_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao salvar estado de envio: {str(e)}")

    def pause(self):
        """Pausa o loop de envio."""
        self._is_paused = True
        self.status_changed.emit("Pausado pelo usuário")

    def resume(self):
        """Retoma o loop de envio."""
        self._is_paused = False
        self.status_changed.emit("Retomando envio...")

    def stop(self):
        """Solicita a parada definitiva do loop de envio."""
        self._is_stopped = True
        self.status_changed.emit("Parando envio...")

    def run(self):
        """Método principal executado na thread. Orquestra o envio."""
        self.status_changed.emit("Iniciando conexão SMTP...")
        
        # 1. Inicializar cliente SMTP
        try:
            client = SMTPClient(
                provider=self.smtp_config['provider'],
                email=self.smtp_config['email'],
                password=self.smtp_config['password'],
                port=self.smtp_config['port'],
                security=self.smtp_config['security']
            )
        except Exception as e:
            self.error_occurred.emit(f"Falha ao configurar SMTP: {str(e)}")
            return

        sent_count = self.state["sent_today"]
        failed_count = 0
        total_contacts = len(self.contacts)
        start_index = self.state["last_index"]
        start_time = datetime.now()
        
        # 2. Loop de envio
        for i in range(start_index, total_contacts):
            # Verifica se foi solicitado para parar
            if self._is_stopped:
                break
                
            # Loop de pausa (aguarda até ser retomado ou parado)
            while self._is_paused:
                time.sleep(1)
                if self._is_stopped:
                    break
                    
            if self._is_stopped:
                break
                
            # 3. Verificar limite diário rígido (200 e-mails)
            if sent_count >= MAX_DAILY_LIMIT:
                msg = f"Limite diário de {MAX_DAILY_LIMIT} e-mails atingido."
                self.status_changed.emit(msg)
                self.error_occurred.emit(msg)
                break

            contact = self.contacts[i]
            email = contact.get("EMail", "").strip().lower()
            codigo = contact.get("CodigoRevendedor", "")
            nome = contact.get("Nome", "")
            
            # 4. Verificar se já foi enviado hoje (evita reenvio na retomada)
            if email in self.state["sent_emails"]:
                continue

            # 5. Renderizar templates (assunto, HTML, texto)
            try:
                rendered_subject = render_template(self.subject, contact)
                rendered_html = render_template(self.html_body, contact)
                rendered_text = render_template(self.text_body, contact)
            except Exception as e:
                self._emit_log(codigo, email, nome, "FALHA", f"Erro no template: {str(e)}")
                failed_count += 1
                self._update_progress(i, total_contacts, sent_count, failed_count)
                continue

            # 6. Enviar e-mail via SMTP
            self.status_changed.emit(f"Enviando para {email} ({i+1}/{total_contacts})...")
            success, message = client.send_email(
                to_email=email,
                to_name=nome,
                subject=rendered_subject,
                html_body=rendered_html,
                text_body=rendered_text
            )

            # 7. Registrar log e atualizar contadores
            status = "ENVIADO" if success else "FALHA"
            self._emit_log(codigo, email, nome, status, "" if success else message)

            if success:
                sent_count += 1
                self.state["sent_emails"].append(email)
            else:
                failed_count += 1

            # 8. Persistir estado (índice e contador)
            self.state["sent_today"] = sent_count
            self.state["last_index"] = i + 1
            self._save_state()

            # 9. Atualizar Interface Gráfica
            self._update_progress(i, total_contacts, sent_count, failed_count)

            # 10. Intervalo aleatório entre envios (anti-spam)
            if i < total_contacts - 1 and not self._is_stopped:
                sleep_time = random.randint(MIN_INTERVAL_SECONDS, MAX_INTERVAL_SECONDS)
                self.status_changed.emit(f"Aguardando {sleep_time}s para o próximo envio...")
                time.sleep(sleep_time)

        # 11. Finalização e resumo
        end_time = datetime.now()
        summary = {
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "total": total_contacts,
            "sent": sent_count,
            "failed": failed_count,
            "remaining": total_contacts - self.state["last_index"]
        }
        
        self.finished_sending.emit(summary)
        self.status_changed.emit("Processo finalizado")

    def _emit_log(self, codigo: str, email: str, nome: str, status: str, erro: str):
        """Emite o sinal de log formatado."""
        self.log_updated.emit({
            "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "codigo": codigo,
            "destinatario": email,
            "nome": nome,
            "status": status,
            "erro": erro
        })

    def _update_progress(self, current_index: int, total: int, sent: int, failed: int):
        """Emite o sinal de progresso formatado."""
        remaining = total - (current_index + 1)
        self.progress_updated.emit(sent, failed, remaining)