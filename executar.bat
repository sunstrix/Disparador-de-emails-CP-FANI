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
if not exist "venv\Scripts\pythonw.exe" (
    echo ERRO: Ambiente virtual nao encontrado!
    echo.
    echo Execute o arquivo "instalar_completo.bat" como administrador
    echo para instalar o aplicativo e suas dependencias.
    echo.
    pause
    exit /b 1
)
echo Ambiente virtual encontrado!
echo.

REM Definir o caminho do Python do ambiente virtual
set PYTHONW=venv\Scripts\pythonw.exe

REM Verificar se o Python do venv funciona
%PYTHONW% --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python do ambiente virtual nao esta funcionando!
    echo.
    echo Execute o arquivo "instalar_completo.bat" como administrador
    echo para reparar a instalacao.
    echo.
    pause
    exit /b 1
)

REM Verificar se as dependencias estao instaladas
%PYTHONW% -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo ERRO: Dependencias nao instaladas no ambiente virtual!
    echo.
    echo Execute o arquivo "instalar_completo.bat" como administrador
    echo para instalar as dependencias necessarias.
    echo.
    pause
    exit /b 1
)
echo Dependencias OK!
echo.

echo Iniciando o aplicativo...
echo.
echo ============================================================
echo   O aplicativo sera iniciado em segundo plano.
echo   Use o icone na bandeja do sistema (perto do relogio)
echo   para controlar o envio.
echo ============================================================
echo.

REM Executar o aplicativo usando pythonw.exe (sem console)
start "" "%PYTHONW%" main.py

REM Se o programa falhar ao iniciar, mostrar mensagem
timeout /t 2 /nobreak >nul
tasklist /FI "IMAGENAME eq pythonw.exe" /FI "WINDOWTITLE eq Disparador*" | find "pythonw.exe" >nul
if errorlevel 1 (
    echo.
    echo ============================================================
    echo   O aplicativo pode ter falhado ao iniciar!
    echo ============================================================
    echo.
    echo Verifique os logs em:
    echo %LOCALAPPDATA%\CPFani\logs\
    echo.
    echo Se o problema persistir, execute o arquivo
    echo "instalar_completo.bat" como administrador para reparar.
    echo.
    pause
)