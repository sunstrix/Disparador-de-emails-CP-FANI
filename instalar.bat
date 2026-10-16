@echo off
chcp 65001 >nul
title Instalador - Disparador de E-mails CP Fani
color 0A
echo.
echo ============================================================
echo   INSTALADOR - DISPARADOR DE E-MAILS CP FANI
echo ============================================================
echo.

REM Navegar para o diretorio onde este script esta localizado
cd /d "%~dp0"

REM Verificar se Python esta instalado
echo [1/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
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
python --version
echo Python encontrado!
echo.

REM Verificar se o ambiente virtual existe
echo [2/4] Verificando ambiente virtual...
if not exist "venv\" (
    echo Criando ambiente virtual...
    python -m venv venv
    if errorlevel 1 (
        echo ERRO: Falha ao criar ambiente virtual!
        pause
        exit /b 1
    )
    echo Ambiente virtual criado com sucesso!
) else (
    echo Ambiente virtual ja existe.
)
echo.

REM Ativar ambiente virtual
echo [3/4] Ativando ambiente virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERRO: Falha ao ativar ambiente virtual!
    pause
    exit /b 1
)
echo Ambiente virtual ativado!
echo.

REM Verificar e instalar pip atualizado
echo [4/4] Instalando dependencias...
echo.
python -m pip install --upgrade pip --quiet
echo pip atualizado!
echo.

REM Verificar se requirements.txt existe
if not exist "requirements.txt" (
    echo ERRO: Arquivo requirements.txt nao encontrado!
    echo.
    echo Verifique se voce esta executando este script na pasta correta.
    echo.
    pause
    exit /b 1
)

echo Instalando dependencias do requirements.txt...
echo.
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo ERRO: Falha ao instalar dependencias!
    echo.
    echo Verifique sua conexao com a internet e tente novamente.
    echo.
    pause
    exit /b 1
)
echo.
echo Dependencias instaladas com sucesso!
echo.

echo ============================================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo.
echo Agora voce pode executar o aplicativo com:
echo executar.bat
echo.
echo Ou diretamente com:
echo python main.py
echo.
pause