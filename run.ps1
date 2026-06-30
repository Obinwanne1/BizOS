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

Write-Host "Starting BizOS at http://localhost:8501" -ForegroundColor Green
python -m streamlit run dashboard/app.py
