@echo off
setlocal EnableExtensions EnableDelayedExpansion

title BT Management System - Offline Production Setup

REM ============================================================
REM BT MANAGEMENT SYSTEM
REM OFFLINE WINDOWS PRODUCTION INSTALLER
REM ============================================================

set "DEPLOYMENT_DIR=%~dp0"
for %%I in ("%DEPLOYMENT_DIR%..") do set "PROJECT_ROOT=%%~fI"

set "BACKEND_DIR=%PROJECT_ROOT%\backend"
set "FRONTEND_DIR=%PROJECT_ROOT%\frontend"
set "PACKAGES_DIR=%DEPLOYMENT_DIR%packages"
set "PYTHON_PACKAGES=%PACKAGES_DIR%\python"
set "NPM_CACHE=%PACKAGES_DIR%\npm"
set "INSTALLERS_DIR=%DEPLOYMENT_DIR%installers"
set "LOG_DIR=%DEPLOYMENT_DIR%logs"

set "VENV_DIR=%BACKEND_DIR%\venv"
set "ENV_FILE=%PROJECT_ROOT%\.env"

set "DB_NAME=bt_management_system"
set "DB_USER=bt_app"
set "DB_PORT=5432"
set "DB_HOST=127.0.0.1"

set "BACKEND_PORT=8000"
set "FRONTEND_PORT=8080"

set "POSTGRES_SERVICE="

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "LOG_FILE=%LOG_DIR%\setup.log"

echo.
echo ============================================================
echo       BT MANAGEMENT SYSTEM - PRODUCTION SETUP
echo ============================================================
echo.
echo Project root: %PROJECT_ROOT%
echo Database:     %DB_NAME%
echo DB user:      %DB_USER%
echo DB port:      %DB_PORT%
echo Backend port: %BACKEND_PORT%
echo Frontend port:%FRONTEND_PORT%
echo.

call :require_admin
if errorlevel 1 exit /b 1

call :validate_project
if errorlevel 1 exit /b 1

call :check_python
if errorlevel 1 exit /b 1

call :check_node
if errorlevel 1 exit /b 1

call :check_postgresql
if errorlevel 1 exit /b 1

call :create_python_environment
if errorlevel 1 exit /b 1

call :install_python_dependencies
if errorlevel 1 exit /b 1

call :configure_environment
if errorlevel 1 exit /b 1

call :create_database
if errorlevel 1 exit /b 1

call :run_django_setup
if errorlevel 1 exit /b 1

call :install_frontend_dependencies
if errorlevel 1 exit /b 1

call :build_frontend
if errorlevel 1 exit /b 1

call :create_startup_files
if errorlevel 1 exit /b 1

echo.
echo ============================================================
echo SETUP COMPLETED SUCCESSFULLY
echo ============================================================
echo.
echo Start the system using:
echo.
echo     deployment\start_system.bat
echo.
echo Application URL:
echo     http://127.0.0.1:%FRONTEND_PORT%
echo.
echo Backend API:
echo     http://127.0.0.1:%BACKEND_PORT%
echo.
pause
exit /b 0


:require_admin
net session >nul 2>&1
if not errorlevel 1 (
    echo [OK] Administrator privileges confirmed.
    exit /b 0
)

echo [ERROR] Please run this file as Administrator.
echo Right-click setup_windows.bat and select "Run as administrator".
pause
exit /b 1


:validate_project
echo [INFO] Validating project structure...

if not exist "%BACKEND_DIR%\manage.py" (
    echo [ERROR] Backend manage.py was not found:
    echo %BACKEND_DIR%\manage.py
    exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
    echo [ERROR] Frontend package.json was not found:
    echo %FRONTEND_DIR%\package.json
    exit /b 1
)

if not exist "%BACKEND_DIR%\requirements.txt" (
    echo [WARNING] backend\requirements.txt was not found.
)

if not exist "%DEPLOYMENT_DIR%requirements-production.txt" (
    echo [ERROR] deployment\requirements-production.txt was not found.
    exit /b 1
)

if not exist "%DEPLOYMENT_DIR%.env.example" (
    echo [ERROR] deployment\.env.example was not found.
    exit /b 1
)

echo [OK] Project structure validated.
exit /b 0


:check_python
echo.
echo [INFO] Checking Python installation...

where py >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%V in ('py --version 2^>^&1') do echo [OK] %%V
    set "PYTHON_COMMAND=py"
    exit /b 0
)

where python >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%V in ('python --version 2^>^&1') do echo [OK] %%V
    set "PYTHON_COMMAND=python"
    exit /b 0
)

