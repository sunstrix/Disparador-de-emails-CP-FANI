@echo off
chcp 65001 >nul
setlocal EnableExtensions
title Instalador - Disparador de E-mails CP Fani
color 0A
cd /d "%~dp0"

:: ==============================================================================
:: CONFIGURACAO DE VARIAVEIS E LOGS
:: ==============================================================================
set "LOG_DIR=%LOCALAPPDATA%\CPFani\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set TIMESTAMP=%%I
set "LOG_FILE=%LOG_DIR%\instalar_completo_%TIMESTAMP%.log"

echo ============================================================ > "%LOG_FILE%"
echo   LOG INSTALADOR COMPLETO - %TIMESTAMP% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

:: ==============================================================================
:: 1. RESOLVER INSTALL_DIR DINAMICAMENTE (MEUS DOCUMENTOS)
:: ==============================================================================
for /f "delims=" %%i in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::MyDocuments)"') do set "MY_DOCS=%%i"
if "%MY_DOCS%"=="" set "MY_DOCS=%USERPROFILE%\Documents"
set "INSTALL_DIR=%MY_DOCS%\Disparador de e-mails"

echo "%INSTALL_DIR%" | findstr /I "OneDrive" >nul
if errorlevel 1 goto :sem_onedrive

echo.
echo AVISO: Sua pasta Documentos esta no OneDrive:
echo %INSTALL_DIR%
echo.
echo O OneDrive pode travar arquivos do ambiente virtual e causar erros de acesso.
echo.
echo [1] Sim, instalar em Documentos (OneDrive)
echo [2] Nao, instalar em %USERPROFILE%\Disparador de e-mails
echo.
set /p "CHOICE=Escolha (1 ou 2): "
echo Escolha do usuario: %CHOICE% >> "%LOG_FILE%"
if "%CHOICE%"=="1" goto :sem_onedrive
set "INSTALL_DIR=%USERPROFILE%\Disparador de e-mails"

:sem_onedrive
set "UPDATE_MODE=0"
if "%~1"=="/atualizar" set "UPDATE_MODE=1"

echo ============================================================
echo   INSTALADOR COMPLETO - DISPARADOR DE E-MAILS CP FANI
echo   Pasta de destino: %INSTALL_DIR%
echo ============================================================
echo Log: %LOG_FILE%
echo.
echo INSTALL_DIR: %INSTALL_DIR% >> "%LOG_FILE%"

:: ==============================================================================
:: 2. VERIFICAR/INSTALAR PYTHON 3.12 (64-BIT)
:: ==============================================================================
echo [1/6] Verificando Python 3.12...
set "PY_CMD="

py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3.12"
    goto :python_encontrado
)

python --version 2>&1 | findstr /C:"3.12" >nul
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :python_encontrado
)

echo Python 3.12 nao encontrado. Tentando instalar via winget...
winget install --id Python.Python.3.12 -e --scope user --silent --accept-package-agreements --accept-source-agreements >> "%LOG_FILE%" 2>&1

py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3.12"
    goto :python_encontrado
)

set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
python --version 2>&1 | findstr /C:"3.12" >nul
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :python_encontrado
)

echo ERRO: Python 3.12 nao encontrado. >> "%LOG_FILE%"
echo.
echo ERRO: O Python 3.12 (64-bit) e necessario para garantir a compatibilidade de wheels.
echo Por favor, instale o Python 3.12 e execute este instalador novamente.
pause
exit /b 1

:python_encontrado
echo Comando Python selecionado: %PY_CMD%
echo Python selecionado: %PY_CMD% >> "%LOG_FILE%"
%PY_CMD% --version >> "%LOG_FILE%" 2>&1

:: ==============================================================================
:: 3. PREPARAR PASTA E BAIXAR VIA ZIP COM ROBOCOPY RECURSIVO
:: ==============================================================================
echo.
echo [2/6] Preparando pasta e baixando arquivos...

if exist "%INSTALL_DIR%\venv" (
    echo Fazendo backup do ambiente virtual...
    if exist "%TEMP%\cpfani_venv_backup" rmdir /s /q "%TEMP%\cpfani_venv_backup" 2>nul
    xcopy "%INSTALL_DIR%\venv" "%TEMP%\cpfani_venv_backup\" /E /I /H /Y >nul 2>&1
    echo Backup do venv realizado >> "%LOG_FILE%"
)

echo Limpando instalacao anterior...
attrib -R "%INSTALL_DIR%\*.*" /S /D >nul 2>&1
rmdir /s /q "%INSTALL_DIR%" 2>nul

if exist "%INSTALL_DIR%" (
    echo Pasta ainda bloqueada. Encerrando processos Python do aplicativo...
    echo Primeira tentativa de rmdir falhou; executando taskkill >> "%LOG_FILE%"
    taskkill /f /im pythonw.exe >nul 2>&1
    taskkill /f /im python.exe >nul 2>&1
    timeout /t 3 /nobreak >nul
    attrib -R "%INSTALL_DIR%\*.*" /S /D >nul 2>&1
    rmdir /s /q "%INSTALL_DIR%" 2>nul
)

if exist "%INSTALL_DIR%" (
    echo ERRO: nao foi possivel remover %INSTALL_DIR% >> "%LOG_FILE%"
    echo.
    echo ERRO: nao foi possivel limpar a pasta de instalacao.
    pause
    exit /b 1
)

mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"

echo Baixando pacote do GitHub...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://github.com/sunstrix/Disparador-de-emails-CP-FANI/archive/refs/heads/main.zip' -OutFile '%TEMP%\cpfani_main.zip' -UseBasicParsing"
if errorlevel 1 (
    echo Falha no download do ZIP >> "%LOG_FILE%"
    echo Falha no download. Verifique sua conexao.
    pause
    exit /b 1
)

echo Extraindo arquivos...
if exist "%TEMP%\cpfani_extracted" rmdir /s /q "%TEMP%\cpfani_extracted" 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%TEMP%\cpfani_main.zip' -DestinationPath '%TEMP%\cpfani_extracted' -Force"
if errorlevel 1 (
    echo Falha ao extrair o ZIP >> "%LOG_FILE%"
    echo Falha ao extrair os arquivos.
    pause
    exit /b 1
)

:: Copia todos os arquivos e pastas extraidos usando Robocopy
robocopy "%TEMP%\cpfani_extracted\Disparador-de-emails-CP-FANI-main" "%INSTALL_DIR%" /E /MOVE >nul 2>&1
del /F /Q "%TEMP%\cpfani_main.zip" >nul 2>&1
rmdir /s /q "%TEMP%\cpfani_extracted" 2>nul

:: ==============================================================================
:: 4. AMBIENTE VIRTUAL LIMPO + PIP GARANTIDO (PYTHON 3.12)
:: ==============================================================================
echo.
echo [3/6] Configurando ambiente virtual (Python 3.12)...
cd /d "%INSTALL_DIR%"

if exist "venv" (
    attrib -R "venv\*.*" /S /D >nul 2>&1
    rmdir /s /q "venv" 2>nul
)

echo Criando ambiente virtual limpo com Python 3.12...
%PY_CMD% -m venv venv >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo Falha ao criar ambiente virtual >> "%LOG_FILE%"
    echo Falha ao criar ambiente virtual.
    pause
    exit /b 1
)

echo Garantindo pip no ambiente virtual...
"venv\Scripts\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip ausente no venv; executando ensurepip >> "%LOG_FILE%"
    "venv\Scripts\python.exe" -m ensurepip --upgrade --default-pip >> "%LOG_FILE%" 2>&1
)

echo Instalando dependencias...
"venv\Scripts\python.exe" -m pip install --upgrade pip --quiet >> "%LOG_FILE%" 2>&1
"venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo Falha ao instalar dependencias >> "%LOG_FILE%"
    echo Falha ao instalar dependencias.
    pause
    exit /b 1
)

:: ==============================================================================
:: 5. VERIFICACAO FINAL POS-INSTALACAO
:: ==============================================================================
echo.
echo [4/6] Verificacao final...
set "MISSING=0"

if not exist "main.py" (
    echo ERRO: main.py nao encontrado!
    echo main.py ausente >> "%LOG_FILE%"
    set "MISSING=1"
)
if not exist "requirements.txt" (
    echo ERRO: requirements.txt nao encontrado!
    echo requirements.txt ausente >> "%LOG_FILE%"
    set "MISSING=1"
)
if not exist "executar.bat" (
    echo ERRO: executar.bat nao encontrado!
    echo executar.bat ausente >> "%LOG_FILE%"
    set "MISSING=1"
)
if not exist "venv\Scripts\pythonw.exe" (
    echo ERRO: venv\Scripts\pythonw.exe nao encontrado!
    echo pythonw.exe ausente >> "%LOG_FILE%"
    set "MISSING=1"
)

if "%MISSING%"=="1" (
    echo.
    echo Arquivos criticos ausentes. Verifique o log.
    pause
    exit /b 1
)

echo Todos os arquivos criticos presentes. >> "%LOG_FILE%"
echo Todos os arquivos criticos presentes.

:: ==============================================================================
:: 6. CRIAR ATALHOS (PER-USER, SEM ADMIN)
:: ==============================================================================
echo.
echo [5/6] Criando atalhos...
set "DESKTOP_USER=%USERPROFILE%\Desktop"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP_USER%\Disparador de E-mails CP Fani.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\venv\Scripts\pythonw.exe'; $Shortcut.Arguments = 'main.py'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = 'shell32.dll,134'; $Shortcut.WindowStyle = 7; $Shortcut.Save()"
echo Atalho criado em: %DESKTOP_USER% >> "%LOG_FILE%"

set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
if not exist "%START_MENU%" mkdir "%START_MENU%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%START_MENU%\Disparador de E-mails CP Fani.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\venv\Scripts\pythonw.exe'; $Shortcut.Arguments = 'main.py'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = 'shell32.dll,134'; $Shortcut.WindowStyle = 7; $Shortcut.Save()"
echo Atalho criado no Menu Iniciar >> "%LOG_FILE%"

echo.
echo ============================================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo Pasta de instalacao: %INSTALL_DIR%
echo Logs: %LOG_DIR%
echo.
echo INSTALACAO CONCLUIDA COM SUCESSO >> "%LOG_FILE%"

if "%UPDATE_MODE%"=="1" (
    echo Reiniciando o aplicativo...
    start "" "%INSTALL_DIR%\venv\Scripts\pythonw.exe" "main.py"
) else (
    pause
)
exit /b 0