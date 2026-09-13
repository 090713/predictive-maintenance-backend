@echo off
REM Fathom Backend Startup (Windows)

echo === Fathom Backend Startup ===

REM Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: python not found in PATH
    exit /b 1
)

REM Create venv if not exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate
call .venv\Scripts\activate.bat

REM Install deps
echo Installing dependencies...
pip install -q -r requirements.txt

REM Check .env
if not exist ".env" (
    echo Warning: .env not found, copying from .env.example
    copy .env.example .env
    echo Please edit .env with your MongoDB URI and JWT secret
    exit /b 1
)

REM Run
echo Starting server on http://localhost:8000
echo API docs: http://localhost:8000/docs
uvicorn backend.main:app --reload --port 8000