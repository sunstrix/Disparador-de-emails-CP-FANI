@echo off
setlocal EnableExtensions
title Instalador Completo - Disparador de E-mails CP FANI

:: ==============================================================================
:: CONFIGURACAO DE LOGS E VARIAVEIS INICIAIS
:: ==============================================================================
set "LOG_DIR=%LOCALAPPDATA%\CPFani\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set "TIMESTAMP=%%I"
set "LOG_FILE=%LOG_DIR%\instalar_completo_%TIMESTAMP%.log"

echo ============================================================ > "%LOG_FILE%"
echo   LOG INSTALADOR COMPLETO - %TIMESTAMP% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

:: Parse de argumentos (/atualizar, /dir:"...", /pid:..., /copied)
set "UPDATE_MODE=0"
set "ARG_DIR="
set "ARG_PID="
set "IS_COPIED=0"

:parse_args
if "%~1"=="" goto :end_parse_args
if /i "%~1"=="/atualizar" set "UPDATE_MODE=1"
if /i "%~1"=="/copied" set "IS_COPIED=1"
set "ARG_PARAM=%~1"
if /i "%ARG_PARAM:~0,5%"=="/dir:" set "ARG_DIR=%ARG_PARAM:~5%"
if /i "%ARG_PARAM:~0,5%"=="/pid:" set "ARG_PID=%ARG_PARAM:~5%"
shift
goto :parse_args
:end_parse_args

:: Se estiver em modo de atualizacao e nao tiver sido copiado ainda para %TEMP%
if "%UPDATE_MODE%"=="1" if "%IS_COPIED%"=="0" goto :self_copy_temp

goto :main_process

:self_copy_temp
set "TEMP_SCRIPT=%TEMP%\cpfani_installer_%TIMESTAMP%_%RANDOM%.bat"
copy /y "%~f0" "%TEMP_SCRIPT%" >nul
if errorlevel 1 (
    echo [ERRO] Falha ao copiar instalador para pasta temporaria. >> "%LOG_FILE%"
    goto :fatal_error
)
echo Copiado para %TEMP_SCRIPT% para permitir atualizacao de arquivos em uso. >> "%LOG_FILE%"
start "" "%TEMP_SCRIPT%" /copied /atualizar /dir:"%ARG_DIR%" /pid:%ARG_PID%
exit /b 0

:main_process

:: ==============================================================================
:: 1. DEFINICAO DA PASTA DE INSTALACAO (INSTALL_DIR)
:: ==============================================================================
if not "%ARG_DIR%"=="" (
    set "INSTALL_DIR=%ARG_DIR%"
    goto :dir_definido
)

for /f "delims=" %%I in ('powershell -NoProfile -Command "[Environment]::GetFolderPath([Environment+SpecialFolder]::MyDocuments)"') do set "MY_DOCS=%%I"
if "%MY_DOCS%"=="" set "MY_DOCS=%USERPROFILE%\Documents"
set "INSTALL_DIR=%MY_DOCS%\Disparador de e-mails"

if "%UPDATE_MODE%"=="1" goto :dir_definido

echo "%INSTALL_DIR%" | findstr /I "OneDrive" >nul
if errorlevel 1 goto :dir_definido

echo.
echo AVISO: Sua pasta Documentos esta sincronizada no OneDrive:
echo %INSTALL_DIR%
echo.
echo O OneDrive pode travar arquivos do ambiente virtual e gerar erros.
echo.
echo [1] Instalar em Documentos (OneDrive)
echo [2] Instalar em %USERPROFILE%\Disparador de e-mails
echo.
choice /c 12 /m "Escolha uma opcao:"
if errorlevel 2 set "INSTALL_DIR=%USERPROFILE%\Disparador de e-mails"

:dir_definido
echo INSTALL_DIR: %INSTALL_DIR% >> "%LOG_FILE%"
echo UPDATE_MODE: %UPDATE_MODE% >> "%LOG_FILE%"

echo ============================================================
echo   INSTALADOR COMPLETO - DISPARADOR DE E-MAILS CP FANI
echo   Pasta de destino: %INSTALL_DIR%
echo ============================================================
echo Log de instalacao: %LOG_FILE%
echo.