echo [ERROR] Python was not found.
echo Install Python using the bundled installer in:
echo %INSTALLERS_DIR%
exit /b 1


:check_node
echo.
echo [INFO] Checking Node.js installation...

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js was not found.
    echo Install Node.js using the bundled installer in:
    echo %INSTALLERS_DIR%
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found.
    exit /b 1
)

for /f "delims=" %%V in ('node --version 2^>^&1') do echo [OK] Node.js %%V
for /f "delims=" %%V in ('npm --version 2^>^&1') do echo [OK] npm %%V

exit /b 0


:check_postgresql
echo.
echo [INFO] Checking PostgreSQL installation...

where psql >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PostgreSQL command-line tools were not found.
    echo Install PostgreSQL using the bundled installer in:
    echo %INSTALLERS_DIR%
    exit /b 1
)

where pg_isready >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pg_isready was not found.
    exit /b 1
)

pg_isready -h %DB_HOST% -p %DB_PORT% >nul 2>&1
if errorlevel 1 (
    echo [WARNING] PostgreSQL is not responding on port %DB_PORT%.
    echo Ensure the PostgreSQL service is installed and running.
    exit /b 1
)

echo [OK] PostgreSQL is available on port %DB_PORT%.

for /f "tokens=2 delims==" %%S in ('sc query state^= all ^| findstr /I "postgresql"') do (
    set "POSTGRES_SERVICE=%%S"
)

exit /b 0


:create_python_environment
echo.
echo [INFO] Creating Python virtual environment...

if exist "%VENV_DIR%" (
    echo [INFO] Removing any existing virtual environment so it is rebuilt for this computer...
    rmdir /s /q "%VENV_DIR%"
    if exist "%VENV_DIR%" (
        echo [ERROR] Could not remove the existing virtual environment.
        exit /b 1
    )
)

"%PYTHON_COMMAND%" -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo [ERROR] Could not create Python virtual environment.
    exit /b 1
)

echo [OK] Python virtual environment created.
exit /b 0


:install_python_dependencies
echo.
echo [INFO] Installing Python dependencies...

if exist "%PYTHON_PACKAGES%\*.whl" (
    echo [INFO] Local Python package cache found. Installing offline...
    "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip --no-index --find-links="%PYTHON_PACKAGES%"
    if errorlevel 1 echo [WARNING] Could not upgrade pip from the local cache. Continuing...

    "%VENV_DIR%\Scripts\python.exe" -m pip install --no-index --find-links="%PYTHON_PACKAGES%" -r "%DEPLOYMENT_DIR%requirements-production.txt"
) else (
    echo [INFO] No local Python package cache found. Installing from PyPI...
    "%VENV_DIR%\Scripts\python.exe" -m pip install -r "%DEPLOYMENT_DIR%requirements-production.txt"
)

if errorlevel 1 (
    echo [ERROR] Python dependency installation failed.
    exit /b 1
)

echo [OK] Python dependencies installed.
exit /b 0


:configure_environment
echo.
echo [INFO] Creating production environment configuration...

if exist "%ENV_FILE%" (
    echo [WARNING] Existing .env file found.
    choice /M "Replace existing .env with generated production configuration"
    if errorlevel 2 (
        echo [INFO] Existing .env file preserved.
        exit /b 0
    )
)

set "GENERATED_SECRET="

for /f "delims=" %%S in ('"%VENV_DIR%\Scripts\python.exe" -c "from secrets import token_urlsafe; print(token_urlsafe(64))"') do (
    set "GENERATED_SECRET=%%S"
)

if "%GENERATED_SECRET%"=="" (
    echo [ERROR] Could not generate Django SECRET_KEY.
    exit /b 1
)

(
    echo DEBUG=False
    echo.
    echo SECRET_KEY=%GENERATED_SECRET%
    echo.
    echo DB_NAME=%DB_NAME%
    echo DB_USER=%DB_USER%
    echo DB_PASSWORD=CHANGE_THIS_DATABASE_PASSWORD
    echo DB_HOST=%DB_HOST%
    echo DB_PORT=%DB_PORT%
    echo.
    echo ALLOWED_HOSTS=127.0.0.1,localhost
    echo.
    echo CORS_ALLOWED_ORIGINS=http://127.0.0.1:%FRONTEND_PORT%,http://localhost:%FRONTEND_PORT%
    echo.
    echo CSRF_TRUSTED_ORIGINS=http://127.0.0.1:%FRONTEND_PORT%,http://localhost:%FRONTEND_PORT%
    echo.
    echo BACKEND_HOST=127.0.0.1
    echo BACKEND_PORT=%BACKEND_PORT%
    echo FRONTEND_HOST=127.0.0.1
    echo FRONTEND_PORT=%FRONTEND_PORT%
) > "%ENV_FILE%"

