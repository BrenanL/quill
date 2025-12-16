# Quill Dictation Service Startup Script
# This script activates the virtual environment and runs Quill

param(
    [switch]$NoWindow  # Run without keeping window open after exit
)

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Change to script directory
Push-Location $ScriptDir

try {
    # Check if .venvpwsh exists
    $VenvPath = Join-Path $ScriptDir ".venvpwsh"
    $ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"

    if (-not (Test-Path $ActivateScript)) {
        Write-Host "Error: Virtual environment not found at $VenvPath" -ForegroundColor Red
        Write-Host "Run the following to create it:" -ForegroundColor Yellow
        Write-Host "  python -m venv .venvpwsh"
        Write-Host "  .venvpwsh\Scripts\Activate.ps1"
        Write-Host "  pip install uv && uv pip install ."
        if (-not $NoWindow) {
            Write-Host "`nPress any key to exit..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        exit 1
    }

    # Activate virtual environment
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & $ActivateScript

    # Check if config.yaml exists
    $ConfigPath = Join-Path $ScriptDir "config.yaml"
    if (-not (Test-Path $ConfigPath)) {
        Write-Host "Warning: config.yaml not found, using defaults" -ForegroundColor Yellow
        Write-Host "Copy config.example.yaml to config.yaml to customize settings" -ForegroundColor Yellow
    }

    # Run Quill dictation service
    Write-Host "Starting Quill Dictation Service..." -ForegroundColor Green
    Write-Host ""
    python -m Quill.dictation

} finally {
    # Return to original directory
    Pop-Location
}

if (-not $NoWindow) {
    Write-Host "`nQuill has stopped. Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
