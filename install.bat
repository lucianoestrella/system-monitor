@echo off
REM ============================================================================
REM INSTALL.BAT - System Monitor
REM Script de instalação automática para Windows
REM ============================================================================

echo ============================================
echo   System Monitor - Instalacao Automatica
echo ============================================
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo X Python nao encontrado!
    echo   Baixe e instale o Python em: https://www.python.org/downloads/
    echo   Certifique-se de marcar "Add Python to PATH" durante a instalacao
    pause
    exit /b 1
)

echo [OK] Python encontrado:
python --version
echo.

REM Cria ambiente virtual
echo [*] Criando ambiente virtual...
if exist ".venv" (
    echo [!] Ambiente virtual ja existe. Removendo...
    rmdir /s /q .venv
)

python -m venv .venv

if %errorlevel% neq 0 (
    echo [X] Erro ao criar ambiente virtual!
    pause
    exit /b 1
)

echo [OK] Ambiente virtual criado
echo.

REM Ativa ambiente virtual
echo [*] Ativando ambiente virtual...
call .venv\Scripts\activate.bat

if %errorlevel% neq 0 (
    echo [X] Erro ao ativar ambiente virtual!
    pause
    exit /b 1
)

echo [OK] Ambiente virtual ativado
echo.

REM Atualiza pip
echo [*] Atualizando pip...
python -m pip install --upgrade pip --quiet

REM Instala dependências
echo [*] Instalando dependencias...
if exist "requirements.txt" (
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [X] Erro ao instalar dependencias!
        pause
        exit /b 1
    )
) else (
    echo [!] requirements.txt nao encontrado. Instalando dependencias basicas...
    pip install psutil rich customtkinter
)

echo.
echo ============================================
echo   [OK] INSTALACAO CONCLUIDA COM SUCESSO!
echo ============================================
echo.
echo Para usar o System Monitor:
echo.
echo 1. Ative o ambiente virtual:
echo    .venv\Scripts\activate
echo.
echo 2. Execute o programa:
echo    python main.py          # Modo padrao (GUI)
echo    python main.py --cli    # Modo CLI
echo    python gui.py           # Apenas GUI
echo    python cli.py           # Apenas CLI
echo.
echo 3. Para desativar o ambiente virtual:
echo    deactivate
echo.
echo ============================================
echo.
pause