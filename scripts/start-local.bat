@echo off
echo Switching to local environment...
python scripts/switch-env.py local

echo.
echo Starting local development server...
cd server
"/cygdrive/c/Users/pangruitao/.conda/envs/ghf-server/python.exe" -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

pause