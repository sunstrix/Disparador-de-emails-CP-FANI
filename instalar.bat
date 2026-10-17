@echo off
chcp 65001 >nul
title Instalador - Disparador de E-mails CP Fani
color 0A

:: Criar pasta de logs se nao existir
if not exist "logs" mkdir logs

:: Gerar timestamp via PowerShell (formato universal)
for /f %%I in ('powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set TIMESTAMP=%%I
set "LOG_FILE=logs\instalar_%TIMESTAMP%.log"

:: Iniciar arquivo de log
echo ============================================================ > "%LOG_FILE%"
echo   LOG DE INSTALACAO - %TIMESTAMP% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

echo.
echo ============================================================
echo   INSTALADOR - DISPARADOR DE E-MAILS CP FANI
echo ============================================================
echo Log desta execucao: %LOG_FILE%
echo.

REM Navegar para o diretorio onde este script esta localizado
cd /d "%~dp0"

:: Verificar se Python esta instalado
echo [1/4] Verificando Python...
echo [1/4] Verificando Python... >> "%LOG_FILE%"
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado! >> "%LOG_FILE%"
    echo.
    echo ERRO: Python nao encontrado!
    echo.
    echo Por favor, instale o Python 3.10 ou superior:
    echo https://www.python.org/downloads/
    echo.
    echo Durante a instalacao, marque a opcao:
    echo "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%V in ('python --version 2^>^&1') do echo %%V >> "%LOG_FILE%"
echo Python encontrado! >> "%LOG_FILE%"
echo Python encontrado!
echo.

:: Verificar se o ambiente virtual existe
echo [2/4] Verificando ambiente virtual...
echo [2/4] Verificando ambiente virtual... >> "%LOG_FILE%"
if not exist "venv\" (
    echo Criando ambiente virtual... >> "%LOG_FILE%"
    echo Criando ambiente virtual...
    python -m venv venv >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo ERRO: Falha ao criar ambiente virtual! >> "%LOG_FILE%"
        echo ERRO: Falha ao criar ambiente virtual!
        pause
        exit /b 1
    )
    echo Ambiente virtual criado com sucesso! >> "%LOG_FILE%"
    echo Ambiente virtual criado com sucesso!
) else (
    echo Ambiente virtual ja existe. >> "%LOG_FILE%"
    echo Ambiente virtual ja existe.
)
echo.

:: Atualizar pip (SEM activate.bat, conforme convencao)
echo [3/4] Atualizando pip...
echo [3/4] Atualizando pip... >> "%LOG_FILE%"
"venv\Scripts\python.exe" -m pip install --upgrade pip --quiet >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo ERRO: Falha ao atualizar pip! >> "%LOG_FILE%"
    echo ERRO: Falha ao atualizar pip!
    pause
    exit /b 1
)
echo pip atualizado! >> "%LOG_FILE%"
echo pip atualizado!
echo.

:: Verificar se requirements.txt existe
if not exist "requirements.txt" (
    echo ERRO: Arquivo requirements.txt nao encontrado! >> "%LOG_FILE%"
    echo.
    echo ERRO: Arquivo requirements.txt nao encontrado!
    echo.
    echo Verifique se voce esta executando este script na pasta correta.
    echo.
    pause
    exit /b 1
)

echo [4/4] Instalando dependencias do requirements.txt...
echo [4/4] Instalando dependencias do requirements.txt... >> "%LOG_FILE%"
echo.

"venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo.
    echo ERRO: Falha ao instalar dependencias! >> "%LOG_FILE%"
    echo.
    echo ERRO: Falha ao instalar dependencias!
    echo.
    echo Verifique sua conexao com a internet e tente novamente.
    echo.
    echo Log completo salvo em: %LOG_FILE%
    pause
    exit /b 1
)

echo.
echo Dependencias instaladas com sucesso! >> "%LOG_FILE%"
echo Dependencias instaladas com sucesso!
echo.

echo ============================================================ >> "%LOG_FILE%"
echo   INSTALACAO CONCLUIDA COM SUCESSO! >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

echo.
echo ============================================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo.
echo Agora voce pode executar o aplicativo com:
echo executar.bat
echo.
echo Ou diretamente com:
echo venv\Scripts\python.exe main.py
echo.
echo Log completo salvo em: %LOG_FILE%
echo.
pause