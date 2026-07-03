@echo off
REM Run the FastAPI server with uvicorn on Windows

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
