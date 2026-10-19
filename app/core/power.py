# ==============================================================================
# GESTÃO DE ENERGIA E SUSPENSÃO DO WINDOWS - DISPARADOR DE E-MAILS CP FANI
# ==============================================================================
# Módulo responsável por evitar a suspensão/hibernação do Windows durante o
# disparo de e-mails em segundo plano utilizando a API Win32 SetThreadExecutionState.

import sys
import ctypes

# Constantes da API Win32 SetThreadExecutionState
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

_is_preventing_sleep = False


def prevent_sleep(keep_display_on: bool = False) -> bool:
    """
    Solicita ao Windows que impeça a suspensão do sistema enquanto o envio estiver ativo.
    Fora do Windows, a chamada é ignorada de forma segura.
    Retorna True se a chamada foi realizada com sucesso.
    """
    global _is_preventing_sleep
    if sys.platform != "win32":
        return False
    
    try:
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        if keep_display_on:
            flags |= ES_DISPLAY_REQUIRED
        
        result = ctypes.windll.kernel32.SetThreadExecutionState(flags)
        if result != 0:
            _is_preventing_sleep = True
            return True
    except Exception:
        pass
    
    return False


def allow_sleep() -> bool:
    """
    Restaura as configurações de energia padrão do Windows, permitindo a suspensão normal.
    Fora do Windows, a chamada é ignorada de forma segura.
    Retorna True se a restauração foi realizada com sucesso.
    """
    global _is_preventing_sleep
    if sys.platform != "win32":
        return False
    
    try:
        result = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        _is_preventing_sleep = False
        return result != 0
    except Exception:
        pass
    
    return False


def is_preventing_sleep() -> bool:
    """Retorna True se o bloqueio de suspensão estiver ativo."""
    return _is_preventing_sleep