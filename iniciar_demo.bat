@echo off
rem Duplo clique: arranca a API e o dashboard e abre o browser.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar_demo.ps1" %*
echo.
pause
