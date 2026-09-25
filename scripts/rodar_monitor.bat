@echo off
setlocal
cd /d "%~dp0"
if not defined MONITOR_PYTHON set "MONITOR_PYTHON=%~dp0venv\Scripts\python.exe"
if not exist "%MONITOR_PYTHON%" (
  echo Python nao encontrado. Crie o venv ou defina MONITOR_PYTHON.
  exit /b 1
)
if not exist "C:\logs" mkdir "C:\logs"
"%MONITOR_PYTHON%" -u "%~dp0monitor_youtube_live_multi.py" --env "%~dp0.env" --csv "C:\logs\dados_live.csv" --url "https://www.youtube.com/watch?v=juUt-rN5CVo" --url "https://www.youtube.com/watch?v=4CAmwaFJo6k" >> "C:\logs\yt-monitor.log" 2>&1
exit /b %errorlevel%
