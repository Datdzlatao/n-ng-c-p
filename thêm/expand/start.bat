@echo off
chcp 65001 > nul
title HE THONG DIEM DANH STEM — EDUSAMS LAUNCHER
color 0A

echo ============================================================
echo   🎓 HỆ THỐNG ĐIỂM DANH THÔNG MINH STEM — WINDOWS LAUNCHER
echo ============================================================
echo.

set "ROOT_DIR=%~dp0"
set "VENV_ACTIVATE="
set "PYTHON_EXE="

:: 1. Tự động phát hiện môi trường ảo Python (Virtual Environment)
if exist "%ROOT_DIR%venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=call "%ROOT_DIR%venv\Scripts\activate.bat""
    set "PYTHON_EXE="%ROOT_DIR%venv\Scripts\python.exe""
    echo [OK] Tìm thấy môi trường ảo: venv/
) else if exist "%ROOT_DIR%.venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=call "%ROOT_DIR%.venv\Scripts\activate.bat""
    set "PYTHON_EXE="%ROOT_DIR%.venv\Scripts\python.exe""
    echo [OK] Tìm thấy môi trường ảo: .venv/
) else if exist "%ROOT_DIR%backend\venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=call "%ROOT_DIR%backend\venv\Scripts\activate.bat""
    set "PYTHON_EXE="%ROOT_DIR%backend\venv\Scripts\python.exe""
    echo [OK] Tìm thấy môi trường ảo: backend/venv/
) else if exist "%ROOT_DIR%backend\.venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=call "%ROOT_DIR%backend\.venv\Scripts\activate.bat""
    set "PYTHON_EXE="%ROOT_DIR%backend\.venv\Scripts\python.exe""
    echo [OK] Tìm thấy môi trường ảo: backend/.venv/
)

:: 2. Kiểm tra Python nếu chưa có venv
if "%PYTHON_EXE%"=="" (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        python --version >nul 2>nul
        if %errorlevel% equ 0 (
            set "PYTHON_EXE=python"
            set "VENV_ACTIVATE=rem No venv"
            echo [OK] Sử dụng Python hệ thống.
        )
    )
    if "%PYTHON_EXE%"=="" (
        where py >nul 2>nul
        if %errorlevel% equ 0 (
            set "PYTHON_EXE=py -3"
            set "VENV_ACTIVATE=rem No venv"
            echo [OK] Sử dụng Python Launcher (py -3).
        )
    )
)

if "%PYTHON_EXE%"=="" (
    color 0C
    echo [LỖI] Không tìm thấy Python trên hệ thống!
    echo Vui lòng tải và cài đặt Python 3.10+ từ: https://www.python.org/downloads/
    echo Lưu ý: Hãy tích chọn "Add Python to PATH" trong trình cài đặt.
    echo.
    pause
    exit /b 1
)

:: 3. Kiểm tra và giải phóng cổng 8000 nếu đang bị treo bởi phiên chạy trước
netstat -ano | findstr :8000 | findstr LISTENING >nul 2>nul
if %errorlevel% equ 0 (
    echo [CẢNH BÁO] Cổng 8000 đang được sử dụng! Đang giải phóng cổng...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
        taskkill /f /pid %%a >nul 2>nul
    )
    timeout /t 1 /nobreak > nul
)

:: 4. Khởi động Backend API Server (Port 8000)
echo [*] Đang khởi động Backend API Server (Port 8000)...
start "STEM - Backend API Server" cmd /k "chcp 65001 > nul && title STEM Backend Server (Port 8000) && cd /d "%ROOT_DIR%backend" && %VENV_ACTIVATE% && python run.py"

:: 5. Kiểm tra Node.js & npm để chạy Frontend Dev Server (Port 5173)
set "HAS_NPM=0"
where npm >nul 2>nul
if %errorlevel% equ 0 (
    set "HAS_NPM=1"
    echo [*] Đang khởi động Frontend Web Vite (Port 5173)...
    start "STEM - Frontend Web Vite" cmd /k "chcp 65001 > nul && title STEM Frontend Vite (Port 5173) && cd /d "%ROOT_DIR%frontend-web" && if not exist node_modules (echo [Frontend] Cài đặt dependencies... && npm install) && npm run dev"
) else (
    echo [INFO] Không tìm thấy Node.js/npm. Chạy ở chế độ All-in-One:
    echo        Frontend và Dashboard được phục vụ trực tiếp qua Backend FastAPI.
)

:: 6. Đợi 3 giây để server khởi động và mở trình duyệt
echo [*] Đang chờ dịch vụ khởi chạy...
timeout /t 3 /nobreak > nul

echo [*] Đang mở trình duyệt...
if "%HAS_NPM%"=="1" (
    start http://localhost:5173
) else (
    start http://localhost:8000/app/index.html
)

cls
color 0B
echo ============================================================
echo   🎉 HỆ THỐNG ĐÃ ĐƯỢC KHỞI ĐỘNG THÀNH CÔNG TRÊN WINDOWS!
echo ============================================================
echo.
if "%HAS_NPM%"=="1" (
echo   🌐 Trang chủ Web React:       http://localhost:5173
echo   📊 Dashboard 5 Vai Trò:       http://localhost:5173/app/index.html
) else (
echo   🌐 Trang chủ Web All-in-One:   http://localhost:8000
echo   📊 Dashboard 5 Vai Trò:       http://localhost:8000/app/index.html
)
echo   ⚡ Backend REST API:          http://localhost:8000
echo   📚 Tài liệu Swagger Docs:     http://localhost:8000/docs
echo.
echo   👑 Tài khoản Quản trị Tối cao: admin / Admin@EduSams2026#Secure
echo ============================================================
echo   📷 ĐỂ CHẠY TRẠM CAMERA AI ĐIỂM DANH:
echo      Nhấp đúp chuột vào file: run_camera.bat
echo.
echo   🛑 ĐỂ DỪNG TOÀN BỘ HỆ THỐNG:
echo      Nhấp đúp chuột vào file: stop.bat
echo ============================================================
echo.
echo Nhấn phím bất kỳ để đóng cửa sổ thông báo này (Dịch vụ vẫn tiếp tục chạy ngầm).
pause > nul
