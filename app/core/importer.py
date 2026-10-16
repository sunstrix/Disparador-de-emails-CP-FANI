# ==============================================================================
# IMPORTADOR DE DADOS - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Responsável por ler, limpar, validar e preparar a base de destinatários
# a partir de arquivos .xlsx ou .csv, garantindo a integridade dos dados e LGPD.

import pandas as pd
import re
import unicodedata
from typing import Dict, List, Tuple, Any

def normalize_string(text: str) -> str:
    """Remove acentos e converte para minúsculas para comparação robusta de cabeçalhos."""
    if not isinstance(text, str):
        return ""
    text = text.strip().lower()
    return ''.join(
        c for c in unicodedata.normalize('NFKD', text)
        if unicodedata.category(c) != 'Mn'
    )

def is_valid_email(email: str) -> bool:
    """Valida o formato básico de um e-mail."""
    if not email or not isinstance(email, str):
        return False
    email = email.strip().lower()
    # Regex padrão para validação de e-mail
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))

def auto_detect_columns(df: pd.DataFrame) -> Dict[str, str]:
    """
    Tenta identificar automaticamente as colunas de Código, Nome e E-mail.
    Retorna um dicionário com os nomes reais das colunas no DataFrame.
    """
    detected = {}
    target_mapping = {
        'codigo': ['codigo', 'codigorevendedor', 'cod_revendedor', 'id', 'codigo_revendedor', 'cod'],
        'nome': ['nome', 'nome_completo', 'revendedor', 'nome_revendedor'],
        'email': ['email', 'e-mail', 'mail', 'e_mail', 'email_contato']
    }

    # Normaliza os cabeçalhos do DataFrame para busca insensível a acentos/maiúsculas
    normalized_cols = {normalize_string(col): col for col in df.columns}

    for target, possible_names in target_mapping.items():
        for name in possible_names:
            norm_name = normalize_string(name)
            if norm_name in normalized_cols:
                detected[target] = normalized_cols[norm_name]
                break
    
    return detected

def process_contacts(
    df: pd.DataFrame,
    col_codigo: str,
    col_nome: str,
    col_email: str
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Processa o DataFrame: limpa, valida e remove duplicatas.
    Retorna o DataFrame limpo e um dicionário com estatísticas.
    """
    stats = {
        'total_linhas': len(df),
        'sem_email': 0,
        'email_invalido': 0,
        'duplicados': 0,
        'validos': 0
    }

    df_clean = df.copy()
    
    # 1. Tratar nulos e forçar tipo string (evita que "192.713" vire float)
    df_clean[col_codigo] = df_clean[col_codigo].fillna('').astype(str).str.strip()
    df_clean[col_nome] = df_clean[col_nome].fillna('').astype(str).str.strip()
    df_clean[col_email] = df_clean[col_email].fillna('').astype(str).str.strip().str.lower()

    valid_rows = []
    
    # 2. Classificar e filtrar linha a linha
    for _, row in df_clean.iterrows():
        email = row[col_email]
        
        # Verificar se está vazio (incluindo a string 'nan' que o pandas às vezes gera)
        if not email or email == 'nan':
            stats['sem_email'] += 1
            continue
            
        # Verificar validade do formato
        if not is_valid_email(email):
            stats['email_invalido'] += 1
            continue
            
        valid_rows.append(row)

    df_valid = pd.DataFrame(valid_rows)

    if df_valid.empty:
        stats['validos'] = 0
        # Retorna DataFrame vazio com as colunas padronizadas para evitar erros na UI
        return pd.DataFrame(columns=['CodigoRevendedor', 'Nome', 'EMail']), stats

    # 3. Remover duplicatas baseadas no e-mail (mantendo o primeiro encontrado)
    initial_valid_count = len(df_valid)
    df_valid = df_valid.drop_duplicates(subset=[col_email], keep='first')
    stats['duplicados'] = initial_valid_count - len(df_valid)
    stats['validos'] = len(df_valid)

    # 4. Padronizar colunas de saída para o sistema interno
    df_final = pd.DataFrame()
    df_final['CodigoRevendedor'] = df_valid[col_codigo]
    df_final['Nome'] = df_valid[col_nome]
    df_final['EMail'] = df_valid[col_email]
    
    # 5. Preservar outras colunas para variáveis dinâmicas no template
    for col in df_valid.columns:
        if col not in [col_codigo, col_nome, col_email]:
            # Normaliza o nome da coluna para ser uma variável segura (ex: "Tel Celular" -> "tel_celular")
            safe_col_name = re.sub(r'[^a-zA-Z0-9_]', '_', col).lower()
            df_final[safe_col_name] = df_valid[col]

    return df_final, stats

def load_contacts(file_path: str, sheet_name: str = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Carrega o arquivo bruto e identifica as colunas.
    A UI deve chamar esta função, mostrar as colunas detectadas para confirmação,
    e depois chamar process_contacts com as colunas confirmadas.
    """
    result = {
        'success': False,
        'error_message': '',
        'detected_columns': {},
        'available_sheets': []
    }

    try:
        if file_path.lower().endswith('.csv'):
            # P1-3: CSV brasileiro com ";" - usa sep=None e engine='python' para detecção automática
            # Tenta múltiplos encodings comuns no Brasil
            df = None
            encodings = ['utf-8', 'cp1252', 'latin1', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(
                        file_path, 
                        dtype=str, 
                        encoding=encoding,
                        sep=None,  # Detecção automática do separador
                        engine='python'  # Necessário para sep=None
                    )
                    # Se conseguiu ler e tem mais de uma coluna, o encoding está correto
                    if len(df.columns) > 1:
                        break
                except UnicodeDecodeError:
                    continue
                except Exception:
                    continue
            
            if df is None or len(df.columns) == 0:
                result['error_message'] = "Não foi possível ler o arquivo CSV. Verifique o encoding e o formato."
                return None, result
                
        elif file_path.lower().endswith('.xlsx'):
            # Obter lista de abas
            xls = pd.ExcelFile(file_path)
            result['available_sheets'] = xls.sheet_names
            
            # Se não for especificada, pega a primeira aba por padrão
            target_sheet = sheet_name if sheet_name in result['available_sheets'] else result['available_sheets'][0]
            df = pd.read_excel(xls, sheet_name=target_sheet, dtype=str)
            
        elif file_path.lower().endswith('.xls'):
            # P1-3: .xls antigo exige xlrd - orientar o usuário a converter para .xlsx
            result['error_message'] = "Arquivos .xls (Excel 97-2003) não são suportados. Por favor, converta para .xlsx no Excel e tente novamente."
            return None, result
            
        else:
            result['error_message'] = "Formato de arquivo não suportado. Use .xlsx ou .csv"
            return None, result

        # Verificar se o DataFrame está vazio
        if df.empty:
            result['error_message'] = "O arquivo está vazio ou não contém dados válidos."
            return None, result

        # Auto-detectar colunas
        result['detected_columns'] = auto_detect_columns(df)

        # Verificação de segurança: se não encontrar e-mail, o arquivo é inútil para o disparo
        if 'email' not in result['detected_columns']:
            result['error_message'] = "Não foi possível identificar uma coluna de 'E-mail' no arquivo. Verifique os cabeçalhos."
            return None, result

        result['success'] = True
        return df, result

    except pd.errors.EmptyDataError:
        result['error_message'] = "O arquivo está vazio."
        return None, result
    except pd.errors.ParserError as e:
        result['error_message'] = f"Erro ao processar o arquivo: {str(e)}"
        return None, result
    except Exception as e:
        result['error_message'] = f"Erro ao ler o arquivo: {str(e)}"
        return None, result