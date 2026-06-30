# BizOS launcher — run from bizos/ directory
$env:PYTHONPATH = $PSScriptRoot
Write-Host "Starting BizOS at http://localhost:8501" -ForegroundColor Green
streamlit run dashboard/app.py
