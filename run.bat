@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Virtual environment not found at .venv
  echo Create it first:
  echo   py -m venv .venv
  exit /b 1
)

call ".venv\Scripts\activate.bat"
python run.py %*
