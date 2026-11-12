@echo off
chcp 65001 > nul
title DUNG HE THONG DIEM DANH STEM
color 0C

echo ============================================================
echo   🛑 ĐANG DỪNG TOÀN BỘ HỆ THỐNG ĐIỂM DANH STEM (EDUSAMS)
echo ============================================================
echo.

:: 1. Dừng Camera Stream Ports (8081, 8082, 8083)
echo [*] Đang giải phóng các cổng Camera AI (8081, 8082)...
for %%p in (8081 8082 8083) do (
    for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :%%p ^| findstr LISTENING') do (
        taskkill /f /pid %%a >nul 2>nul
    )
)

:: 2. Dừng Frontend Vite (Port 5173)
echo [*] Đang giải phóng cổng Frontend Vite (5173)...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>nul
)

:: 3. Dừng Backend FastAPI (Port 8000)
echo [*] Đang giải phóng cổng Backend FastAPI (8000)...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>nul
)

:: 4. Đóng các cửa sổ CMD tương ứng theo tiêu đề
taskkill /fi "WINDOWTITLE eq STEM - Backend API Server*" /f >nul 2>nul
taskkill /fi "WINDOWTITLE eq STEM - Frontend Web Vite*" /f >nul 2>nul
taskkill /fi "WINDOWTITLE eq TRAM CAMERA AI DIEM DANH STEM*" /f >nul 2>nul
taskkill /fi "WINDOWTITLE eq STEM Backend Server*" /f >nul 2>nul
taskkill /fi "WINDOWTITLE eq STEM Frontend Vite*" /f >nul 2>nul

echo.
echo ============================================================
echo   ✅ ĐÃ DỪNG TOÀN BỘ CÁC DỊCH VỤ THÀNH CÔNG!
echo ============================================================
echo.
timeout /t 3
exit /b 0
