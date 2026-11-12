#!/usr/bin/env bash
# =============================================================================
#  KHỞI ĐỘNG TRẠM CAMERA AI ĐIỂM DANH (OPENCV + YUNET + SFACE)
# =============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR/edge"

# Tìm python có sẵn OpenCV
if [ -f "$DIR/venv/bin/python" ]; then
    PYTHON="$DIR/venv/bin/python"
elif [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
elif [ -f "$DIR/backend/venv/bin/python" ]; then
    PYTHON="$DIR/backend/venv/bin/python"
else
    PYTHON="python3"
fi

echo "============================================================"
echo "📷 ĐANG KHỞI ĐỘNG HỆ THỐNG ĐA CAMERA AI ĐIỂM DANH STEM..."
echo "============================================================"
echo "🌐 Tự động nạp cấu hình và đồng bộ toàn bộ camera từ Dashboard."
echo "💡 Nhấn Ctrl+C để dừng toàn bộ hệ thống camera an toàn."
echo "============================================================"

if [ "$#" -gt 0 ]; then
    $PYTHON main.py "$@"
else
    $PYTHON supervisor.py "$@"
fi
