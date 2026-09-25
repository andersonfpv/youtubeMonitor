@echo off
setlocal
cd /d "%~dp0"
if not defined MONITOR_PYTHON set "MONITOR_PYTHON=%~dp0venv\Scripts\python.exe"
if not exist "%MONITOR_PYTHON%" (
  echo Python nao encontrado. Crie o venv ou defina MONITOR_PYTHON.
  pause
  exit /b 1
)
"%MONITOR_PYTHON%" -B "%~dp0agenda_relatorios.py" --env "%~dp0.env" --csv "C:\logs\dados_live.csv"
if errorlevel 1 pause