:: ==============================================================================
:: 2. AGUARDAR / ENCERRAR PROCESSO ANTERIOR (SE PASSADO PID OU ARQUIVOS EM USO)
:: ==============================================================================
if not "%ARG_PID%"=="" (
    echo Aguardando encerramento do processo anterior (PID %ARG_PID%)...
    powershell -NoProfile -Command "$pidNum = [int]'%ARG_PID%'; $timeout = 60; $elapsed = 0; while ((Get-Process -Id $pidNum -ErrorAction SilentlyContinue) -and ($elapsed -lt $timeout)) { Start-Sleep -Seconds 1; $elapsed++ }" >> "%LOG_FILE%" 2>&1
)

:: Encerrar somente processos Python rodando DENTRO da pasta INSTALL_DIR (se houver)
powershell -NoProfile -Command "$dir = $env:INSTALL_DIR; Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($dir, [System.StringComparison]::OrdinalIgnoreCase) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >> "%LOG_FILE%" 2>&1

:: ==============================================================================
:: 3. VERIFICACAO E CONFIGURACAO DO PYTHON (3.10 A 3.13)
:: ==============================================================================
echo [1/5] Verificando ambiente Python...
set "PY_EXE="

call :detect_python
if not "%PY_EXE%"=="" goto :python_pronto

echo Python compativel nao encontrado (3.10 a 3.13). Tentando instalar via winget...
winget install --id Python.Python.3.12 -e --scope user --silent --accept-package-agreements --accept-source-agreements >> "%LOG_FILE%" 2>&1

call :detect_python
if not "%PY_EXE%"=="" goto :python_pronto

echo Instalacao via winget falhou ou nao disponivel. Tentando instalador oficial...
set "PY_INSTALLER=%TEMP%\python-3.12.8-amd64.exe"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe', '$env:PY_INSTALLER')" >> "%LOG_FILE%" 2>&1

if exist "%PY_INSTALLER%" (
    "%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 SimpleInstall=1 >> "%LOG_FILE%" 2>&1
    del /f /q "%PY_INSTALLER%" >nul 2>&1
)

call :detect_python
if not "%PY_EXE%"=="" goto :python_pronto

echo [ERRO] Nao foi possivel localizar ou instalar o Python (3.10 a 3.13). >> "%LOG_FILE%"
echo ERRO: Python 3.10+ nao foi encontrado no sistema. Por favor instale o Python 3.12 manualmente.
goto :fatal_error

:python_pronto
echo Python utilizado: %PY_EXE% >> "%LOG_FILE%"
echo Python localizado: %PY_EXE%

:: ==============================================================================
:: 4. DOWNLOAD E EXTRAÇÃO DO CÓDIGO FONTE (ZIP GITHUB)
:: ==============================================================================
echo.
echo [2/5] Baixando pacote do GitHub...

set "WORK_TEMP=%TEMP%\cpfani_%TIMESTAMP%_%RANDOM%"
mkdir "%WORK_TEMP%" >nul 2>&1
set "ZIP_FILE=%WORK_TEMP%\main.zip"

powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $web = New-Object System.Net.WebClient; $web.Timeout = 30000; try { $web.DownloadFile('https://github.com/sunstrix/Disparador-de-emails-CP-FANI/archive/refs/heads/main.zip', '$env:ZIP_FILE'); } catch { Write-Error $_.Exception.Message; exit 1; }" >> "%LOG_FILE%" 2>&1

if errorlevel 1 (
    echo [ERRO] Falha no download do pacote ZIP do GitHub. >> "%LOG_FILE%"
    echo ERRO: Falha ao baixar o arquivo da aplicacao. Verifique sua conexao de rede.
    goto :cleanup_work_dir
)

if not exist "%ZIP_FILE%" (
    echo [ERRO] Arquivo ZIP nao foi gerado. >> "%LOG_FILE%"
    goto :cleanup_work_dir
)

echo Extraindo arquivos do pacote...
powershell -NoProfile -Command "try { Expand-Archive -Path '$env:ZIP_FILE' -DestinationPath '$env:WORK_TEMP\extracted' -Force } catch { exit 1 }" >> "%LOG_FILE%" 2>&1

if errorlevel 1 (
    echo [ERRO] Falha ao extrair arquivo ZIP. >> "%LOG_FILE%"
    goto :cleanup_work_dir
)

