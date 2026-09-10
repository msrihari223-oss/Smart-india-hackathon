@echo off
title Social Media Analytics Intelligence Server
echo =================================================================
echo   AETHERIA // AI Social Media Intelligence Backend Engine
echo =================================================================
echo.
echo Starting FastAPI & WebSocket live stream on http://localhost:8000/ ...
echo.

cd /d "%~dp0"

:: Open default web browser after short delay
start "" http://localhost:8000/

:: Start Uvicorn ASGI Server
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

pause