echo.
echo The generated .env file contains a placeholder database password.
echo A masked prompt will set it while configuring the PostgreSQL role.

echo [OK] Environment configuration created.
exit /b 0


:create_database
echo.
echo [INFO] Creating PostgreSQL role and fresh database...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference = 'Stop';" ^
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false);" ^
    "$envFile = Join-Path $env:PROJECT_ROOT '.env';" ^
    "$appPtr = [IntPtr]::Zero;" ^
    "$adminPtr = [IntPtr]::Zero;" ^
    "try {" ^
    "  $appSecure = Read-Host 'Enter PostgreSQL password for bt_app' -AsSecureString;" ^
    "  if ($appSecure.Length -eq 0) { throw 'Application database password cannot be empty.' };" ^
    "  $adminSecure = Read-Host 'Enter PostgreSQL administrator password' -AsSecureString;" ^
    "  if ($adminSecure.Length -eq 0) { throw 'PostgreSQL administrator password cannot be empty.' };" ^
    "  $appPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($appSecure);" ^
    "  $adminPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminSecure);" ^
    "  $appPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($appPtr);" ^
    "  $envLines = [IO.File]::ReadAllLines($envFile);" ^
    "  $passwordLine = -1;" ^
    "  for ($i = 0; $i -lt $envLines.Length; $i++) { if ($envLines[$i].StartsWith('DB_PASSWORD=')) { if ($passwordLine -ge 0) { throw 'The .env file contains multiple DB_PASSWORD entries.' }; $passwordLine = $i } };" ^
    "  if ($passwordLine -lt 0) { throw 'The .env file does not contain DB_PASSWORD.' };" ^
    "  $quote = [string][char]39;" ^
    "  $identifierQuote = [string][char]34;" ^
    "  $passwordLiteral = $quote + $appPassword.Replace($quote, $quote + $quote) + $quote;" ^
    "  $roleIdentifier = $identifierQuote + $env:DB_USER.Replace($identifierQuote, $identifierQuote + $identifierQuote) + $identifierQuote;" ^
    "  $roleNameLiteral = $quote + $env:DB_USER.Replace($quote, $quote + $quote) + $quote;" ^
    "  $roleSql = 'DO $setup$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = ' + $roleNameLiteral + ') THEN CREATE ROLE ' + $roleIdentifier + ' LOGIN PASSWORD ' + $passwordLiteral + '; ELSE ALTER ROLE ' + $roleIdentifier + ' LOGIN PASSWORD ' + $passwordLiteral + '; END IF; END $setup$;';" ^
    "  $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($adminPtr);" ^
    "  $roleSql | & psql -h $env:DB_HOST -p $env:DB_PORT -U postgres -d postgres -v ON_ERROR_STOP=1;" ^
    "  if ($LASTEXITCODE -ne 0) { throw 'Could not create or configure the PostgreSQL role.' };" ^
    "  $dbNameLiteral = $quote + $env:DB_NAME.Replace($quote, $quote + $quote) + $quote;" ^
    "  $existingDatabase = & psql -h $env:DB_HOST -p $env:DB_PORT -U postgres -d postgres -tAc ('SELECT 1 FROM pg_database WHERE datname = ' + $dbNameLiteral);" ^
    "  if ($LASTEXITCODE -ne 0) { throw 'Could not check whether the PostgreSQL database exists.' };" ^
    "  if ($existingDatabase.Trim() -ne '1') { & createdb -h $env:DB_HOST -p $env:DB_PORT -U postgres $env:DB_NAME; if ($LASTEXITCODE -ne 0) { throw 'Could not create the PostgreSQL database.' } } else { Write-Host '[INFO] Database already exists. It will not be deleted.' };" ^
    "  $databaseIdentifier = $identifierQuote + $env:DB_NAME.Replace($identifierQuote, $identifierQuote + $identifierQuote) + $identifierQuote;" ^
    "  $ownerSql = 'ALTER DATABASE ' + $databaseIdentifier + ' OWNER TO ' + $roleIdentifier + ';';" ^
    "  $ownerSql | & psql -h $env:DB_HOST -p $env:DB_PORT -U postgres -d postgres -v ON_ERROR_STOP=1;" ^
    "  if ($LASTEXITCODE -ne 0) { throw 'Could not assign database ownership.' };" ^
    "  $escapedEnvPassword = $appPassword.Replace([string][char]92, [string][char]92 + [string][char]92).Replace($quote, [string][char]92 + $quote);" ^
    "  $envLines[$passwordLine] = 'DB_PASSWORD=' + $quote + $escapedEnvPassword + $quote;" ^
    "  [IO.File]::WriteAllLines($envFile, $envLines, [Text.UTF8Encoding]::new($false));" ^
    "  Write-Host '[OK] PostgreSQL role, database, and environment password are configured.';" ^
    "} catch {" ^
    "  [Console]::Error.WriteLine('[ERROR] Database setup failed: ' + $_.Exception.Message);" ^
    "  exit 1;" ^
    "} finally {" ^
    "  $env:PGPASSWORD = $null;" ^
    "  if ($appPtr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($appPtr) };" ^
    "  if ($adminPtr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($adminPtr) };" ^
    "  if ($appSecure) { $appSecure.Dispose() };" ^
    "  if ($adminSecure) { $adminSecure.Dispose() };" ^
    "  $appPassword = $null;" ^
    "}"

