@echo off
setlocal EnableExtensions

title BT Management System - Health Check

set "DEPLOYMENT_DIR=%~dp0"
set "PROJECT_ROOT=%DEPLOYMENT_DIR%.."
set "BACKEND_DIR=%PROJECT_ROOT%\backend"

set "BACKEND_HOST=127.0.0.1"
set "BACKEND_PORT=8000"
set "FRONTEND_HOST=127.0.0.1"
set "FRONTEND_PORT=8080"
set "CHECK_FAILED=0"

echo.
echo ==========================================
echo   BT MANAGEMENT SYSTEM - HEALTH CHECK
echo ==========================================
echo.

echo [1/5] Checking backend port...

netstat -ano | findstr ":%BACKEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [FAIL] Backend is not running.
    set "CHECK_FAILED=1"
) else (
    echo [PASS] Backend is listening on port %BACKEND_PORT%.
)

echo.
echo [2/5] Checking frontend port...

netstat -ano | findstr ":%FRONTEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [FAIL] Frontend is not running.
    set "CHECK_FAILED=1"
) else (
    echo [PASS] Frontend is listening on port %FRONTEND_PORT%.
)

echo.
echo [3/5] Checking backend URL...

powershell -NoProfile -Command ^
"try { ^
    $response = Invoke-WebRequest -Uri 'http://%BACKEND_HOST%:%BACKEND_PORT%/' -UseBasicParsing -TimeoutSec 5; ^
    Write-Host '[PASS] Backend URL responded with HTTP' $response.StatusCode; ^
    exit 0 ^
} catch { ^
    if ($_.Exception.Response) { ^
        Write-Host '[PASS] Backend URL responded with HTTP' [int]$_.Exception.Response.StatusCode; ^
        exit 0 ^
    }; ^
    Write-Host '[FAIL] Backend URL could not be reached.'; ^
    exit 1 ^
}"
if errorlevel 1 set "CHECK_FAILED=1"

echo.
echo [4/5] Checking frontend URL...

powershell -NoProfile -Command ^
"try { ^
    $response = Invoke-WebRequest -Uri 'http://%FRONTEND_HOST%:%FRONTEND_PORT%/' -UseBasicParsing -TimeoutSec 5; ^
    if ($response.StatusCode -eq 200) { ^
        Write-Host '[PASS] Frontend returned HTTP 200.'; ^
        exit 0 ^
    } else { ^
        Write-Host '[FAIL] Frontend returned HTTP' $response.StatusCode; ^
        exit 1 ^
    } ^
} catch { ^
    Write-Host '[FAIL] Frontend URL could not be reached.'; ^
    exit 1 ^
}"
if errorlevel 1 set "CHECK_FAILED=1"

echo.
echo [5/5] Checking Django configuration...

if not exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    echo [FAIL] Backend virtual environment was not found.
    set "CHECK_FAILED=1"
    goto :FINISH
)

pushd "%BACKEND_DIR%"

call venv\Scripts\activate.bat

python manage.py check
if errorlevel 1 (
    echo [FAIL] Django configuration check failed.
    set "CHECK_FAILED=1"
) else (
    echo [PASS] Django configuration is valid.
)

popd

:FINISH
echo.
echo ==========================================
echo   HEALTH CHECK COMPLETE
echo ==========================================
echo.

pause
if "%CHECK_FAILED%"=="1" (
    endlocal
    exit /b 1
)
endlocal
exit /b 0