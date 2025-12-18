@echo off
REM Ejecuta directamente el python del venv para evitar activar el script
cd /d "%~dp0"
"%~dp0\.venv\Scripts\python.exe" "%~dp0api_chat.py"
pause
