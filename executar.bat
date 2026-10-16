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
echo [DEBUG] Diretorio atual: %CD%
echo [DEBUG] Diretorio do script: %~dp0
cd /d "%~dp0"
echo [DEBUG] Novo diretorio atual: %CD%
echo.

REM Verificar se o arquivo main.py existe
if not exist "main.py" (
    echo ERRO: Arquivo main.py nao encontrado!
    echo.
    echo Diretorio atual: %CD%
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
if not exist "venv\Scripts\activate.bat" (
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

REM Ativar ambiente virtual
echo Ativando ambiente virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERRO: Falha ao ativar ambiente virtual!
    pause
    exit /b 1
)
echo Ambiente virtual ativado!
echo.

echo Iniciando o aplicativo...
echo.
echo ============================================================
echo   Para fechar o aplicativo, basta fechar esta janela
echo   ou pressionar Ctrl+C
echo ============================================================
echo.

REM Executar o aplicativo
python main.py

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