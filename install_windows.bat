@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul || (echo Python launcher required & pause & exit /b 1)
where git >nul 2>nul || (echo Git for Windows required & pause & exit /b 1)
py -3.10 -m venv .venv || goto fail
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel || goto fail
.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu || goto fail
.venv\Scripts\python.exe -m pip install git+https://github.com/myshell-ai/MeloTTS.git || goto fail
.venv\Scripts\python.exe -m unidic download || goto fail
.venv\Scripts\python.exe -m unittest discover -s tests -v || goto fail
echo Installation done; use start_windows.bat
pause
exit /b 0
:fail
echo Installation failed; read log above
pause
exit /b 1
