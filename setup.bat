@echo off
echo Setting up Sentry Stream Processor...

:: Check if python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python could not be found. Please install Python 3.9 or higher and add it to your PATH.
    pause
    exit /b
)

:: Create virtual environment if it doesn't exist
if not exist venv\ (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Install requirements
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Setup complete! You can now start the application with run.bat
pause
