# Build on Windows x64 using Python 3.13 and Inno Setup 6.
# Install build tools into a development virtual environment, not on the target PC.
$ErrorActionPreference = 'Stop'
python -m PyInstaller --noconfirm --onedir --windowed --name MonitorYouTube --add-data 'scripts\dashboard.html;.' --add-data 'scripts\agenda.html;.' --collect-all selenium --collect-all tzdata scripts\app.py
if ($LASTEXITCODE -ne 0) { throw 'Falha no empacotamento.' }
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' packaging\installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar instalador.' }
