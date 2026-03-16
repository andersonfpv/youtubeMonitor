@echo off
cd /d "%~dp0"
python "monitor_youtube_live_multi.py" --csv "C:\logs\dados_live.csv" --url "https://www.youtube.com/watch?v=juUt-rN5CVo" --url "https://www.youtube.com/watch?v=4CAmwaFJo6k" >> "C:\logs\yt-monitor.log" 2>&1
