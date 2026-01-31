Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info([string]$msg) {
    Write-Host "[yt-dlp-gui] $msg"
}

function Invoke-External([string]$exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed ($LASTEXITCODE): $exe $($arguments -join ' ')"
    }
}

function Test-PipAvailable([string]$pythonExe) {
    & $pythonExe -c "import pip" 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Resolve-PythonPackageInstaller([string]$venvPython) {
    if (Test-PipAvailable $venvPython) { return "pip" }

    Write-Info "pip not found in this venv; trying ensurepip..."
    try {
        Invoke-External $venvPython @("-m", "ensurepip", "--upgrade")
    } catch {
        # ensurepip isn't always available (e.g., some uv/embedded builds)
        Write-Info "ensurepip failed (will try uv if available)."
    }
    if (Test-PipAvailable $venvPython) { return "pip" }

    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -ne $uvCmd) { return "uv" }

    return "none"
}

try {
    # Always run from the project directory.
    $root = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location $root

    # Be resilient on older PowerShells.
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    } catch { }

    $venvDir = Join-Path $root ".venv"
    $activate = Join-Path $venvDir "Scripts\Activate.ps1"

    if (-not (Test-Path $activate)) {
        Write-Info "Creating virtual environment (.venv)..."
        Invoke-External "python" @("-m", "venv", ".venv")
    }

    Write-Info "Activating .venv..."
    . $activate

    # Prevent Python from dropping into an interactive REPL after running a module
    # if the user's environment has PYTHONINSPECT set.
    Remove-Item Env:PYTHONINSPECT -ErrorAction SilentlyContinue

    Write-Info "Ensuring dependencies are installed..."
    $venvPython = (Get-Command python).Source
    $installer = Resolve-PythonPackageInstaller $venvPython
    Write-Info "Installer selected: $installer"
    try {
        if ($installer -eq "pip") {
            Invoke-External $venvPython @("-m", "pip", "install", "-U", "pip")
            Invoke-External $venvPython @("-m", "pip", "install", "-r", "requirements.txt")
        } elseif ($installer -eq "uv") {
            # Use uv to install into the active venv (explicit --python for safety).
            Invoke-External "uv" @("pip", "install", "--python", $venvPython, "-r", "requirements.txt")
        } else {
            Write-Info "Neither pip nor uv is available; skipping dependency install."
        }
    } catch {
        Write-Info "Dependency install failed (continuing):"
        Write-Info $_.Exception.Message
    }

    # Check for yt-dlp updates by comparing current version to GitHub latest release tag.
    $current = (& $venvPython -m yt_dlp --version 2>$null).Trim()
    if (-not $current) { $current = "(unknown)" }
    Write-Info "Current yt-dlp version: $current"

    try {
        $headers = @{ "User-Agent" = "yt-dlp-gui-startup-script" }
        $latest = (Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest").tag_name
        if (-not $latest) { throw "No tag_name found." }
        Write-Info "Latest yt-dlp release: $latest"

        if ($current -ne $latest) {
            Write-Info "Updating yt-dlp..."
            try {
                if (Test-PipAvailable $venvPython) {
                    Invoke-External $venvPython @("-m", "pip", "install", "-U", "yt-dlp")
                } else {
                    Invoke-External "uv" @("pip", "install", "--python", $venvPython, "-U", "yt-dlp")
                }
            } catch {
                Write-Info "yt-dlp update failed (continuing):"
                Write-Info $_.Exception.Message
            }
        } else {
            Write-Info "yt-dlp is up to date."
        }
    } catch {
        Write-Info "Could not check latest yt-dlp release (continuing)."
        Write-Info $_.Exception.Message
    }

    Write-Info "Launching GUI..."
    Invoke-External $venvPython @("yt_dlp_gui.py")
}
catch {
    Write-Host "[yt-dlp-gui] ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "[yt-dlp-gui] Press Enter to close..."
    [void](Read-Host)
    exit 1
}
