@echo off
echo ==========================================
echo   DTU Grocery Price Compare - Setup
echo ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.10+.
    pause
    exit /b 1
)

:: Create virtual environment if not exists
if not exist "venv" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install dependencies
echo [3/3] Installing dependencies...
pip install -r requirements.txt -q

echo.
echo ==========================================
echo   Starting Server...
echo   Open http://localhost:8000
echo ==========================================
echo.

python main.py