for /d %%D in ("%WORK_TEMP%\extracted\*") do set "EXTRACT_DIR=%%D"

if not exist "%EXTRACT_DIR%\main.py" (
    echo [ERRO] Arquivos extraidos incompletos ou main.py ausente. >> "%LOG_FILE%"
    goto :cleanup_work_dir
)

echo Sincronizando codigo-fonte para %INSTALL_DIR%...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%" >nul 2>&1

robocopy "%EXTRACT_DIR%" "%INSTALL_DIR%" /E /NP /R:2 /W:1 /LOG+:"%LOG_FILE%" >nul
if errorlevel 8 (
    echo [ERRO] Robocopy retornou erro grave ao copiar arquivos. >> "%LOG_FILE%"
    goto :cleanup_work_dir
)

:: Limpeza do diretorio de trabalho temporario
:cleanup_work_dir
if exist "%WORK_TEMP%" rmdir /s /q "%WORK_TEMP%" >nul 2>&1

if not exist "%INSTALL_DIR%\main.py" (
    echo ERRO: Falha na sincronizacao do codigo-fonte. >> "%LOG_FILE%"
    goto :fatal_error
)

:: ==============================================================================
:: 5. CONFIGURACAO E MANUTENCAO DO AMBIENTE VIRTUAL (VENV)
:: ==============================================================================
echo.
echo [3/5] Configurando ambiente virtual (venv)...
cd /d "%INSTALL_DIR%"

set "VENV_DIR=%INSTALL_DIR%\venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "NEED_REQ_INSTALL=1"

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys" >nul 2>&1
    if not errorlevel 1 goto :venv_valido
)

echo Ambiente virtual ausente ou corrompido. Criando novo venv... >> "%LOG_FILE%"
if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%" >nul 2>&1

"%PY_EXE%" -m venv "%VENV_DIR%" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [ERRO] Falha ao criar ambiente virtual com %PY_EXE%. >> "%LOG_FILE%"
    goto :fatal_error
)

:venv_valido
"%VENV_PY%" -m ensurepip --upgrade --default-pip >> "%LOG_FILE%" 2>&1

:: Verificar se requirements.txt mudou via hash SHA256
set "REQ_HASH_FILE=%VENV_DIR%\.req_hash"
set "CURRENT_REQ_HASH="

for /f "delims=" %%H in ('powershell -NoProfile -Command "Get-FileHash -Algorithm SHA256 -Path '%INSTALL_DIR%\requirements.txt' | Select-Object -ExpandProperty Hash"') do set "CURRENT_REQ_HASH=%%H"

if exist "%REQ_HASH_FILE%" (
    set /p OLD_REQ_HASH=<"%REQ_HASH_FILE%"
    if "%CURRENT_REQ_HASH%"=="%OLD_REQ_HASH%" (
        echo Dependencias inalteradas. Pulando instalacao via pip. >> "%LOG_FILE%"
        set "NEED_REQ_INSTALL=0"
    )
)

if "%NEED_REQ_INSTALL%"=="1" (
    echo Instalando / atualizando dependencias no venv...
    "%VENV_PY%" -m pip install --upgrade pip --quiet >> "%LOG_FILE%" 2>&1
    "%VENV_PY%" -m pip install -r requirements.txt --quiet >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo [ERRO] Falha na instalacao de dependencias via pip. >> "%LOG_FILE%"
        goto :fatal_error
    )
    if not "%CURRENT_REQ_HASH%"=="" echo %CURRENT_REQ_HASH%>"%REQ_HASH_FILE%"
)

:: ==============================================================================
:: 6. VERIFICACAO INTEGRAL POS-INSTALACAO
:: ==============================================================================
echo.
echo [4/5] Executando verificacao de integridade...

set "MISSING_FILES=0"
if not exist "%INSTALL_DIR%\main.py" set "MISSING_FILES=1"
if not exist "%INSTALL_DIR%\requirements.txt" set "MISSING_FILES=1"
if not exist "%INSTALL_DIR%\executar.bat" set "MISSING_FILES=1"
if not exist "%INSTALL_DIR%\version.txt" set "MISSING_FILES=1"
if not exist "%INSTALL_DIR%\ico\icone.ico" set "MISSING_FILES=1"
if not exist "%INSTALL_DIR%\logo\logo.png" set "MISSING_FILES=1"
if not exist "%INSTALL_DIR%\app\ui\main_window.py" set "MISSING_FILES=1"
if not exist "%INSTALL_DIR%\app\core\sender_worker.py" set "MISSING_FILES=1"

