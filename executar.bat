@echo off
setlocal EnableExtensions
title Disparador de E-mails CP Fani
color 0B

cd /d "%~dp0"

:: Configurar diretorio e arquivo de log em LOCALAPPDATA
set "LOG_DIR=%LOCALAPPDATA%\CPFani\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

for /f "delims=" %%I in ('powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set "TIMESTAMP=%%I"
set "LOG_FILE=%LOG_DIR%\executar_%TIMESTAMP%.log"

echo ============================================================ > "%LOG_FILE%"
echo   LOG DE EXECUCAO - %TIMESTAMP% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

:: Verificar main.py
if not exist "main.py" (
    echo [ERRO CRITICO] Arquivo main.py nao encontrado em %CD% >> "%LOG_FILE%"
    echo.
    echo ERRO: Arquivo main.py nao foi encontrado na pasta atual.
    echo Execute o instalar_completo.bat para reparar os arquivos.
    echo.
    pause
    exit /b 1
)

:: Verificar executavel pythonw.exe no venv
if not exist "venv\Scripts\pythonw.exe" (
    echo [ERRO CRITICO] venv\Scripts\pythonw.exe nao encontrado em %CD% >> "%LOG_FILE%"
    echo.
    echo ERRO: Ambiente virtual (venv) invalido ou nao encontrado.
    echo Execute o instalar_completo.bat para reparar o ambiente.
    echo.
    pause
    exit /b 1
)

:: Verificar requirements.txt
if not exist "requirements.txt" (
    echo [ERRO CRITICO] Arquivo requirements.txt nao encontrado em %CD% >> "%LOG_FILE%"
    echo.
    echo ERRO: Arquivo requirements.txt nao foi encontrado.
    echo Execute o instalar_completo.bat para reparar a instalacao.
    echo.
    pause
    exit /b 1
)

echo Verificacoes concluidas com sucesso. Iniciando aplicativo... >> "%LOG_FILE%"

:: Iniciar aplicacao em segundo plano sem manter o console aberto
start "" "venv\Scripts\pythonw.exe" "main.py"

echo Aplicativo iniciado via pythonw.exe em %TIMESTAMP% >> "%LOG_FILE%"
exit /b 0