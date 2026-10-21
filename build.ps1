# Lokaler Build (Windows 11, Python 3.11 + Inno Setup 6 installiert) -> installer\YAVIS-Setup.exe
$ErrorActionPreference = "Stop"
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m unittest discover tests
.\.venv\Scripts\pyinstaller --noconfirm --windowed --name YAVIS `
  --collect-all faster_whisper --collect-all ctranslate2 --collect-all av --collect-all ddgs --collect-all customtkinter --hidden-import edge_tts `
  --hidden-import pyttsx3.drivers --hidden-import pyttsx3.drivers.sapi5 --hidden-import comtypes `
  run_yavis.py
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" installer.iss
Write-Host "Fertig: installer\YAVIS-Setup.exe"
