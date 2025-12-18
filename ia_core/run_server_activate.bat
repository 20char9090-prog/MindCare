@echo off
REM Abre PowerShell, activa el venv y ejecuta api_chat.py en la misma ventana (no la cierra)
powershell -NoProfile -ExecutionPolicy Bypass -NoExit -Command "cd 'C:\Users\carlos\Desktop\MindCare1\ia_core'; . '.\.venv\Scripts\Activate.ps1'; python api_chat.py"
pause
