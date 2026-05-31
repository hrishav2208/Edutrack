@echo off
title Edutrack - Educational Management System
echo ===================================================
echo               EDUTRACK AUTO-LAUNCHER               
echo ===================================================
echo.

:: Check if virtual environment exists, if not, create it
if not exist "venv\" (
    echo [1/3] Creating Python Virtual Environment (venv)...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Python is not installed or not in your system PATH.
        echo Please download and install Python from: https://www.python.org/
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b
    )
)

:: Activate the virtual environment
call venv\Scripts\activate

:: Install/update dependencies
echo [2/3] Verifying python library dependencies...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

:: Open the browser automatically
echo [3/3] Launching Edutrack web application...
echo.
echo Opening http://127.0.0.1:5000 in your default browser...
start "" http://127.0.0.1:5000

:: Run the Flask server
python wsgi.py

pause
