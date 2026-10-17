@echo off
chcp 65001 >nul
title Instalador Completo - Disparador de E-mails CP Fani
color 0A

:: ==============================================================================
:: CONFIGURACAO DE VARIAVEIS E LOGS
:: ==============================================================================
set "LOG_DIR=%LOCALAPPDATA%\CPFani\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\instalar_completo_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log"
set "LOG_FILE=%LOG_FILE: =0%"

:: ==============================================================================
:: 1. RESOLVER INSTALL_DIR DINAMICAMENTE (MEUS DOCUMENTOS)
:: ==============================================================================
for /f "delims=" %%i in ('powershell -Command "[Environment]::GetFolderPath([Environment+SpecialFolder]::MyDocuments)"') do set "MY_DOCS=%%i"
set "INSTALL_DIR=%MY_DOCS%\Disparador de e-mails"

:: Detectar redirecionamento OneDrive
echo "%INSTALL_DIR%" | findstr /I "OneDrive" >nul
if not errorlevel 1 (
    echo.
    echo AVISO: Sua pasta Documentos esta no OneDrive:
    echo %INSTALL_DIR%
    echo.
    echo O OneDrive pode travar arquivos do ambiente virtual e causar erros de acesso.
    echo.
    echo Deseja instalar no OneDrive mesmo assim?
    echo.
    echo [1] Sim, instalar em Documentos (OneDrive)
    echo [2] Nao, instalar em %USERPROFILE%\Disparador de e-mails
    echo.
    set /p "CHOICE=Escolha (1 ou 2): "
    if not "%CHOICE%"=="1" (
        set "INSTALL_DIR=%USERPROFILE%\Disparador de e-mails"
    )
)

set "UPDATE_MODE=0"
if "%~1"=="/atualizar" set "UPDATE_MODE=1"

echo ============================================================
echo   INSTALADOR COMPLETO - DISPARADOR DE E-MAILS CP FANI
echo   Pasta de destino: %INSTALL_DIR%
echo ============================================================
echo Log: %LOG_FILE%
echo.

:: ==============================================================================
:: 2. VERIFICAR/INSTALAR PYTHON
:: ==============================================================================
echo [1/6] Verificando Python 3.10+...
python --version >nul 2>&1
if not errorlevel 1 (
    python --version
) else (
    echo Python nao encontrado. Tentando instalar via winget...
    winget install --id Python.Python.3.12 -e --scope user --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
    if errorlevel 1 (
        echo Falha ao instalar via winget. Por favor, instale o Python manualmente.
        echo Falha ao instalar Python via winget >> "%LOG_FILE%"
        pause
        exit /b 1
    )
    echo Python instalado com sucesso via winget.
    echo Python instalado via winget >> "%LOG_FILE%"
    
    :: Atualizar PATH do processo atual
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
    python --version
)

:: ==============================================================================
:: 3. PREPARAR PASTA E BAIXAR VIA ZIP
:: ==============================================================================
echo.
echo [2/6] Preparando pasta e baixando arquivos...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

if exist "%INSTALL_DIR%\venv" (
    echo Fazendo backup do ambiente virtual...
    xcopy "%INSTALL_DIR%\venv" "%TEMP%\cpfani_venv_backup\" /E /I /H /Y >nul
    echo Backup do venv realizado >> "%LOG_FILE%"
)

echo Limpando instalacao anterior...
attrib -R "%INSTALL_DIR%\*.*" /S /D >nul 2>&1
rmdir /s /q "%INSTALL_DIR%" 2>nul
mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"

echo Baixando pacote do GitHub...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/sunstrix/Disparador-de-emails-CP-FANI/archive/refs/heads/main.zip' -OutFile '%TEMP%\cpfani_main.zip' -UseBasicParsing"
if errorlevel 1 (
    echo Falha no download. Verifique sua conexao.
    echo Falha no download do ZIP >> "%LOG_FILE%"
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
:: 4. AMBIENTE VIRTUAL E DEPENDENCIAS
:: ==============================================================================
echo.
echo [3/6] Configurando ambiente virtual...
cd /d "%INSTALL_DIR%"

echo Criando ambiente virtual limpo...
python -m venv venv
if errorlevel 1 (
    echo Falha ao criar ambiente virtual >> "%LOG_FILE%"
    echo Falha ao criar ambiente virtual.
    pause
    exit /b 1
)

echo Instalando dependencias...
"venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
"venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo Falha ao instalar dependencias >> "%LOG_FILE%"
    echo Falha ao instalar dependencias.
    pause
    exit /b 1
)

