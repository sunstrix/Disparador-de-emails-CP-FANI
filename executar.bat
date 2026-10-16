@echo off
chcp 65001 >nul
title Disparador de E-mails CP Fani
color 0B

echo.
echo ============================================================
echo   DISPARADOR DE E-MAILS CP FANI
echo ============================================================
echo.

REM Navegar para o diretorio onde este script esta localizado
cd /d "%~dp0"

REM Verificar se o arquivo main.py existe
if not exist "main.py" (
    echo ERRO: Arquivo main.py nao encontrado!
    echo.
    echo Verifique se voce esta executando este script na pasta correta.
    echo A pasta deve conter: main.py, app\, requirements.txt
    echo.
    pause
    exit /b 1
)
echo Arquivo main.py encontrado!
echo.

REM Verificar se o ambiente virtual existe
if not exist "venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado!
    echo Criando ambiente virtual automaticamente...
    echo.
    python -m venv venv
    if errorlevel 1 (
        echo ERRO: Falha ao criar ambiente virtual!
        echo Verifique se o Python esta instalado corretamente.
        pause
        exit /b 1
    )
    echo Ambiente virtual criado com sucesso!
    echo.
) else (
    echo Ambiente virtual encontrado!
)

REM Definir o caminho do Python do ambiente virtual
set PYTHON=venv\Scripts\python.exe
set PIP=venv\Scripts\pip.exe

REM Verificar se o Python do venv funciona
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python do ambiente virtual nao esta funcionando!
    echo Tente executar o arquivo instalar.bat para recriar o ambiente.
    pause
    exit /b 1
)
echo Python do ambiente virtual: 
%PYTHON% --version
echo.

REM Verificar se as dependencias estao instaladas
echo Verificando dependencias...
%PYTHON% -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo.
    echo AVISO: Dependencias nao instaladas no ambiente virtual!
    echo.
    echo Instalando automaticamente...
    echo.
    %PIP% install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERRO: Falha ao instalar dependencias!
        echo Tente executar o arquivo instalar.bat manualmente.
        pause
        exit /b 1
    )
    echo.
    echo Dependencias instaladas com sucesso!
) else (
    echo Dependencias OK!
)
echo.

echo Iniciando o aplicativo...
echo.
echo ============================================================
echo   Para fechar o aplicativo, basta fechar esta janela
echo   ou pressionar Ctrl+C
echo ============================================================
echo.

REM Executar o aplicativo usando o Python do ambiente virtual
%PYTHON% main.py

REM Se o programa fechar com erro, manter a janela aberta
if errorlevel 1 (
    echo.
    echo ============================================================
    echo   O aplicativo fechou com erro!
    echo ============================================================
    echo.
    echo Codigo de erro: %errorlevel%
    echo.
    pause
)