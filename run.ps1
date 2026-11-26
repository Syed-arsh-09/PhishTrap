# Start PhishTrap API and Web Console using the local virtual environment
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Starting PhishTrap Server on http://localhost:8000        " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
& ".\venv\Scripts\python.exe" -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
