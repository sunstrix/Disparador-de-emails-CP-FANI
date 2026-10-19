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
set "LOG_FILE=%LOG_DIR%\instalar_%TIMESTAMP%.log"

echo ============================================================ > "%LOG_FILE%"
echo   LOG INSTALADOR - %TIMESTAMP% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

:: ==============================================================================
:: 0. PROTECAO CONTRA AUTO-DESTRUICAO
:: ==============================================================================
:: Verifica se o script esta sendo executado dentro da pasta de instalacao final
:: Se sim, aborta para evitar apagar os arquivos do projeto
for /f "delims=" %%i in ('powershell -NoProfile -Command "[System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::MyDocuments)"') do set "MY_DOCS=%%i"
if "%MY_DOCS%"=="" set "MY_DOCS=%USERPROFILE%\Documents"
set "INSTALL_DIR=%MY_DOCS%\Disparador de e-mails"

:: Normaliza os caminhos para comparacao (remove barras finais)
set "CURRENT_DIR=%CD%"
if "%CURRENT_DIR:~-1%"=="\" set "CURRENT_DIR=%CURRENT_DIR:~0,-1%"
if "%INSTALL_DIR:~-1%"=="\" set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"

if /I "%CURRENT_DIR%"=="%INSTALL_DIR%" (
    echo.
    echo ============================================================
    echo   ERRO: OPERACAO BLOQUEADA
    echo ============================================================
    echo.
    echo Este script (instalar.bat) NAO deve ser executado dentro da
    echo pasta de instalacao final:
    echo %INSTALL_DIR%
    echo.
    echo O instalar.bat e destinado apenas para DESENVOLVIMENTO LOCAL,
    echo quando voce tem o codigo fonte na pasta raiz do projeto.
    echo.
    echo Para USUARIOS FINAIS, utilize apenas o instalar_completo.bat
    echo que baixa o projeto do GitHub automaticamente.
    echo.
    echo Se voce precisa reinstalar, execute o instalar_completo.bat
    echo a partir da pasta onde ele esta localizado.
    echo.
    echo Log: %LOG_FILE%
    echo.
    pause
    exit /b 1
)

:: ==============================================================================
:: 1. RESOLVER INSTALL_DIR DINAMICAMENTE (MEUS DOCUMENTOS)
:: ==============================================================================
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
echo   INSTALADOR - DISPARADOR DE E-MAILS CP FANI
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
:: 3. PREPARAR PASTA (LIMPEZA SEGURA E SEM BLOQUEIO) E BAIXAR VIA ZIP
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
cd /d "%TEMP%"
if exist "%INSTALL_DIR%" (
    taskkill /f /im pythonw.exe >nul 2>&1
    taskkill /f /im python.exe >nul 2>&1
    timeout /t 2 /nobreak >nul
    attrib -R "%INSTALL_DIR%\*.*" /S /D >nul 2>&1
    for /d %%p in ("%INSTALL_DIR%\*") do rmdir /s /q "%%p" 2>nul
    del /f /q /s "%INSTALL_DIR%\*" >nul 2>&1
)
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"
echo Pasta limpa e recriada com sucesso >> "%LOG_FILE%"

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

:: Mover todos os arquivos e subpastas recursivamente com Robocopy
robocopy "%TEMP%\cpfani_extracted\Disparador-de-emails-CP-FANI-main" "%INSTALL_DIR%" /E /MOVE >nul 2>&1
del /F /Q "%TEMP%\cpfani_main.zip" >nul 2>&1
if exist "%TEMP%\cpfani_extracted" rmdir /s /q "%TEMP%\cpfani_extracted" 2>nul

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
:: 5. TESTAR VENV / RESTAURAR BACKUP / RECRIAR
:: ==============================================================================
echo.
echo [4/6] Testando ambiente virtual...
call :TESTAR_VENV
if not errorlevel 1 goto :venv_ok

echo Venv invalido. Tentando restaurar backup...
echo Venv invalido; tentando restaurar backup >> "%LOG_FILE%"
if exist "%TEMP%\cpfani_venv_backup" (
    attrib -R "venv\*.*" /S /D >nul 2>&1
    rmdir /s /q "venv" 2>nul
    xcopy "%TEMP%\cpfani_venv_backup" "venv\" /E /I /H /Y >nul
    rmdir /s /q "%TEMP%\cpfani_venv_backup" 2>nul
    call :TESTAR_VENV
    if not errorlevel 1 goto :venv_ok
    echo Backup restaurado tambem falhou no teste >> "%LOG_FILE%"
)

echo Backup indisponivel ou invalido. Recriando venv do zero com Python 3.12...
echo Recriando venv do zero >> "%LOG_FILE%"
attrib -R "venv\*.*" /S /D >nul 2>&1
rmdir /s /q "venv" 2>nul
%PY_CMD% -m venv venv >> "%LOG_FILE%" 2>&1
"venv\Scripts\python.exe" -m ensurepip --upgrade --default-pip >> "%LOG_FILE%" 2>&1
"venv\Scripts\python.exe" -m pip install --upgrade pip --quiet >> "%LOG_FILE%" 2>&1
"venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet >> "%LOG_FILE%" 2>&1

call :TESTAR_VENV
if errorlevel 1 (
    echo ERRO: venv inutilizavel apos recriacao >> "%LOG_FILE%"
    echo ERRO: ambiente virtual inutilizavel apos recriacao.
    pause
    exit /b 1
)

:venv_ok
echo Ambiente virtual valido. >> "%LOG_FILE%"
echo Ambiente virtual valido.

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

echo Todos os arquivos criticos presentes. >> "%LOG_FILE%"
echo Todos os arquivos criticos presentes.

:: ==============================================================================
:: 7. CRIAR ATALHOS (PER-USER, SEM ADMIN)
:: ==============================================================================
echo.
echo [6/6] Criando atalhos...
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

:: ==============================================================================
:: SUBROTINA: TESTA VENV (PYTHON + PIP)
:: ==============================================================================
:TESTAR_VENV
"venv\Scripts\python.exe" --version >nul 2>&1
if errorlevel 1 exit /b 1
"venv\Scripts\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 exit /b 1
exit /b 0