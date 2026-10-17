# ==============================================================================
# WORKER DE ENVIO - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Thread responsável por orquestrar o envio de e-mails em segundo plano,
# respeitando limites diários, intervalos aleatórios, disjuntor de falhas (circuit breaker)
# e prevenção de suspensão do sistema operacional.

import json
import os
import time
import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from PySide6.QtCore import QThread, Signal

from app.config import (
    MAX_DAILY_LIMIT, 
    MIN_INTERVAL_SECONDS, 
    MAX_INTERVAL_SECONDS, 
    APP_STATE_FILE
)
from app.core.smtp_client import SMTPClient
from app.core.template_engine import render_template
from app.core.power import prevent_sleep, allow_sleep

# Termos e códigos de erro considerados fatais para interrupção imediata pelo disjuntor
FATAL_SMTP_KEYWORDS = [
    "autenticação", "authentication", "535", "cota", "quota", 
    "limit", "421", "450", "452", "550", "5.4.5", "refused", "recusado"
]


class SenderWorker(QThread):
    # Sinais para comunicação segura com a Interface Gráfica (UI)
    progress_updated = Signal(int, int, int, float)  # (enviados, falhas, restantes, tempo_estimado_segundos)
    log_updated = Signal(dict)                # Registro de log individual para o CSV e UI
    status_changed = Signal(str)              # Status atual do processo
    finished_sending = Signal(dict)           # Resumo final para o relatório
    error_occurred = Signal(str)              # Erros críticos do sistema
    state_mismatch = Signal(str)              # Sinaliza quando o estado carregado não bate com a campanha atual

    def __init__(
        self, 
        contacts: List[Dict[str, Any]], 
        subject: str, 
        html_body: str, 
        text_body: str, 
        smtp_config: Dict[str, Any],
        daily_limit: int = MAX_DAILY_LIMIT,
        min_interval: int = MIN_INTERVAL_SECONDS,
        max_interval: int = MAX_INTERVAL_SECONDS,
        max_consecutive_failures: int = 5,
        only_failures: bool = False
    ):
        super().__init__()
        self.all_contacts = contacts
        self.subject = subject
        self.html_body = html_body
        self.text_body = text_body
        self.smtp_config = smtp_config
        self.max_consecutive_failures = max_consecutive_failures
        self.only_failures = only_failures
        
        # Limites configuráveis pela UI
        self.daily_limit = min(daily_limit, MAX_DAILY_LIMIT)
        self.min_interval = max(1, min_interval)
        self.max_interval = max(self.min_interval, max_interval)
        
        # Flags de controle de execução
        self._is_paused = False
        self._is_stopped = False
        
        # Gera a assinatura da campanha atual
        self.campaign_signature = self._generate_campaign_signature()
        
        # Carrega o estado persistente (limite diário, falhas e índice de retomada)
        self.state = self._load_state()
        
        # Filtragem caso seja solicitada apenas a reexecução de falhas
        if self.only_failures:
            failed_set = set(self.state.get("failed_emails", []))
            self.contacts = [c for c in self.all_contacts if c.get("EMail", "").strip().lower() in failed_set]
        else:
            self.contacts = self.all_contacts

        # Contadores separados para esta execução
        self.execution_sent = 0
        self.execution_failed = 0
        self.consecutive_failures = 0
        self.start_time: Optional[datetime] = None
        self._finished_emitted = False

    def _generate_campaign_signature(self) -> str:
        """
        Gera um hash único baseado na lista de e-mails e na conta remetente.
        Usado para detectar se a campanha mudou e invalidar o estado de retomada.
        """
        emails_str = "|".join(c.get("EMail", "").strip().lower() for c in self.all_contacts)
        account = self.smtp_config.get("email", "").strip().lower()
        signature_data = f"{account}:{emails_str}"
        return hashlib.sha256(signature_data.encode('utf-8')).hexdigest()[:16]

    def _load_state(self) -> Dict[str, Any]:
        """
        Carrega o estado do último envio do arquivo JSON.
        Reseta o contador se mudou o dia ou se a campanha/conta mudou.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        current_account = self.smtp_config.get("email", "").strip().lower()
        
        default_state = {
            "last_date": today,
            "account": current_account,
            "campaign_signature": self.campaign_signature,
            "sent_today": 0,
            "last_index": 0,
            "sent_emails": [],
            "failed_emails": []
        }
        
        if os.path.exists(APP_STATE_FILE):
            try:
                with open(APP_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    
                    if "failed_emails" not in state:
                        state["failed_emails"] = []

                    # Verifica se mudou o dia
                    if state.get("last_date") != today:
                        state["sent_today"] = 0
                        state["last_date"] = today
                        state["sent_emails"] = []
                        state["failed_emails"] = []
                        state["last_index"] = 0
                    
                    # Verifica se a conta ou a campanha mudou
                    if (state.get("account") != current_account or 
                        state.get("campaign_signature") != self.campaign_signature):
                        self.state_mismatch.emit("Campanha ou conta diferente da última execução")
                        state["last_index"] = 0
                        state["sent_emails"] = []
                        state["failed_emails"] = []
                        state["campaign_signature"] = self.campaign_signature
                        state["account"] = current_account
                    
                    return state
            except Exception:
                pass
                
        return default_state

    def _save_state(self):
        """Salva o estado atual no arquivo JSON de forma segura."""
        try:
            with open(APP_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao salvar estado de envio: {str(e)}")

    def reset_progress(self):
        """Reinicia o progresso de envio."""
        self.state["last_index"] = 0
        self.state["sent_emails"] = []
        self.state["failed_emails"] = []
        self._save_state()
        self.status_changed.emit("Progresso reiniciado")

    def pause(self):
        """Pausa o loop de envio e libera o gerenciador de energia."""
        self._is_paused = True
        allow_sleep()
        self.status_changed.emit("Pausado pelo usuário")

    def resume(self):
        """Retoma o loop de envio e ativa a prevenção de suspensão."""
        self._is_paused = False
        prevent_sleep()
        self.status_changed.emit("Retomando envio...")

    def stop(self):
        """Solicita a parada definitiva do loop de envio."""
        self._is_stopped = True
        self.requestInterruption()
        allow_sleep()
        self.status_changed.emit("Parando envio...")

    def _interruptible_sleep(self, seconds: float) -> bool:
        """
        Aguarda o tempo especificado em frações de 100ms, verificando flags de interrupção.
        Retorna True se foi interrompido.
        """
        steps = int(seconds * 10)
        for _ in range(steps):
            if self._is_stopped or self._is_paused or self.isInterruptionRequested():
                return True
            self.msleep(100)
        return False

    def _is_fatal_error(self, message: str) -> bool:
        """Verifica se a mensagem de erro SMTP corresponde a uma falha fatal/permanente."""
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in FATAL_SMTP_KEYWORDS)

    def run(self):
        """Método principal executado na thread. Orquestra o envio e o disjuntor."""
        prevent_sleep()
        try:
            self.status_changed.emit("Iniciando conexão SMTP...")
            
            try:
                client = SMTPClient(
                    provider=self.smtp_config['provider'],
                    email=self.smtp_config['email'],
                    password=self.smtp_config['password'],
                    port=self.smtp_config['port'],
                    security=self.smtp_config['security']
                )
                success, msg = client.connect()
                if not success:
                    raise Exception(f"Falha ao conectar: {msg}")
            except Exception as e:
                self.error_occurred.emit(f"Falha ao configurar SMTP: {str(e)}")
                return

            sent_count = self.state["sent_today"]
            failed_count = len(self.state.get("failed_emails", []))
            total_contacts = len(self.contacts)
            start_index = 0 if self.only_failures else self.state["last_index"]
            self.start_time = datetime.now()
            
            for i in range(start_index, total_contacts):
                if self._is_stopped or self.isInterruptionRequested():
                    break
                    
                while self._is_paused:
                    self.msleep(200)
                    if self._is_stopped or self.isInterruptionRequested():
                        break
                        
                if self._is_stopped or self.isInterruptionRequested():
                    break
                    
                if sent_count >= self.daily_limit:
                    msg = f"Limite diário de {self.daily_limit} e-mails atingido."
                    self.status_changed.emit(msg)
                    self.error_occurred.emit(msg)
                    break

                contact = self.contacts[i]
                email = contact.get("EMail", "").strip().lower()
                codigo = contact.get("CodigoRevendedor", "")
                nome = contact.get("Nome", "")
                
                # Se não for envio exclusivo de falhas e já tiver sido enviado hoje, pula
                if not self.only_failures and email in self.state["sent_emails"]:
                    continue

                try:
                    rendered_subject = render_template(self.subject, contact)
                    rendered_html = render_template(self.html_body, contact)
                    rendered_text = render_template(self.text_body, contact)
                except Exception as e:
                    self._emit_log(codigo, email, nome, "FALHA", f"Erro no template: {str(e)}")
                    failed_count += 1
                    self.execution_failed += 1
                    if email not in self.state["failed_emails"]:
                        self.state["failed_emails"].append(email)
                    self._update_progress(i, total_contacts, sent_count, failed_count)
                    continue

                self.status_changed.emit(f"Enviando para {email} ({i+1}/{total_contacts})...")
                success, message = client.send_email(
                    to_email=email,
                    to_name=nome,
                    subject=rendered_subject,
                    html_body=rendered_html,
                    text_body=rendered_text
                )

                status = "ENVIADO" if success else "FALHA"
                self._emit_log(codigo, email, nome, status, "" if success else message)

                if success:
                    sent_count += 1
                    self.execution_sent += 1
                    self.consecutive_failures = 0
                    if email not in self.state["sent_emails"]:
                        self.state["sent_emails"].append(email)
                    if email in self.state["failed_emails"]:
                        self.state["failed_emails"].remove(email)
                else:
                    failed_count += 1
                    self.execution_failed += 1
                    self.consecutive_failures += 1
                    if email not in self.state["failed_emails"]:
                        self.state["failed_emails"].append(email)

                # Persistência de estado
                self.state["sent_today"] = sent_count
                if not self.only_failures:
                    self.state["last_index"] = i + 1
                self._save_state()

                self._update_progress(i, total_contacts, sent_count, failed_count)

                # Avaliação do Disjuntor (Circuit Breaker)
                if not success:
                    if self._is_fatal_error(message):
                        fatal_msg = f"Disjuntor acionado por erro fatal/autenticação: {message}"
                        self.status_changed.emit(fatal_msg)
                        self.error_occurred.emit(fatal_msg)
                        self._is_paused = True
                        break

                    if self.consecutive_failures >= self.max_consecutive_failures:
                        circuit_msg = f"Disjuntor acionado: {self.consecutive_failures} falhas consecutivas. Disparo pausado."
                        self.status_changed.emit(circuit_msg)
                        self.error_occurred.emit(circuit_msg)
                        self._is_paused = True
                        break

                if i < total_contacts - 1 and not self._is_stopped and not self.isInterruptionRequested():
                    sleep_time = random.randint(self.min_interval, self.max_interval)
                    self.status_changed.emit(f"Aguardando {sleep_time}s para o próximo envio...")
                    if self._interruptible_sleep(sleep_time):
                        if self._is_paused:
                            continue
                        else:
                            break

            end_time = datetime.now()
            summary = {
                "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else "N/A",
                "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "total": total_contacts,
                "sent": sent_count,
                "failed": failed_count,
                "remaining": total_contacts - (self.state["last_index"] if not self.only_failures else total_contacts),
                "execution_sent": self.execution_sent,
                "execution_failed": self.execution_failed,
                "failed_emails_count": len(self.state["failed_emails"])
            }
            
            self._finished_emitted = True
            self.finished_sending.emit(summary)
            self.status_changed.emit("Processo finalizado")
            
            client.close()
            
        except Exception as e:
            self.error_occurred.emit(f"Erro crítico no worker: {str(e)}")
        finally:
            allow_sleep()
            if not self._finished_emitted:
                error_summary = {
                    "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else "N/A",
                    "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total": len(self.contacts),
                    "sent": self.execution_sent,
                    "failed": self.execution_failed,
                    "remaining": len(self.contacts) - self.state["last_index"],
                    "execution_sent": self.execution_sent,
                    "execution_failed": self.execution_failed,
                    "error": True
                }
                self._finished_emitted = True
                self.finished_sending.emit(error_summary)

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
        """Emite o sinal de progresso formatado com estimativa de tempo (ETA)."""
        remaining = total - (current_index + 1)
        
        estimated_time = 0.0
        if self.start_time and (self.execution_sent + self.execution_failed) > 0:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            processed = self.execution_sent + self.execution_failed
            avg_time_per_email = elapsed / processed
            estimated_time = avg_time_per_email * remaining
        
        self.progress_updated.emit(sent, failed, remaining, estimated_time)