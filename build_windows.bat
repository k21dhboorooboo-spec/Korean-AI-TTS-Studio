@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Install dependencies first with install_windows.bat
 pause
 exit /b 1
)
.venv\Scripts\python.exe -m pip install pyinstaller==6.16.0 || goto fail
.venv\Scripts\python.exe -m unittest discover -s tests -v || goto fail
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name KoreanAITTSStudio --collect-all melo --collect-all unidic --collect-all torch app.py || goto fail
where ISCC.exe >nul 2>nul
if errorlevel 1 (
 echo PyInstaller built dist\KoreanAITTSStudio but Inno Setup ISCC.exe is not in PATH.
 echo Install Inno Setup 6 and compile installer\KoreanAITTSStudio.iss
 pause
 exit /b 2
)
ISCC.exe installer\KoreanAITTSStudio.iss || goto fail
echo Installer created in dist_installer
pause
exit /b 0
:fail
echo Build or tests failed; see errors above.
pause
exit /b 1
