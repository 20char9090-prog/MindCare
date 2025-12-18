@echo off
REM Ejecuta start_server.ps1 (debe estar en la misma carpeta) con PowerShell
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0start_server.ps1'"
pause
