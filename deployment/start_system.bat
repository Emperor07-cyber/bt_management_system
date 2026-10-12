@echo off
setlocal EnableExtensions

title BT Management System - Start

set "DEPLOYMENT_DIR=%~dp0"
set "PROJECT_ROOT=%DEPLOYMENT_DIR%.."
set "BACKEND_DIR=%PROJECT_ROOT%\backend"
set "LOG_DIR=%DEPLOYMENT_DIR%logs"

set "PYTHON_EXE=%BACKEND_DIR%\venv\Scripts\python.exe"
set "WAITRESS_EXE=%BACKEND_DIR%\venv\Scripts\waitress-serve.exe"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo.
echo ==========================================
echo   BT MANAGEMENT SYSTEM - START SYSTEM
echo ==========================================
echo.

if not exist "%PYTHON_EXE%" (
    echo ERROR: Python virtual environment was not found:
    echo %PYTHON_EXE%
    pause
    exit /b 1
)

if not exist "%WAITRESS_EXE%" (
    echo ERROR: Waitress was not found:
    echo %WAITRESS_EXE%
    echo.
    echo Install Waitress in the backend virtual environment.
    pause
    exit /b 1
)

if not exist "%PROJECT_ROOT%\frontend\dist\index.html" (
    echo ERROR: Frontend build was not found:
    echo %PROJECT_ROOT%\frontend\dist\index.html
    pause
    exit /b 1
)

echo.
echo [1/2] Checking Django configuration...

pushd "%BACKEND_DIR%"

"%PYTHON_EXE%" manage.py check
if errorlevel 1 (
    echo ERROR: Django configuration check failed.
    popd
    pause
    exit /b 1
)

popd

echo Django configuration is valid.

echo.
echo [2/2] Starting backend and frontend...
powershell -NoProfile -ExecutionPolicy Bypass -File "%DEPLOYMENT_DIR%manage_services.ps1" -Action Start -ProjectRoot "%PROJECT_ROOT%"
if errorlevel 1 (
    echo ERROR: One or more services failed to start. Any service started by this attempt was stopped.
    echo Check %LOG_DIR%\backend.log, %LOG_DIR%\backend.error.log, %LOG_DIR%\frontend.log, and %LOG_DIR%\frontend.error.log.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   BT MANAGEMENT SYSTEM IS RUNNING
echo ==========================================
echo.
echo Application:
echo http://127.0.0.1:8080
echo.
echo Backend:
echo http://127.0.0.1:8000
echo.

choice /C YN /M "Open the application in your browser"
if errorlevel 2 goto END

start "" "http://127.0.0.1:8080"

:END
echo.
echo Use stop_system.bat to stop the system.
echo.

pause
endlocal