@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo AI Personalized Diet Recommendation System
echo ================================================

where py >nul 2>nul
if %errorlevel%==0 (
    set PYTHON_CMD=py
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python was not found. Install Python 3.10 or newer from https://www.python.org/downloads/
        echo During installation, enable Add Python to PATH.
        pause
        exit /b 1
    )
    set PYTHON_CMD=python
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto error
)

echo Installing or checking required packages...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto error
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error

echo Starting Streamlit...
call ".venv\Scripts\python.exe" -m streamlit run python/app.py
if errorlevel 1 goto error
goto end

:error
echo.
echo Something went wrong. Check the error above and the README instructions.
pause
exit /b 1

:end
endlocal
