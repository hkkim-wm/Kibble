@echo off
echo Starting Kibble Web at http://localhost:8080
echo Press Ctrl+C to stop
python -m http.server 8080 --bind 127.0.0.1 2>nul || (
    echo Python not found. Trying npx serve...
    npx serve -l 8080 2>nul || (
        echo Could not start server. Please install Python or Node.js.
        pause
    )
)
