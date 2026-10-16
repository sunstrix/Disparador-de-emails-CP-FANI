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
echo [1/5] Verificando Python 3.10+...
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

:: Atualiza explicitamente a variavel PATH no processo do CMD atual
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
python --version

:: ==============================================================================
:: 2. PREPARAR PASTA E BAIXAR VIA ZIP (SUBSTITUI O GIT)
:: ==============================================================================
echo [2/5] Preparando pasta e baixando arquivos...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Faz backup do venv se existir
if exist "%INSTALL_DIR%\venv" (
    echo Fazendo backup do ambiente virtual...
    xcopy "%INSTALL_DIR%\venv" "%TEMP%\cpfani_venv_backup\" /E /I /H /Y >nul
)

:: Remove arquivos antigos e FORCA o desbloqueio (resolve Permission Denied)
echo Limpando instalacao anterior e desbloqueando arquivos...
attrib -R "%INSTALL_DIR%\*.*" /S /D >nul 2>&1
rmdir /s /q "%INSTALL_DIR%" 2>nul
mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"

:: Baixa o ZIP mais recente do GitHub
echo Baixando pacote do GitHub...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/sunstrix/Disparador-de-emails-CP-FANI/archive/refs/heads/main.zip' -OutFile '%TEMP%\cpfani_main.zip' -UseBasicParsing"
if %errorlevel% neq 0 (
    echo Falha no download. Verifique sua conexao com a internet.
    pause
    exit /b 1
)

:: Extrai o ZIP
echo Extraindo arquivos...
powershell -Command "Expand-Archive -Path '%TEMP%\cpfani_main.zip' -DestinationPath '%TEMP%' -Force"

:: Move os arquivos da pasta extraida para a pasta de instalacao
move "%TEMP%\Disparador-de-emails-CP-FANI-main\*" "%INSTALL_DIR%" >nul 2>&1
move "%TEMP%\Disparador-de-emails-CP-FANI-main\.*" "%INSTALL_DIR%" >nul 2>&1

:: Limpa arquivos temporarios
del /F /Q "%TEMP%\cpfani_main.zip" >nul 2>&1
rmdir /s /q "%TEMP%\Disparador-de-emails-CP-FANI-main" >nul 2>&1

:: ==============================================================================
:: 3. AMBIENTE VIRTUAL E DEPENDENCIAS
:: ==============================================================================
echo [3/5] Configurando ambiente virtual...
cd /d "%INSTALL_DIR%"

:: Recria o venv do zero para evitar qualquer resquicio de permissao negada
echo Criando ambiente virtual limpo...
python -m venv venv

echo Instalando dependencias...
"venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
"venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo Falha ao instalar dependencias. Feche o VS Code ou Bloco de Notas e tente novamente.
    pause
    exit /b 1
)

:: ==============================================================================
:: 4. TRAVAR PERMISSOES DA PASTA (Seguranca/LGPD)
:: ==============================================================================
echo [4/5] Travando permissoes da pasta de instalacao...
icacls "%INSTALL_DIR%" /inheritance:r /grant "*S-1-5-32-544:(OI)(CI)F" /grant "*S-1-5-18:(OI)(CI)F" /grant "*S-1-5-32-545:(OI)(CI)RX" /T /Q

:: ==============================================================================
:: 5. CRIAR ATALHO NA AREA DE TRABALHO PUBLICA
:: ==============================================================================
echo [5/5] Criando atalho na area de trabalho...
set "DESKTOP_PUBLIC=C:\Users\Public\Desktop"
if not exist "%DESKTOP_PUBLIC%" set "DESKTOP_PUBLIC=%PUBLIC%\Desktop"

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP_PUBLIC%\Disparador de E-mails CP Fani.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\venv\Scripts\pythonw.exe'; $Shortcut.Arguments = 'main.py'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\ico\icone.ico,0'; $Shortcut.WindowStyle = 7; $Shortcut.Save()"

echo.
echo ============================================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo O atalho foi criado na area de trabalho publica.
echo Os dados do usuario serao salvos em: %LOCALAPPDATA%\CPFani
echo.

if "%UPDATE_MODE%"=="1" (
    echo Reiniciando o aplicativo...
    start "" "%INSTALL_DIR%\venv\Scripts\pythonw.exe" "main.py"
) else (
    pause
)