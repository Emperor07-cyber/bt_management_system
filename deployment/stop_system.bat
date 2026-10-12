@echo off
setlocal EnableExtensions

title BT Management System - Stop

set "DEPLOYMENT_DIR=%~dp0"
set "PROJECT_ROOT=%DEPLOYMENT_DIR%.."
set "LOG_DIR=%DEPLOYMENT_DIR%logs"

echo.
echo ==========================================
echo   BT MANAGEMENT SYSTEM - STOP SYSTEM
echo ==========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%DEPLOYMENT_DIR%manage_services.ps1" -Action Stop -ProjectRoot "%PROJECT_ROOT%"
if errorlevel 1 (
    echo.
    echo [ERROR] One or more services could not be safely stopped.
    echo Review the messages above and the PID files in %LOG_DIR%.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   BT MANAGEMENT SYSTEM STOPPED
echo ==========================================
echo.
echo Logs are preserved in:
echo %LOG_DIR%
echo.

pause
endlocal
exit /b 0