# BizOS launcher — run from bizos/ directory
$env:PYTHONPATH = $PSScriptRoot

# Load .env
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
        }
    }
    Write-Host ".env loaded" -ForegroundColor Green
} else {
    Write-Host "WARNING: .env not found — agents need ANTHROPIC_API_KEY" -ForegroundColor Yellow
}

# Start scheduler in background
Write-Host "Starting BizOS Scheduler..." -ForegroundColor Cyan
Start-Process -FilePath "python" -ArgumentList "scheduler.py" -WorkingDirectory $PSScriptRoot -WindowStyle Minimized

Start-Sleep -Seconds 1

# Start dashboard
Write-Host "Starting BizOS Dashboard at http://localhost:8501" -ForegroundColor Green
python -m streamlit run dashboard/app.py
