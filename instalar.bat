@echo off
chcp 65001 >nul
title Instalador - Disparador de E-mails CP Fani
color 0A

echo.
echo ============================================================
echo   INSTALADOR - DISPARADOR DE E-MAILS CP FANI
echo ============================================================
echo.

REM Verificar se Python esta instalado
echo [1/5] Verificando Python...
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
echo [2/5] Verificando ambiente virtual...
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
echo [3/5] Ativando ambiente virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERRO: Falha ao ativar ambiente virtual!
    pause
    exit /b 1
)
echo Ambiente virtual ativado!
echo.

REM Verificar e instalar pip atualizado
echo [4/5] Verificando pip...
python -m pip install --upgrade pip --quiet
echo pip atualizado!
echo.

REM Instalar dependencias
echo [5/5] Instalando dependencias...
echo.
echo Verificando pacotes ja instalados...
echo.

REM Verificar cada pacote individualmente
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo Instalando PySide6...
    pip install PySide6>=6.5.0 --quiet
) else (
    echo PySide6 ja instalado.
)

python -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo Instalando pandas...
    pip install pandas>=2.0.0 --quiet
) else (
    echo pandas ja instalado.
)

python -c "import openpyxl" >nul 2>&1
if errorlevel 1 (
    echo Instalando openpyxl...
    pip install openpyxl>=3.1.0 --quiet
) else (
    echo openpyxl ja instalado.
)

python -c "import keyring" >nul 2>&1
if errorlevel 1 (
    echo Instalando keyring...
    pip install keyring>=24.0.0 --quiet
) else (
    echo keyring ja instalado.
)

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