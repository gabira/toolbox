@echo off
rem Cria o atalho "TOOLBOX" na Area de Trabalho, com o icone do programa.
rem Rode uma vez. O atalho abre o iniciar.bat minimizado (sem janela preta na frente).
setlocal
cd /d "%~dp0"
set "DESTINO=%~1"
if "%DESTINO%"=="" set "DESTINO=DESKTOP"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$pasta = if ('%DESTINO%' -eq 'DESKTOP') { [Environment]::GetFolderPath('Desktop') } else { '%DESTINO%' };" ^
  "$atalho = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $pasta 'TOOLBOX.lnk'));" ^
  "$atalho.TargetPath = '%~dp0iniciar.bat';" ^
  "$atalho.WorkingDirectory = '%~dp0';" ^
  "$atalho.IconLocation = '%~dp0toolbox\ui\imagens\toolbox.ico';" ^
  "$atalho.WindowStyle = 7;" ^
  "$atalho.Description = 'TOOLBOX';" ^
  "$atalho.Save()"
if errorlevel 1 (
    echo [TOOLBOX] Nao foi possivel criar o atalho.
) else (
    echo [TOOLBOX] Atalho "TOOLBOX" criado.
)
if "%~1"=="" pause
