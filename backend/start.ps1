# Change to the backend directory
Set-Location $PSScriptRoot

# Run uvicorn with the venv Python
& "$PSScriptRoot\..\.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
