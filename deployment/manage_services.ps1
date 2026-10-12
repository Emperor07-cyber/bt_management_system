param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Start", "Stop")]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
$DeploymentDir = Join-Path $ProjectRoot "deployment"
$BackendDir = Join-Path $ProjectRoot "backend"
$WaitressExe = Join-Path $BackendDir "venv\Scripts\waitress-serve.exe"
$LogDir = Join-Path $DeploymentDir "logs"

$Services = @(
    @{
        Name = "backend"
        Host = "127.0.0.1"
        Port = 8000
        Threads = 4
        Module = "config.wsgi:application"
        WorkingDirectory = $BackendDir
    },
    @{
        Name = "frontend"
        Host = "127.0.0.1"
        Port = 8080
        Threads = 2
        Module = "deployment.serve_frontend:application"
        WorkingDirectory = $ProjectRoot
    }
)

function Get-ServiceProcess($Service) {
    $PidFile = Join-Path $LogDir ($Service.Name + ".pid")
    if (-not (Test-Path -LiteralPath $PidFile -PathType Leaf)) {
        return $null
    }

    $PidText = (Get-Content -LiteralPath $PidFile -Raw).Trim()
    $ServicePid = 0
    if (-not [int]::TryParse($PidText, [ref]$ServicePid) -or $ServicePid -le 0) {
        throw "Invalid PID file for $($Service.Name): $PidFile"
    }

    $Process = Get-CimInstance Win32_Process -Filter "ProcessId = $ServicePid"
    if (-not $Process) {
        Remove-Item -LiteralPath $PidFile -Force
        return $null
    }

    $ExpectedListen = "--listen=$($Service.Host):$($Service.Port)"
    if (
        -not [string]::Equals($Process.ExecutablePath, $WaitressExe, [StringComparison]::OrdinalIgnoreCase) -or
        $Process.CommandLine.IndexOf($ExpectedListen, [StringComparison]::OrdinalIgnoreCase) -lt 0 -or
        $Process.CommandLine.IndexOf($Service.Module, [StringComparison]::OrdinalIgnoreCase) -lt 0
    ) {
        throw "PID $ServicePid in $PidFile is not the expected $($Service.Name) service. It was not stopped."
    }

    return [PSCustomObject]@{
        Id = $ServicePid
        PidFile = $PidFile
    }
}

function Stop-OwnedService($Service) {
    $OwnedProcess = Get-ServiceProcess $Service
    if (-not $OwnedProcess) {
        Write-Host "[INFO] $($Service.Name) is not running."
        return
    }

    Stop-Process -Id $OwnedProcess.Id -Force
    Remove-Item -LiteralPath $OwnedProcess.PidFile -Force
    Write-Host "[OK] Stopped $($Service.Name) process $($OwnedProcess.Id)."
}

function Wait-ForService($Service, $Process) {
    $Deadline = (Get-Date).AddSeconds(10)
    do {
        $Process.Refresh()
        if ($Process.HasExited) {
            throw "$($Service.Name) exited during startup. See $LogDir\$($Service.Name).log and $LogDir\$($Service.Name).error.log."
        }

        $Listener = Get-NetTCPConnection -State Listen -LocalPort $Service.Port -ErrorAction SilentlyContinue |
            Where-Object { $_.OwningProcess -eq $Process.Id } |
            Select-Object -First 1
        if ($Listener) {
            return
        }

        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $Deadline)

    throw "$($Service.Name) did not listen on port $($Service.Port). See $LogDir\$($Service.Name).log and $LogDir\$($Service.Name).error.log."
}

function Start-OwnedService($Service) {
    $ExistingProcess = Get-ServiceProcess $Service
    if ($ExistingProcess) {
        throw "$($Service.Name) is already running as process $($ExistingProcess.Id)."
    }

    $PortListener = Get-NetTCPConnection -State Listen -LocalPort $Service.Port -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($PortListener) {
        throw "Port $($Service.Port) is already in use by process $($PortListener.OwningProcess). No process was stopped."
    }

    $StdoutLog = Join-Path $LogDir ($Service.Name + ".log")
    $StderrLog = Join-Path $LogDir ($Service.Name + ".error.log")
    $PidFile = Join-Path $LogDir ($Service.Name + ".pid")
    $ArgumentLine = "--listen=$($Service.Host):$($Service.Port) --threads=$($Service.Threads) $($Service.Module)"
    $Process = Start-Process `
        -FilePath $WaitressExe `
        -ArgumentList $ArgumentLine `
        -WorkingDirectory $Service.WorkingDirectory `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog `
        -WindowStyle Hidden `
        -PassThru

    [IO.File]::WriteAllText($PidFile, [string]$Process.Id, [Text.Encoding]::ASCII)
    try {
        Wait-ForService $Service $Process
    }
    catch {
        try {
            Stop-OwnedService $Service
        }
        catch {
            [Console]::Error.WriteLine("[ERROR] Startup cleanup failed: $($_.Exception.Message)")
        }
        throw
    }

    Write-Host "[OK] Started $($Service.Name) on $($Service.Host):$($Service.Port) (PID $($Process.Id))."
}

if (-not (Test-Path -LiteralPath $LogDir -PathType Container)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

if ($Action -eq "Stop") {
    $StopFailed = $false
    foreach ($Service in @($Services[1], $Services[0])) {
        try {
            Stop-OwnedService $Service
        }
        catch {
            [Console]::Error.WriteLine("[ERROR] $($_.Exception.Message)")
            $StopFailed = $true
        }
    }

    if ($StopFailed) {
        exit 1
    }

    exit 0
}

if (-not (Test-Path -LiteralPath $WaitressExe -PathType Leaf)) {
    throw "Waitress executable was not found: $WaitressExe"
}

$StartedServices = @()
try {
    foreach ($Service in $Services) {
        Start-OwnedService $Service
        $StartedServices += $Service
    }
}
catch {
    [Console]::Error.WriteLine("[ERROR] $($_.Exception.Message)")
    if ($StartedServices.Count -gt 0) {
        foreach ($Service in @($StartedServices[($StartedServices.Count - 1)..0])) {
            try {
                Stop-OwnedService $Service
            }
            catch {
                [Console]::Error.WriteLine("[ERROR] Cleanup failed: $($_.Exception.Message)")
            }
        }
    }
    exit 1
}
