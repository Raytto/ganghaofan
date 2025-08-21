@echo off
echo Starting local development server with logging...
cd /d "E:\ppfiles\mp\ganghaofan"

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Start server and redirect output to log file
echo Starting server at %date% %time% > logs\server.log
"C:\Users\pangruitao\.conda\envs\ghf-server\python.exe" -m uvicorn server.app:app --reload --host 0.0.0.0 --port 8000 >> logs\server.log 2>&1

echo Server stopped at %date% %time% >> logs\server.log
echo Server stopped. Check logs\server.log for details.
pause