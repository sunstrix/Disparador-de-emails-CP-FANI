@echo off
chcp 65001 >nul
setlocal EnableExtensions
title Disparador de E-mails CP Fani - Executar
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

:: 1. Verificar main.py
if not exist "main.py" (
    echo [ERRO CRITICO] Arquivo main.py nao encontrado em %CD% >> "%LOG_FILE%"
    echo.
    echo ERRO: Arquivo main.py nao foi encontrado na pasta atual.
    echo Execute o instalar_completo.bat para reparar a instalacao.
    echo.
    pause
    exit /b 1
)

:: 2. Verificar se o ambiente virtual existe
if not exist "venv\Scripts\python.exe" (
    echo [ERRO CRITICO] venv\Scripts\python.exe nao encontrado em %CD% >> "%LOG_FILE%"
    echo.
    echo ERRO: Ambiente virtual (venv) invalido ou nao encontrado.
    echo Execute o instalar_completo.bat para reparar o ambiente.
    echo.
    pause
    exit /b 1
)

:: 3. Testar se os modulos obrigatorios e o app estao carregando sem erros no venv
"venv\Scripts\python.exe" -c "import PySide6, pandas, keyring, app.ui.main_window" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [ERRO CRITICO] Falha ao carregar modulos no venv. >> "%LOG_FILE%"
    echo.
    echo ============================================================
    echo   ERRO AO CARREGAR DEPENDENCIAS DO APLICATIVO
    echo ============================================================
    echo Ocorreu uma falha ao carregar os modulos Python.
    echo Tentando executar via terminal para exibir o relatorio de erro:
    echo.
    "venv\Scripts\python.exe" "main.py"
    echo.
    echo Por favor, execute o instalar_completo.bat para reinstalar as dependencias.
    pause
    exit /b 1
)

echo Verificacoes concluidas com sucesso. Iniciando aplicativo... >> "%LOG_FILE%"

:: 4. Iniciar aplicacao em segundo plano
if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" "main.py"
) else (
    start "" "venv\Scripts\python.exe" "main.py"
)

echo Aplicativo iniciado com sucesso em %TIMESTAMP% >> "%LOG_FILE%"
exit /b 0