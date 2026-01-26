@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   🚀 启动 EvoCorps 开发环境
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] 检查依赖...
call npm install --silent

echo.
echo [2/2] 启动服务...
echo.
call npm start

pause
