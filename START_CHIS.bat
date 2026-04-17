@echo off
echo ============================================
echo   CHIS - Cognitive Hiring Intelligence System
echo ============================================
echo.

:: Check if virtual environment exists
IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
    echo Done.
)

:: Activate venv
echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install dependencies if needed
echo [3/3] Checking dependencies...
pip install -r requirements.txt --quiet

:: Run the app
echo.
echo Starting CHIS server...
echo Open your browser at: http://127.0.0.1:5000
echo Press CTRL+C to stop.
echo.
python run.py

pause
