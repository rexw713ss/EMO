@echo off
chcp 65001 >nul 2>&1
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Python virtual environment not found. Run: python -m venv .venv
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0check_env.py"
pause
