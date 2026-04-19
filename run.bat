@echo off
if not exist venv\ (
    echo  Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

:: Quick VC++ check before we waste time activating
if not exist "%SystemRoot%\System32\vcruntime140.dll" (
    echo.
    echo  [ERROR] Visual C++ Redistributable is not installed!
    echo  PyTorch cannot start without it.
    echo.
    echo  Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo  Install, reboot, and try again.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Starting Sentry Stream Processor...
python main.py
pause