if errorlevel 1 (
    echo [ERROR] PostgreSQL setup did not complete.
    exit /b 1
)

echo [OK] PostgreSQL database is ready.
exit /b 0


:run_django_setup
echo.
echo [INFO] Running Django migrations and checks...

pushd "%BACKEND_DIR%"

"%VENV_DIR%\Scripts\python.exe" manage.py check --deploy
if errorlevel 1 (
    echo [WARNING] Django deployment checks reported issues.
    echo Review the output before using the system.
)

"%VENV_DIR%\Scripts\python.exe" manage.py migrate --noinput
if errorlevel 1 (
    echo [ERROR] Django migrations failed.
    popd
    exit /b 1
)

if not exist "%BACKEND_DIR%\staticfiles" mkdir "%BACKEND_DIR%\staticfiles"

"%VENV_DIR%\Scripts\python.exe" manage.py collectstatic --noinput
if errorlevel 1 (
    echo [ERROR] Static file collection failed.
    popd
    exit /b 1
)

echo.
echo Create the initial administrator account.
choice /C YN /M "Create the initial administrator account now"
if errorlevel 2 (
    echo [INFO] You can create the administrator later with:
    echo     "%VENV_DIR%\Scripts\python.exe" manage.py createsuperuser
    goto :django_setup_complete
)
echo.

"%VENV_DIR%\Scripts\python.exe" manage.py createsuperuser
if errorlevel 1 (
    echo [ERROR] Administrator account creation failed.
    popd
    exit /b 1
)

:django_setup_complete
popd

echo [OK] Django setup completed.
exit /b 0


:install_frontend_dependencies
echo.
echo [INFO] Installing frontend dependencies...

pushd "%FRONTEND_DIR%"

if not exist "package-lock.json" (
    echo [ERROR] frontend\package-lock.json was not found.
    popd
    exit /b 1
)

if exist "%NPM_CACHE%\_cacache" (
    echo [INFO] Local npm cache found. Installing offline...
    npm ci --offline --cache "%NPM_CACHE%"
) else (
    echo [INFO] No local npm cache found. Installing from the npm registry...
    npm ci
)

if errorlevel 1 (
    echo [ERROR] Frontend dependency installation failed.
    popd
    exit /b 1
)

popd

echo [OK] Frontend dependencies installed.
exit /b 0


:build_frontend
echo.
echo [INFO] Building React frontend for production...

pushd "%FRONTEND_DIR%"

(
    echo VITE_API_BASE_URL=http://127.0.0.1:%BACKEND_PORT%/api/v1
) > ".env.production"

npm run build
if errorlevel 1 (
    echo [ERROR] Frontend production build failed.
    popd
    exit /b 1
)

popd

echo [OK] Frontend production build completed.
exit /b 0


:create_startup_files
echo.
echo [INFO] Creating startup configuration...

if not exist "%DEPLOYMENT_DIR%start_system.bat" (
    echo [INFO] start_system.bat will be supplied separately.
)

if not exist "%DEPLOYMENT_DIR%stop_system.bat" (
    echo [INFO] stop_system.bat will be supplied separately.
)

(
    echo DB_NAME=%DB_NAME%
    echo DB_USER=%DB_USER%
    echo DB_PORT=%DB_PORT%
    echo BACKEND_PORT=%BACKEND_PORT%
    echo FRONTEND_PORT=%FRONTEND_PORT%
) > "%DEPLOYMENT_DIR%deployment-settings.txt"

echo [OK] Deployment settings saved.
exit /b 0