:: ==============================================================================
:: 5. TESTAR AMBIENTE VIRTUAL (BACKUP/RESTAURACAO)
:: ==============================================================================
echo.
echo [4/6] Testando ambiente virtual...
"venv\Scripts\python.exe" --version >nul 2>&1
if errorlevel 1 (
    echo Python do venv falhou. Tentando restaurar backup...
    echo Venv falhou, restaurando backup >> "%LOG_FILE%"
    
    if exist "%TEMP%\cpfani_venv_backup" (
        attrib -R "%INSTALL_DIR%\venv\*.*" /S /D >nul 2>&1
        rmdir /s /q "%INSTALL_DIR%\venv" 2>nul
        xcopy "%TEMP%\cpfani_venv_backup" "%INSTALL_DIR%\venv\" /E /I /H /Y >nul
        rmdir /s /q "%TEMP%\cpfani_venv_backup"
        
        "venv\Scripts\python.exe" --version >nul 2>&1
        if errorlevel 1 (
            echo Backup tambem falhou. Recriando venv do zero...
            echo Backup falhou, recriando venv >> "%LOG_FILE%"
            attrib -R "%INSTALL_DIR%\venv\*.*" /S /D >nul 2>&1
            rmdir /s /q "%INSTALL_DIR%\venv" 2>nul
            python -m venv venv
            "venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
            "venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
        )
    ) else (
        echo Sem backup. Recriando venv do zero...
        echo Sem backup, recriando venv >> "%LOG_FILE%"
        attrib -R "%INSTALL_DIR%\venv\*.*" /S /D >nul 2>&1
        rmdir /s /q "%INSTALL_DIR%\venv" 2>nul
        python -m venv venv
        "venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
        "venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
    )
)

:: ==============================================================================
:: 6. VERIFICACAO FINAL POS-INSTALACAO
:: ==============================================================================
echo.
echo [5/6] Verificacao final...
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

echo Todos os arquivos criticos presentes.

:: ==============================================================================
:: 7. CRIAR ATALHO (PER-USER, SEM ADMIN)
:: ==============================================================================
echo.
echo [6/6] Criando atalho na area de trabalho...
set "DESKTOP_USER=%USERPROFILE%\Desktop"

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP_USER%\Disparador de E-mails CP Fani.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\venv\Scripts\pythonw.exe'; $Shortcut.Arguments = 'main.py'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = 'shell32.dll,134'; $Shortcut.WindowStyle = 7; $Shortcut.Save()"

echo Atalho criado em: %DESKTOP_USER%\Disparador de E-mails CP Fani.lnk
echo Atalho criado no desktop do usuario >> "%LOG_FILE%"

:: Atalho opcional no Menu Iniciar (per-user)
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
if not exist "%START_MENU%" mkdir "%START_MENU%"

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%START_MENU%\Disparador de E-mails CP Fani.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\venv\Scripts\pythonw.exe'; $Shortcut.Arguments = 'main.py'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = 'shell32.dll,134'; $Shortcut.WindowStyle = 7; $Shortcut.Save()"

echo Atalho criado em: %START_MENU%\Disparador de E-mails CP Fani.lnk
echo Atalho criado no Menu Iniciar >> "%LOG_FILE%"

:: ==============================================================================
:: CONCLUSAO
:: ==============================================================================
echo.
echo ============================================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo Pasta de instalacao: %INSTALL_DIR%
echo Logs: %LOG_DIR%
echo.

if "%UPDATE_MODE%"=="1" (
    echo Reiniciando o aplicativo...
    echo Modo atualizacao - reiniciando app >> "%LOG_FILE%"
    start "" "%INSTALL_DIR%\venv\Scripts\pythonw.exe" "main.py"
) else (
    pause
)