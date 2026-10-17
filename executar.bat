@echo off
chcp 65001 >nul
title Disparador de E-mails CP Fani
color 0B
cd /d "%~dp0"

:: Criar pasta de logs se nao existir
if not exist "logs" mkdir logs

:: Gerar timestamp via PowerShell (formato universal)
for /f %%I in ('powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set TIMESTAMP=%%I
set LOG_FILE=logs\executar_%TIMESTAMP%.log

:: Iniciar arquivo de log
echo ============================================================ > "%LOG_FILE%"
echo   LOG DE EXECUCAO - %TIMESTAMP% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

echo ============================================================
echo   DISPARADOR DE E-MAILS CP FANI
echo ============================================================
echo Log desta execucao: %LOG_FILE%
echo.

:: Verifica se o main.py existe
if not exist "main.py" (
    echo ERRO CRITICO: Arquivo main.py nao encontrado. >> "%LOG_FILE%"
    echo Pasta atual: %CD% >> "%LOG_FILE%"
    echo.
    echo ERRO: Arquivo main.py nao encontrado.
    echo Execute o "instalar_completo.bat" como administrador.
    pause
    exit /b 1
)
echo [OK] Arquivo main.py encontrado. >> "%LOG_FILE%"

:: Verifica se o Python do venv existe
if not exist "venv\Scripts\python.exe" (
    echo ERRO CRITICO: Python do ambiente virtual nao encontrado. >> "%LOG_FILE%"
    echo Caminho esperado: %CD%\venv\Scripts\python.exe >> "%LOG_FILE%"
    echo.
    echo ERRO: Ambiente virtual nao encontrado.
    echo Execute o "instalar_completo.bat" como administrador.
    pause
    exit /b 1
)
echo [OK] Ambiente virtual encontrado. >> "%LOG_FILE%"

:: Verifica se o requirements.txt existe
if not exist "requirements.txt" (
    echo ERRO CRITICO: Arquivo requirements.txt nao encontrado. >> "%LOG_FILE%"
    echo.
    echo ERRO: Arquivo requirements.txt nao encontrado.
    echo Execute o "instalar_completo.bat" como administrador.
    pause
    exit /b 1
)
echo [OK] Arquivo requirements.txt encontrado. >> "%LOG_FILE%"

echo.
echo Iniciando aplicativo...
echo Iniciando main.py em %TIMESTAMP% >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

:: Executa o main.py e captura toda saida (stdout + stderr) no log
"venv\Scripts\python.exe" main.py >> "%LOG_FILE%" 2>&1
set EXIT_CODE=%errorlevel%

echo. >> "%LOG_FILE%"
echo Codigo de retorno: %EXIT_CODE% >> "%LOG_FILE%"
echo Finalizado em %TIMESTAMP% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

:: Se o python fechou com erro, mostra detalhes
if %EXIT_CODE% neq 0 (
    echo.
    echo ============================================================
    echo   ERRO: O aplicativo fechou inesperadamente (codigo %EXIT_CODE%).
    echo ============================================================
    echo.
    echo Log completo salvo em: %LOG_FILE%
    echo.
    echo Possiveis causas:
    echo   - Dependencias nao instaladas (rode instalar_completo.bat)
    echo   - Erro no codigo do main.py
    echo   - Falta de permissao na pasta
    echo.
    pause
    exit /b %EXIT_CODE%
)

echo.
echo Aplicativo finalizado normalmente.
echo Log completo salvo em: %LOG_FILE%
pause