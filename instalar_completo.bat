@echo off
chcp 65001 >nul
title Instalador Completo - Disparador de E-mails CP Fani
color 0A

:: ==============================================================================
:: AUTO-ELEVAÇÃO (UAC)
:: ==============================================================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permissoes de administrador...
    powershell -Command "Start-Process -FilePath '%~f0' -ArgumentList '%*' -Verb RunAs"
    exit /b
)

:: ==============================================================================
:: CONFIGURAÇÃO DE VARIÁVEIS
:: ==============================================================================
set "INSTALL_DIR=C:\Disparador de e-mails"
set "UPDATE_MODE=0"
if "%~1"=="/atualizar" set "UPDATE_MODE=1"

echo ============================================================
echo   INSTALADOR COMPLETO - DISPARADOR DE E-MAILS CP FANI
echo   Pasta de destino: %INSTALL_DIR%
echo ============================================================

:: ==============================================================================
:: 1. VERIFICAR/INSTALAR GIT
:: ==============================================================================
echo [1/6] Verificando Git...
where git >nul 2>&1
if %errorlevel% equ 0 (
    git --version
) else (
    echo Git nao encontrado. Tentando instalar via winget...
    winget install --id Git.Git -e --source winget --scope machine --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
    if %errorlevel% neq 0 (
        echo Falha ao instalar via winget. Por favor, instale o Git manualmente:
        echo https://git-scm.com/download/win
        pause
        exit /b 1
    )
    set "PATH=C:\Program Files\Git\cmd;%PATH%"
    git --version
)
:: Registrar pasta como segura para evitar "dubious ownership" entre contas
git config --system --add safe.directory "%INSTALL_DIR%" >nul 2>&1

:: ==============================================================================
:: 2. VERIFICAR/INSTALAR PYTHON
:: ==============================================================================
echo [2/6] Verificando Python 3.10+...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python nao encontrado. Tentando instalar via winget...
    winget install --id Python.Python.3.12 -e --scope machine --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
    if %errorlevel% neq 0 (
        echo Falha ao instalar via winget. Por favor, instale o Python 3.12 manualmente:
        echo https://www.python.org/downloads/
        echo MARQUE "Add Python to PATH" e "Install for all users".
        pause
        exit /b 1
    )
    set "PATH=C:\Python312;%PATH%"
)
python --version

:: ==============================================================================
:: 3. CLONAR OU ATUALIZAR PROJETO
:: ==============================================================================
echo [3/6] Preparando pasta do projeto...

:: Verificar se a pasta existe
if exist "%INSTALL_DIR%" (
    :: Verificar se é um repositório git válido
    cd /d "%INSTALL_DIR%"
    git rev-parse --git-dir >nul 2>&1
    if %errorlevel% equ 0 (
        :: É um repositório git válido - atualizar
        echo Atualizando repositorio existente...
        git fetch origin
        git reset --hard origin/main
    ) else (
        :: Pasta existe mas não é repositório git - fazer backup e recriar
        echo Pasta existe mas nao e repositorio git. Recriando...
        
        :: Backup do venv se existir
        if exist "%INSTALL_DIR%\venv" (
            echo Preservando ambiente virtual...
            if exist "%TEMP%\cpfani_venv_backup" rmdir /s /q "%TEMP%\cpfani_venv_backup" >nul 2>&1
            xcopy "%INSTALL_DIR%\venv" "%TEMP%\cpfani_venv_backup\" /E /I /H /Y >nul
        )
        
        :: Ajustar permissões da pasta existente para permitir remoção
        echo Ajustando permissoes da pasta existente...
        takeown /f "%INSTALL_DIR%" /r /d y >nul 2>&1
        icacls "%INSTALL_DIR%" /grant "%USERNAME%:(OI)(CI)F" /T /Q >nul 2>&1
        
        :: Remover pasta existente
        rmdir /s /q "%INSTALL_DIR%" 2>nul
        if exist "%INSTALL_DIR%" (
            echo ERRO: Falha ao remover pasta existente. Verifique se há arquivos em uso.
            pause
            exit /b 1
        )
        
        :: Criar pasta vazia
        mkdir "%INSTALL_DIR%"
        
        :: Clonar repositório
        echo Clonando repositorio...
        cd /d "%INSTALL_DIR%"
        git clone --depth 1 https://github.com/sunstrix/Disparador-de-emails-CP-FANI.git .
        
        :: Restaurar venv se existia
        if exist "%TEMP%\cpfani_venv_backup" (
            echo Restaurando ambiente virtual...
            xcopy "%TEMP%\cpfani_venv_backup" "%INSTALL_DIR%\venv\" /E /I /H /Y >nul
            rmdir /s /q "%TEMP%\cpfani_venv_backup"
        )
    )
) else (
    :: Pasta não existe - criar e clonar
    echo Criando pasta e clonando repositorio...
    mkdir "%INSTALL_DIR%"
    cd /d "%INSTALL_DIR%"
    git clone --depth 1 https://github.com/sunstrix/Disparador-de-emails-CP-FANI.git .
)

:: ==============================================================================
:: 4. AMBIENTE VIRTUAL E DEPENDÊNCIAS
:: ==============================================================================
echo [4/6] Configurando ambiente virtual...
cd /d "%INSTALL_DIR%"

:: Ajustar permissões da pasta para permitir escrita (necessário se veio de instalação anterior)
echo Ajustando permissoes para instalacao...
takeown /f "%INSTALL_DIR%" /r /d y >nul 2>&1
icacls "%INSTALL_DIR%" /grant "%USERNAME%:(OI)(CI)F" /T /Q >nul 2>&1

:: Criar venv se não existir
if not exist "venv" python -m venv venv

:: Ativar e instalar dependências
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo Falha ao instalar dependencias. Verifique sua conexao.
    pause
    exit /b 1
)

:: ==============================================================================
:: 5. TRAVAR PERMISSÕES DA PASTA (Segurança/LGPD)
:: ==============================================================================
echo [5/6] Travando permissoes da pasta de instalacao...
:: Remove heranca e concede: Administradores (F), SYSTEM (F), Usuarios (RX)
icacls "%INSTALL_DIR%" /inheritance:r /grant "*S-1-5-32-544:(OI)(CI)F" /grant "*S-1-5-18:(OI)(CI)F" /grant "*S-1-5-32-545:(OI)(CI)RX" /T /Q

:: ==============================================================================
:: 6. CRIAR ATALHO NA ÁREA DE TRABALHO PÚBLICA
:: ==============================================================================
echo [6/6] Criando atalho na area de trabalho...
set "DESKTOP_PUBLIC=C:\Users\Public\Desktop"
if not exist "%DESKTOP_PUBLIC%" set "DESKTOP_PUBLIC=%PUBLIC%\Desktop"

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP_PUBLIC%\Disparador de E-mails CP Fani.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\executar.bat'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\ico\icone.ico,0'; $Shortcut.WindowStyle = 7; $Shortcut.Save()"

echo.
echo ============================================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo O atalho foi criado na area de trabalho publica.
echo Os dados do usuario serao salvos em: %%LOCALAPPDATA%%\CPFani
echo.

if "%UPDATE_MODE%"=="1" (
    echo Reiniciando o aplicativo...
    start "" "%INSTALL_DIR%\executar.bat"
) else (
    pause
)