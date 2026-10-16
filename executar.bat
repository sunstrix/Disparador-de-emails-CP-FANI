@echo off
chcp 65001 >nul
title Disparador de E-mails CP Fani
color 0B

REM Navegar para o diretório onde este script está localizado
cd /d "%~dp0"

echo.
echo ============================================================
echo   DISPARADOR DE E-MAILS CP FANI
echo ============================================================
echo.

REM Verificar se o ambiente virtual existe
if not exist "venv\" (
    echo ERRO: Ambiente virtual nao encontrado!
    echo.
    echo Execute primeiro o arquivo: instalar.bat
    echo.
    pause
    exit /b 1
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

REM Verificar se o arquivo principal existe
if not exist "main.py" (
    echo ERRO: Arquivo main.py nao encontrado!
    echo.
    echo Verifique se voce esta executando este script na pasta correta.
    echo.
    pause
    exit /b 1
)

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