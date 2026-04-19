@echo off
echo.
echo  ========================================
echo    Sentry Stream Processor - Setup
echo  ========================================
echo.

:: -------------------------------------------
:: 1. Check Python
:: -------------------------------------------
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found!
    echo  Install Python 3.10+ from https://python.org
    echo  and make sure "Add to PATH" is checked.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [OK] Python %PYVER% found.

:: -------------------------------------------
:: 2. Check Visual C++ Redistributable
:: -------------------------------------------
echo  Checking for Visual C++ Redistributable...
set VCREDIST_OK=0
if exist "%SystemRoot%\System32\vcruntime140.dll" set VCREDIST_OK=1
if exist "%SystemRoot%\System32\vcruntime140_1.dll" set VCREDIST_OK=1

if %VCREDIST_OK% equ 0 (
    echo.
    echo  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    echo  !!  WARNING: VC++ Redistributable MISSING !!
    echo  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    echo.
    echo  PyTorch will NOT work without it.
    echo  Download and install from:
    echo.
    echo    https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo.
    echo  Then reboot and run this setup again.
    echo.
    echo  Setup will continue, but the app WILL crash
    echo  at runtime until this is installed.
    echo.
    pause
) else (
    echo  [OK] Visual C++ Redistributable found.
)

:: -------------------------------------------
:: 3. Create virtual environment
:: -------------------------------------------
if not exist venv\ (
    echo.
    echo  Creating virtual environment...
    python -m venv venv
) else (
    echo  [OK] Virtual environment exists.
)

:: Activate
call venv\Scripts\activate.bat

:: Upgrade pip
echo  Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

:: -------------------------------------------
:: 4. Install PyTorch (GPU-first strategy)
:: -------------------------------------------
echo.
echo  ----------------------------------------
echo    Detecting hardware...
echo  ----------------------------------------

:: Check for NVIDIA GPU
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo  [GPU] NVIDIA GPU detected!
    echo.
    for /f "tokens=*" %%g in ('nvidia-smi --query-gpu=name --format=csv,noheader,nounits 2^>nul') do (
        echo         %%g
    )
    echo.
    echo  Installing PyTorch with CUDA 12.4...
    echo  (This may take a few minutes)
    echo.
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    if %errorlevel% neq 0 (
        echo.
        echo  [WARN] CUDA install failed, falling back to CPU...
        pip install torch torchvision torchaudio
    )
) else (
    echo.
    echo  [CPU] No NVIDIA GPU detected.
    echo  Installing CPU-only PyTorch...
    echo.
    pip install torch torchvision torchaudio
)

:: -------------------------------------------
:: 5. Install remaining dependencies
:: -------------------------------------------
echo.
echo  Installing remaining dependencies...
pip install -r requirements.txt

:: -------------------------------------------
:: 6. Verify torch loads
:: -------------------------------------------
echo.
echo  ----------------------------------------
echo    Verifying installation...
echo  ----------------------------------------
python -c "import torch; print(f'  [OK] PyTorch {torch.__version__}'); print(f'  [OK] CUDA available: {torch.cuda.is_available()}'); dev = 'cuda: ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'; print(f'  [OK] Device: {dev}')" 2>nul
if %errorlevel% neq 0 (
    echo  [ERROR] PyTorch failed to load!
    echo  If you see a DLL error, install the VC++ Redistributable:
    echo  https://aka.ms/vs/17/release/vc_redist.x64.exe
)

echo.
echo  ========================================
echo    Setup complete! Run with: run.bat
echo  ========================================
echo.
pause
