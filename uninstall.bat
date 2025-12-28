@echo off
REM ============================================================================
REM UNINSTALL.BAT - System Monitor
REM Script de desinstalação para Windows
REM ============================================================================

echo ============================================
echo   System Monitor - Desinstalacao
echo ============================================
echo.
echo [!] ATENCAO: Este script ira remover:
echo    - Ambiente virtual (.venv\)
echo    - Arquivos cache Python (__pycache__, *.pyc)
echo    - Arquivos temporarios do PyInstaller (build\, dist\, *.spec)
echo.
echo    Os relatorios gerados (reports\) NAO serao removidos.
echo.

REM Pergunta confirmação
set /p confirm="Deseja continuar? (S/N): "
if /i not "%confirm%"=="S" (
    echo.
    echo [X] Desinstalacao cancelada.
    pause
    exit /b 0
)

echo.
echo [*] Iniciando desinstalacao...
echo.

REM Remove ambiente virtual
if exist ".venv" (
    echo [*] Removendo ambiente virtual...
    rmdir /s /q .venv
    echo [OK] Ambiente virtual removido
) else (
    echo [!] Ambiente virtual nao encontrado
)

REM Remove cache Python
echo [*] Removendo cache Python...
for /d /r %%i in (__pycache__) do @if exist "%%i" rmdir /s /q "%%i"
del /s /q *.pyc >nul 2>&1
del /s /q *.pyo >nul 2>&1
for /d /r %%i in (*.egg-info) do @if exist "%%i" rmdir /s /q "%%i"
echo [OK] Cache Python removido

REM Remove arquivos do PyInstaller
if exist "build" (
    echo [*] Removendo arquivos do PyInstaller...
    rmdir /s /q build >nul 2>&1
)
if exist "dist" (
    rmdir /s /q dist >nul 2>&1
)
del /q *.spec >nul 2>&1
if exist "build" (
    echo [OK] Arquivos do PyInstaller removidos
)

REM Remove arquivos de teste
if exist "teste.py" (
    echo [*] Removendo arquivos de teste...
    del /q teste.py teste_utf8.pdf gerar_pdf_teste.py >nul 2>&1
    echo [OK] Arquivos de teste removidos
)

echo.
echo ============================================
echo   [OK] DESINSTALACAO CONCLUIDA!
echo ============================================
echo.
echo [i] Os seguintes itens foram PRESERVADOS:
echo    - Codigo fonte (.py)
echo    - Relatorios gerados (reports\)
echo    - Scripts de instalacao (install.bat, requirements.txt)
echo.
echo Para reinstalar, execute:
echo    install.bat
echo.
echo Para remover TUDO (incluindo codigo fonte):
echo    cd ..
echo    rmdir /s /q system_monitor
echo.
echo ============================================
echo.
pause