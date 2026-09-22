@echo off
rem TOOLBOX - inicia o programa (duplo clique).
rem Uso: iniciar.bat          -> modo normal, sem console
rem      iniciar.bat --dev    -> modo desenvolvimento (console, logs e recarga do QML)
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "MODO=%~1"

rem --- 1. Localiza o Python 3.11+ ---
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if defined PY (
    %PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul || set "PY="
)
if not defined PY (
    echo.
    echo [TOOLBOX] Python 3.11 ou superior nao foi encontrado.
    echo Instale em https://www.python.org/downloads/ e marque "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

rem --- 2. Cria o ambiente virtual na primeira execucao ---
if not exist ".venv\Scripts\python.exe" (
    echo [TOOLBOX] Primeira execucao: criando ambiente virtual...
    %PY% -m venv .venv || goto :falha
)

rem --- 3. Instala/atualiza dependencias somente quando mudarem ---
".venv\Scripts\python.exe" scripts\preparar_ambiente.py %MODO% || goto :falha

rem --- 4. Abre o programa ---
if /i "%MODO%"=="--dev" (
    ".venv\Scripts\python.exe" -m toolbox --dev
    exit /b %errorlevel%
)
start "" ".venv\Scripts\pythonw.exe" -m toolbox
exit /b 0

:falha
echo.
echo [TOOLBOX] Nao foi possivel preparar o ambiente. Veja a mensagem acima.
pause
exit /b 1
