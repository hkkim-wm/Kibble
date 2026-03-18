Write-Host "Starting Kibble Web at http://localhost:8080" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Start-Process "http://localhost:8080"
python -m http.server 8080 --bind 127.0.0.1
