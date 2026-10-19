# ==============================================================================
# MOTOR DE TEMPLATES - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Responsável pela substituição segura de variáveis, normalização de nomes
# e validação de campos antes do disparo, evitando vazamento de tags cruas.

import re
import html
import unicodedata
from typing import Dict, List, Any

from app.config import FALLBACK_NOME


def normalize_key(key: str) -> str:
    """
    Normaliza o nome de uma coluna para ser usado como chave de variável.
    Ex: "Tel Celular" -> "tel_celular", "Código Revendedor" -> "codigo_revendedor"
    """
    if not isinstance(key, str):
        return ""
    
    # Remove acentos
    key = ''.join(
        c for c in unicodedata.normalize('NFKD', key)
        if unicodedata.category(c) != 'Mn'
    )
    
    # Minúsculas e substitui espaços/caracteres especiais por underscore
    key = re.sub(r'[^a-z0-9]+', '_', key.lower()).strip('_')
    return key


def extract_first_name(full_name: str, use_two_names: bool = False) -> str:
    """
    Extrai o primeiro nome (ou os dois primeiros) e aplica capitalização correta.
    Ex: "MARIA DONIZETE FERNANDES" -> "Maria" (ou "Maria Donizete" se use_two_names=True)
    """
    if not full_name or not isinstance(full_name, str):
        return ""
    
    # Limpa espaços extras e divide
    parts = full_name.strip().split()
    if not parts:
        return ""
    
    # Pega 1 ou 2 partes
    count = 2 if use_two_names and len(parts) >= 2 else 1
    selected_parts = parts[:count]
    
    # Capitaliza cada parte (ex: "MARIA" -> "Maria", "da" -> "Da")
    return " ".join(part.capitalize() for part in selected_parts)


def format_full_name(full_name: str) -> str:
    """
    Formata o nome completo com capitalização de título.
    """
    if not full_name or not isinstance(full_name, str):
        return ""
    return full_name.strip().title()


def _clean_val(val: Any) -> str:
    """
    Auxiliar para limpar e converter valores de variáveis,
    removendo sufixos .0 e tratando nulos/NaNs.
    """
    if val is None:
        return ""
    
    val_str = str(val).strip()
    if val_str.lower() in ('nan', 'none', 'null', '<na>'):
        return ""
    
    if re.match(r'^\d+\.0$', val_str):
        val_str = val_str[:-2]
    
    return val_str


def render_template(
    text: str,
    row_data: Dict[str, Any],
    fallback: str = FALLBACK_NOME,
    use_two_names: bool = False
) -> str:
    """
    Substitui todas as variáveis {{variavel}} no texto pelos valores da linha.
    Se a variável não existir ou estiver vazia, usa o fallback.
    NUNCA retorna a tag crua {{...}}.
    Aplica html.escape nos valores para evitar quebra de HTML (P1-2).
    """
    if not text or not isinstance(text, str):
        return text
    
    # Prepara um dicionário de chaves normalizadas para busca rápida
    normalized_row = {
        normalize_key(k): _clean_val(v) 
        for k, v in row_data.items() 
        if v is not None
    }
    
    def replacer(match: re.Match) -> str:
        var_raw = match.group(1).strip()
        var_key = normalize_key(var_raw)
        
        # Tratamento especial para primeiro_nome
        if var_key == "primeiro_nome":
            # Busca por colunas que contenham "nome" (nome, nome_completo, etc)
            full_name = ""
            for key in normalized_row:
                if "nome" in key and "primeiro" not in key:
                    full_name = normalized_row[key]
                    break
            
            val = extract_first_name(full_name, use_two_names=use_two_names)
            return html.escape(val) if val else html.escape(fallback)
        
        # Tratamento especial para nome_completo
        if var_key == "nome_completo":
            # Busca por colunas que contenham "nome"
            full_name = ""
            for key in normalized_row:
                if "nome" in key and "primeiro" not in key:
                    full_name = normalized_row[key]
                    break
            
            val = format_full_name(full_name)
            return html.escape(val) if val else html.escape(fallback)
        
        # Busca normal na planilha
        val = normalized_row.get(var_key, "")
        
        # Se estiver vazio ou for nulo/nan
        if not val or val.lower() in ('nan', 'none', 'null', '<na>'):
            return html.escape(fallback)
        
        # Escapa o valor para evitar injeção de HTML acidental (P1-2)
        return html.escape(val)
    
    # Substitui todas as ocorrências de {{ ... }}
    return re.sub(r'\{\{\s*([\w\W]+?)\s*\}\}', replacer, text)


def validate_variables(text: str, available_columns: List[str]) -> List[str]:
    """
    Verifica se todas as variáveis usadas no texto existem nas colunas disponíveis.
    Retorna uma lista de variáveis não encontradas (para aviso ao usuário).
    """
    if not text or not isinstance(text, str):
        return []
    
    # Extrai todas as variáveis do texto
    used_vars = set(re.findall(r'\{\{\s*([\w\W]+?)\s*\}\}', text))
    
    # Normaliza as colunas disponíveis para comparação
    normalized_cols = {normalize_key(col) for col in available_columns}
    
    # Adiciona variáveis especiais que são tratadas internamente
    normalized_cols.add("primeiro_nome")
    normalized_cols.add("nome_completo")
    
    missing = []
    for var in used_vars:
        if normalize_key(var) not in normalized_cols:
            missing.append(var)
    
    return missing