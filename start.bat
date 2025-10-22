@echo off
REM ============================================================================
REM Elevator Controller Startup Script for Windows
REM
REM This script automates the setup and launch process on Windows:
REM 1. Checks Python version
REM 2. Ensures pip is available
REM 3. Installs uv via pip
REM 4. Installs project dependencies
REM 5. Starts simulator server in background
REM 6. Runs elevator controller
REM
REM Usage:
REM   start.bat
REM
REM Requirements:
REM   - Python 3.12 or higher
REM   - Internet connection (for first-time setup)
REM ============================================================================

setlocal enabledelayedexpansion

REM Colors (using ANSI escape codes - works in Windows 10+)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "CYAN=[96m"
set "NC=[0m"

echo %CYAN%============================================================%NC%
echo %CYAN%Elevator Controller Startup (Windows)%NC%
echo %CYAN%============================================================%NC%
echo.

REM ============================================================================
REM Step 1: Check Python
REM ============================================================================
echo %BLUE%[1/6]%NC% Checking Python version...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    python3 --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo %RED%Error: Python 3 is not installed%NC%
        echo Please install Python 3.12+ from https://www.python.org/
        echo Make sure to check "Add Python to PATH" during installation
        pause
        exit /b 1
    )
    set PYTHON_CMD=python3
) else (
    set PYTHON_CMD=python
)

for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %GREEN%✓%NC% Python %PYTHON_VERSION% found
echo.

REM ============================================================================
REM Step 2: Check pip
REM ============================================================================
echo %BLUE%[2/6]%NC% Checking pip...

%PYTHON_CMD% -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%Warning: pip not found, installing...%NC%
    %PYTHON_CMD% -m ensurepip --user
    if !errorlevel! neq 0 (
        echo %RED%Error: Failed to install pip%NC%
        echo Please install pip manually
        pause
        exit /b 1
    )
)

echo %GREEN%✓%NC% pip is available
echo %BLUE%▶%NC% Upgrading pip...
%PYTHON_CMD% -m pip install --user --upgrade pip --quiet
echo %GREEN%✓%NC% pip is ready
echo.

REM ============================================================================
REM Step 3: Check/Install uv
REM ============================================================================
echo %BLUE%[3/6]%NC% Checking uv installation...

where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%Warning: uv not found%NC%
    echo %BLUE%▶%NC% Installing uv via pip...

    %PYTHON_CMD% -m pip install --user uv
    if !errorlevel! neq 0 (
        echo %RED%Error: Failed to install uv%NC%
        pause
        exit /b 1
    )

    echo %GREEN%✓%NC% uv installed via pip

    REM Add Python Scripts to PATH for current session
    for /f "delims=" %%i in ('%PYTHON_CMD% -c "import os, sys; print(os.path.join(os.path.dirname(sys.executable), 'Scripts'))"') do set PYTHON_SCRIPTS=%%i
    set "PATH=%PYTHON_SCRIPTS%;%PATH%"

    echo %BLUE%▶%NC% Added %PYTHON_SCRIPTS% to PATH

    REM Verify uv is now available
    where uv >nul 2>&1
    if !errorlevel! neq 0 (
        echo %RED%Error: uv installed but not found in PATH%NC%
        echo.
        echo Please add Python Scripts directory to your PATH:
        echo   %PYTHON_SCRIPTS%
        echo.
        echo Then restart Command Prompt and run this script again.
        pause
        exit /b 1
    )

    echo %GREEN%✓%NC% uv is now available
) else (
    for /f "tokens=2" %%i in ('uv --version 2^>^&1') do set UV_VERSION=%%i
    echo %GREEN%✓%NC% uv !UV_VERSION! found
)
echo.

REM ============================================================================
REM Step 4: Install dependencies
REM ============================================================================
echo %BLUE%[4/6]%NC% Installing project dependencies...

REM Create logs directory
if not exist logs mkdir logs

REM Sync dependencies
uv sync
if %errorlevel% neq 0 (
    echo %RED%Error: Failed to install dependencies%NC%
    pause
    exit /b 1
)

echo %GREEN%✓%NC% Dependencies installed successfully
echo.

REM ============================================================================
REM Step 5: Start simulator
REM ============================================================================
echo %BLUE%[5/6]%NC% Starting simulator server...

set SIMULATOR_PORT=8000
set SIMULATOR_LOG=logs\simulator_%SIMULATOR_PORT%.log

REM Check if simulator is already running
netstat -an | findstr ":%SIMULATOR_PORT%.*LISTEN" >nul 2>&1
if %errorlevel% equ 0 (
    echo %YELLOW%Warning: Simulator already running on port %SIMULATOR_PORT%%NC%
    echo %BLUE%▶%NC% Using existing simulator instance
) else (
    REM Start simulator in background
    echo %BLUE%▶%NC% Launching simulator on port %SIMULATOR_PORT%...
    start /B "" uv run python -m elevator_saga.server.simulator --host 127.0.0.1 --port %SIMULATOR_PORT% --debug > %SIMULATOR_LOG% 2>&1

    REM Wait for simulator to start (max 30 seconds)
    echo %BLUE%▶%NC% Waiting for simulator to be ready...
    set /a COUNT=0
    :wait_loop
    timeout /t 1 /nobreak >nul
    curl -s http://127.0.0.1:%SIMULATOR_PORT%/api/state >nul 2>&1
    if !errorlevel! equ 0 (
        echo %GREEN%✓%NC% Simulator is ready on http://127.0.0.1:%SIMULATOR_PORT%
        echo %GREEN%✓%NC% Simulator logs: %SIMULATOR_LOG%
        goto simulator_ready
    )
    set /a COUNT+=1
    if !COUNT! lss 30 goto wait_loop

    echo %RED%Error: Simulator failed to start within 30 seconds%NC%
    echo Check logs at: %SIMULATOR_LOG%
    pause
    exit /b 1
)

:simulator_ready
echo.

REM ============================================================================
REM Step 6: Run controller
REM ============================================================================
echo %CYAN%============================================================%NC%
echo %CYAN%Starting Elevator Controller%NC%
echo %CYAN%============================================================%NC%
echo.
echo %BLUE%▶%NC% Press Ctrl+C to stop
echo.

REM Run the controller
uv run python elevator_controller.py %*

REM Note: On Windows, background processes may continue after Ctrl+C
REM You may need to manually close the simulator process from Task Manager
echo.
echo %YELLOW%Note: If simulator is still running, you can stop it from Task Manager%NC%
echo %YELLOW%or by running: taskkill /F /IM python.exe%NC%

endlocal
