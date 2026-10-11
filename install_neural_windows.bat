@echo off
setlocal
cd /d "%~dp0"
py -3.11 -m venv .venv_neural || goto fail
.venv_neural\Scripts\python.exe -m pip install -U pip || goto fail
.venv_neural\Scripts\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu || goto fail
.venv_neural\Scripts\python.exe -m pip install chatterbox-tts || goto fail
echo Neural dependencies installed.
pause
exit /b 0
:fail
echo Installation failed. Check Python 3.11 and package compatibility.
pause
exit /b 1
