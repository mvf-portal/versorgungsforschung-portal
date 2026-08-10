@echo off
REM Doppelklick-Starter fuer das lokale Studien-Update.
REM Voraussetzung: Umgebungsvariable ANTHROPIC_API_KEY ist gesetzt.
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update-studies.ps1"
echo.
echo Fertig. Fenster schliesst sich nach Tastendruck.
pause >nul
