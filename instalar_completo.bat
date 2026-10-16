@echo off
chcp 65001 >nul
title Instalador Completo - Disparador de E-mails CP Fani
color 0A

:: ==============================================================================
:: AUTO-ELEVACAO (UAC)
:: ==============================================================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permissoes de administrador...
    powershell -Command "Start-Process -FilePath '%~f0' -ArgumentList '%*' -Verb RunAs"
    exit /b
)

:: ==============================================================================
:: CONFIGURACAO DE VARIAVEIS
:: ==============================================================================
set "INSTALL_DIR=C:\Disparador de e-mails"
set "UPDATE_MODE=0"
if "%~1"=="/atualizar" set "UPDATE_MODE=1"

echo ============================================================
echo   INSTALADOR COMPLETO - DISPARADOR DE E-MAILS CP FANI
echo   Pasta de destino: %INSTALL_DIR%
echo ============================================================

:: ==============================================================================
:: 1. VERIFICAR/INSTALAR PYTHON
:: ==============================================================================
echo [1/4] Verificando Python 3.10+...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python nao encontrado. Tentando instalar via winget...
    winget install --id Python.Python.3.12 -e --scope machine --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
    if %errorlevel% neq 0 (
        echo Falha ao instalar via winget. Por favor, instale o Python manualmente.
        pause
        exit /b 1
    )
    set "PATH=C:\Python312;%PATH%"
)

set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
python --version

:: ==============================================================================
:: 2. PREPARAR PASTA E BAIXAR VIA ZIP
:: ==============================================================================
echo [2/4] Preparando pasta e baixando arquivos...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

if exist "%INSTALL_DIR%\venv" (
    echo Fazendo backup do ambiente virtual...
    xcopy "%INSTALL_DIR%\venv" "%TEMP%\cpfani_venv_backup\" /E /I /H /Y >nul
)

echo Limpando instalacao anterior...
attrib -R "%INSTALL_DIR%\*.*" /S /D >nul 2>&1
rmdir /s /q "%INSTALL_DIR%" 2>nul
mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"

echo Baixando pacote do GitHub...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/sunstrix/Disparador-de-emails-CP-FANI/archive/refs/heads/main.zip' -OutFile '%TEMP%\cpfani_main.zip' -UseBasicParsing"
if %errorlevel% neq 0 (
    echo Falha no download. Verifique sua conexao.
    pause
    exit /b 1
)

echo Extraindo arquivos...
powershell -Command "Expand-Archive -Path '%TEMP%\cpfani_main.zip' -DestinationPath '%TEMP%' -Force"

move "%TEMP%\Disparador-de-emails-CP-FANI-main\*" "%INSTALL_DIR%" >nul 2>&1
move "%TEMP%\Disparador-de-emails-CP-FANI-main\.*" "%INSTALL_DIR%" >nul 2>&1

del /F /Q "%TEMP%\cpfani_main.zip" >nul 2>&1
rmdir /s /q "%TEMP%\Disparador-de-emails-CP-FANI-main" >nul 2>&1

:: ==============================================================================
:: 3. AMBIENTE VIRTUAL E DEPENDENCIAS
:: ==============================================================================
echo [3/4] Configurando ambiente virtual...
cd /d "%INSTALL_DIR%"

echo Criando ambiente virtual limpo...
python -m venv venv

echo Instalando dependencias...
"venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
"venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo Falha ao instalar dependencias.
    pause
    exit /b 1
)

:: ==============================================================================
:: 4. CRIAR ATALHO (SEM BLOQUEIO DE PERMISSOES)
:: ==============================================================================
echo [4/4] Criando atalho na area de trabalho...
set "DESKTOP_PUBLIC=C:\Users\Public\Desktop"
if not exist "%DESKTOP_PUBLIC%" set "DESKTOP_PUBLIC=%PUBLIC%\Desktop"

:: Usa icone nativo do Windows (Envelope) pois o ico/icone.ico nao existe no repo
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP_PUBLIC%\Disparador de E-mails CP Fani.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\venv\Scripts\pythonw.exe'; $Shortcut.Arguments = 'main.py'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = 'shell32.dll,134'; $Shortcut.WindowStyle = 7; $Shortcut.Save()"

echo.
echo ============================================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo O atalho foi criado na area de trabalho publica.
echo.

if "%UPDATE_MODE%"=="1" (
    echo Reiniciando o aplicativo...
    start "" "%INSTALL_DIR%\venv\Scripts\pythonw.exe" "main.py"
) else (
    pause
)