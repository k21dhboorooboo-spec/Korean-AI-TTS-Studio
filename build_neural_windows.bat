@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv_neural\Scripts\python.exe" (echo Run install_neural_windows.bat first & exit /b 1)
.venv_neural\Scripts\python.exe -m pip install pyinstaller || exit /b 1
.venv_neural\Scripts\python.exe -m unittest discover -s tests -v || exit /b 1
.venv_neural\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name KoreanAITTSStudioNeural --collect-all chatterbox --collect-all torch --collect-all torchaudio neural_app.py || exit /b 1
where ISCC.exe >nul 2>nul
if errorlevel 1 (echo Inno Setup 6 ISCC.exe required for installer & exit /b 2)
ISCC.exe installer\KoreanAITTSStudioNeural.iss || exit /b 1
