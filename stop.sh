#!/usr/bin/env bash

# Hệ Thống Smart Farm Multi-Pen & AI Vision
# Script dừng toàn bộ hệ thống đang chạy ngầm (Background mode)

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$PROJECT_DIR/start.sh" stop
