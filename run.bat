@echo off
title Edutrack - Educational Management System
echo ===================================================
echo               EDUTRACK AUTO-LAUNCHER               
echo ===================================================
echo.

REM --- Step 1: Virtual Environment ---
if exist venv\Scripts\activate.bat goto ACTIVATE
echo [1/3] Creating Python Virtual Environment (venv)...
python -m venv venv
if not exist venv\Scripts\activate.bat (
    echo [ERROR] Failed to create virtual environment. 
    echo Please make sure Python is installed and in your system PATH.
    pause
    exit /b
)

:ACTIVATE
echo [1/3] Activating virtual environment...
call venv\Scripts\activate

REM --- Step 2: Install dependencies ---
echo [2/3] Verifying library dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM --- Step 3: Launch browser and server ---
echo [3/3] Launching Edutrack web application...
echo Opening http://127.0.0.1:5000 in your browser...
start "" http://127.0.0.1:5000

python wsgi.py

echo.
echo Server has stopped.
pause
