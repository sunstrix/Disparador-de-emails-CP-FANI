@echo off
chcp 65001 >nul
title Disparador de E-mails CP Fani
color 0B
cd /d "%~dp0"

echo ============================================================
echo   DISPARADOR DE E-MAILS CP FANI
echo ============================================================
echo.

:: Verifica se o main.py existe
if not exist "main.py" (
    echo ERRO CRITICO: Arquivo main.py nao encontrado.
    echo Pasta atual: %CD%
    echo.
    echo Execute o "instalar_completo.bat" como administrador.
    pause
    exit /b 1
)
echo [OK] Arquivo main.py encontrado.

:: Verifica se o Python do venv existe
if not exist "venv\Scripts\python.exe" (
    echo ERRO CRITICO: Python do ambiente virtual nao encontrado.
    echo Caminho esperado: %CD%\venv\Scripts\python.exe
    echo.
    echo Execute o "instalar_completo.bat" como administrador.
    pause
    exit /b 1
)
echo [OK] Ambiente virtual encontrado.

:: Verifica se o requirements.txt existe
if not exist "requirements.txt" (
    echo ERRO CRITICO: Arquivo requirements.txt nao encontrado.
    echo Execute o "instalar_completo.bat" como administrador.
    pause
    exit /b 1
)
echo [OK] Arquivo requirements.txt encontrado.

echo.
echo Iniciando aplicativo...
echo.

:: Executa o main.py e captura o codigo de retorno
"venv\Scripts\python.exe" main.py
set EXIT_CODE=%errorlevel%

:: Se o python fechou com erro, mostra detalhes
if %EXIT_CODE% neq 0 (
    echo.
    echo ============================================================
    echo   ERRO: O aplicativo fechou inesperadamente (codigo %EXIT_CODE%).
    echo ============================================================
    echo.
    echo Possiveis causas:
    echo   - Dependencias nao instaladas (rode instalar_completo.bat)
    echo   - Erro no codigo do main.py
    echo   - Falta de permissao na pasta
    echo.
    echo Verifique o log em: %TEMP%\cpfani_erro.log
    pause
    exit /b %EXIT_CODE%
)

echo.
echo Aplicativo finalizado normalmente.
pause