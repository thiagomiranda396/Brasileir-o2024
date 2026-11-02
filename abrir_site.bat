@echo off
rem Abre o site do Brasileirao 2024 no navegador (servidor local, sem instalar nada).
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\servidor_local.ps1"
