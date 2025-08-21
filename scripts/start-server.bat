@echo off
echo Starting local development server...
cd /d "E:\ppfiles\mp\ganghaofan"

REM Set environment variables
set PYTHONPATH=%CD%

REM Start server with explicit Python path and nohup-like behavior
start "GHF-Server" /B "C:\Users\pangruitao\.conda\envs\ghf-server\python.exe" -m uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

echo Server started in background
echo Check http://127.0.0.1:8000/health to verify
pause