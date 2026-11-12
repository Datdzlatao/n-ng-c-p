@echo off
chcp 65001 > nul
title TRAM CAMERA AI DIEM DANH STEM — EDUSAMS
color 0D

echo ============================================================
echo   📷 TRẠM CAMERA AI ĐIỂM DANH STEM (OPENCV + TRACKER + QR)
echo ============================================================
echo.

set "ROOT_DIR=%~dp0"
set "VENV_ACTIVATE="
set "PYTHON_EXE="

:: 1. Tự động phát hiện môi trường ảo Python (Virtual Environment)
if exist "%ROOT_DIR%venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=call "%ROOT_DIR%venv\Scripts\activate.bat""
    set "PYTHON_EXE="%ROOT_DIR%venv\Scripts\python.exe""
) else if exist "%ROOT_DIR%.venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=call "%ROOT_DIR%.venv\Scripts\activate.bat""
    set "PYTHON_EXE="%ROOT_DIR%.venv\Scripts\python.exe""
) else if exist "%ROOT_DIR%backend\venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=call "%ROOT_DIR%backend\venv\Scripts\activate.bat""
    set "PYTHON_EXE="%ROOT_DIR%backend\venv\Scripts\python.exe""
) else if exist "%ROOT_DIR%backend\.venv\Scripts\activate.bat" (
    set "VENV_ACTIVATE=call "%ROOT_DIR%backend\.venv\Scripts\activate.bat""
    set "PYTHON_EXE="%ROOT_DIR%backend\.venv\Scripts\python.exe""
)

if "%PYTHON_EXE%"=="" (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PYTHON_EXE=python"
        set "VENV_ACTIVATE=rem No venv"
    ) else (
        where py >nul 2>nul
        if %errorlevel% equ 0 (
            set "PYTHON_EXE=py -3"
            set "VENV_ACTIVATE=rem No venv"
        )
    )
)

if "%PYTHON_EXE%"=="" (
    color 0C
    echo [LỖI] Không tìm thấy Python trên hệ thống!
    echo Vui lòng cài đặt Python 3.10+ và tích chọn "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

:: 2. Chuyển vào thư mục edge
cd /d "%ROOT_DIR%edge"
if "%VENV_ACTIVATE%" neq "" %VENV_ACTIVATE%

:: 3. Kiểm tra kết nối tới Backend (Port 8000)
netstat -ano | findstr :8000 | findstr LISTENING >nul 2>nul
if %errorlevel% neq 0 (
    echo ------------------------------------------------------------
    echo [CẢNH BÁO] Chưa phát hiện Backend API đang chạy trên cổng 8000!
    echo Khuyến nghị: Bạn nên mở file 'start.bat' trước để Camera có thể
    echo đồng bộ danh sách học sinh và gửi dữ liệu điểm danh lên máy chủ.
    echo (Camera vẫn sẽ chạy chế độ ngoại tuyến nếu đã có dữ liệu đệm).
    echo ------------------------------------------------------------
    echo.
)

:: 4. Xử lý tham số truyền vào (nếu có)
if not "%~1"=="" (
    echo [*] Đang khởi chạy Camera AI với tham số: %*
    python main.py %*
    goto end
)

:: 5. Menu tương tác thông minh cho người dùng Windows
echo ============================================================
echo   CHỌN CHẾ ĐỘ KHỞI CHẠY CAMERA AI:
echo ------------------------------------------------------------
echo   [1] Trạm Đa Camera Tự Động (Supervisor - Quản lý tự động) [Mặc định]
echo   [2] Chạy trực tiếp Webcam 0 (Có cửa sổ hiển thị OpenCV GUI)
echo   [3] Trạm Đa Camera Tự Động kèm Cửa sổ OpenCV GUI (--gui)
echo   [4] Thoát
echo ============================================================
echo.

choice /c 1234 /t 5 /d 1 /m "Nhập lựa chọn của bạn (Tự động chọn [1] sau 5 giây): "
set "SEL=%errorlevel%"

if "%SEL%"=="4" (
    echo Thoát chương trình.
    exit /b 0
)

if "%SEL%"=="3" (
    cls
    echo [*] Đang khởi động Trạm Đa Camera AI với giao diện GUI...
    echo [*] Nhấn Ctrl+C hoặc phím Q trên cửa sổ camera để thoát.
    python supervisor.py --gui
    goto end
)

if "%SEL%"=="2" (
    cls
    echo [*] Đang mở trực tiếp Webcam 0 với giao diện GUI...
    echo [*] Nhấn phím Q hoặc ESC trên cửa sổ camera để dừng.
    python main.py --camera 0
    goto end
)

:: Mặc định: Lựa chọn 1
cls
echo [*] Đang khởi chạy Trạm Đa Camera AI (Supervisor)...
echo [*] Hệ thống sẽ tự động đồng bộ cấu hình từ Web Dashboard.
echo [*] Xem luồng camera trực tiếp tại Web Dashboard hoặc http://localhost:8081
echo [*] Nhấn Ctrl+C để dừng toàn bộ trạm camera an toàn.
echo.
python supervisor.py

:end
echo.
echo [*] Đã dừng trạm Camera AI.
pause
