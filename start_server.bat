@echo off
cd /d "%~dp0"
echo Starting Nairobi Transport Monitor at http://127.0.0.1:5000
".venv\Scripts\python.exe" run.py
