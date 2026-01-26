@echo off
echo ========================================
echo Starting EvoCorps Frontend System
echo ========================================
echo.

echo [1/2] Starting Backend API Server (Port 5001)...
start "EvoCorps-Backend-API" cmd /k python frontend_api.py
timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend Dev Server (Port 5173)...
cd frontend
start "EvoCorps-Frontend" cmd /k npm run dev
cd ..

echo.
echo ========================================
echo All services started!
echo ========================================
echo Backend API: http://127.0.0.1:5001
echo Frontend:    http://localhost:5173
echo ========================================
echo.
echo Press any key to exit (services will continue running)...
pause >nul
