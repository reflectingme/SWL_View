@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Virtual environment not found at .venv
  echo Create it first:
  echo   python -m venv .venv
  echo If "python" is not recognized, install Python 3 from python.org
  echo and ensure "Add python.exe to PATH" is enabled.
  exit /b 1
)

call ".venv\Scripts\activate.bat"
python run.py %*