if "%MISSING_FILES%"=="1" (
    echo [ERRO] Arquivos estruturais ausentes apos instalacao. >> "%LOG_FILE%"
    goto :fatal_error
)

"%VENV_PY%" -c "import PySide6, pandas, openpyxl, keyring" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [ERRO] Teste de importacao de bibliotecas no venv falhou. >> "%LOG_FILE%"
    goto :fatal_error
)

echo Integridade e bibliotecas verificadas com sucesso. >> "%LOG_FILE%"

:: ==============================================================================
:: 7. CRIACAO DE ATALHOS (SEM ADMIN, COM ICONE E D'AVILA SAFE)
:: ==============================================================================
echo.
echo [5/5] Criando atalhos no sistema...

set "CPFANI_INSTALL_DIR=%INSTALL_DIR%"

powershell -NoProfile -Command ^
    "$dir = $env:CPFANI_INSTALL_DIR; " ^
    "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
    "$startMenu = [Environment]::GetFolderPath('StartMenu') + '\Programs'; " ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$scDesktop = $ws.CreateShortcut(\"$desktop\Disparador de E-mails CP Fani.lnk\"); " ^
    "$scDesktop.TargetPath = \"$dir\executar.bat\"; " ^
    "$scDesktop.WorkingDirectory = \"$dir\"; " ^
    "$scDesktop.IconLocation = \"$dir\ico\icone.ico,0\"; " ^
    "$scDesktop.WindowStyle = 7; " ^
    "$scDesktop.Save(); " ^
    "$scStart = $ws.CreateShortcut(\"$startMenu\Disparador de E-mails CP Fani.lnk\"); " ^
    "$scStart.TargetPath = \"$dir\executar.bat\"; " ^
    "$scStart.WorkingDirectory = \"$dir\"; " ^
    "$scStart.IconLocation = \"$dir\ico\icone.ico,0\"; " ^
    "$scStart.WindowStyle = 7; " ^
    "$scStart.Save();" >> "%LOG_FILE%" 2>&1

echo ============================================================
echo   INSTALACAO / ATUALIZACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo Pasta de instalacao: %INSTALL_DIR%
echo Logs: %LOG_FILE%
echo.

if "%UPDATE_MODE%"=="1" (
    echo Reiniciando o aplicativo...
    start "" "%INSTALL_DIR%\executar.bat"
    exit /b 0
)

pause
exit /b 0

:: ==============================================================================
:: SUB-ROTINAS DE SUPORTE
:: ==============================================================================

:detect_python
:: Procura interpretadores Python validos (3.10 a 3.13) via launcher py ou PATH
set "PY_EXE="
for %%V in (3.12 3.11 3.10 3.13) do (
    if "%PY_EXE%"=="" (
        for /f "delims=" %%P in ('py -%%V -c "import sys; print(sys.executable)" 2^>nul') do (
            echo "%%P" | findstr /i "WindowsApps" >nul
            if errorlevel 1 set "PY_EXE=%%P"
        )
    )
)
if not "%PY_EXE%"=="" exit /b 0

for /f "delims=" %%P in ('python -c "import sys; print(sys.executable) if sys.version_info >= (3,10) and sys.version_info < (3,14) else None" 2^>nul') do (
    echo "%%P" | findstr /i "WindowsApps" >nul
    if errorlevel 1 set "PY_EXE=%%P"
)
exit /b 0

:fatal_error
echo.
echo ============================================================
echo   ERRO CRITICO DURANTE A INSTALACAO
echo ============================================================
echo Ocorreu um erro ao instalar ou atualizar o aplicativo.
echo Consulte o arquivo de log para detalhes:
echo %LOG_FILE%
echo.

if "%UPDATE_MODE%"=="1" (
    powershell -NoProfile -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Ocorreu uma falha na atualizacao automatica do Disparador CP Fani.`n`nConsulte o log em:`n%LOG_FILE%', 'Erro na Atualizacao', 'OK', 'Error')" >nul 2>&1
)

pause
exit /b 1