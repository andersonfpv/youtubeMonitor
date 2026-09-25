@echo off
setlocal
cd /d "%~dp0"
if not defined MONITOR_PYTHON set "MONITOR_PYTHON=%~dp0venv\Scripts\python.exe"
if not exist "%MONITOR_PYTHON%" (
  echo Python nao encontrado. Configure MONITOR_PYTHON ou crie o venv.
  pause
  exit /b 1
)
"%MONITOR_PYTHON%" -B "%~dp0dashboard.py" --logs "C:\logs"
if errorlevel 1 pause
