#!/usr/bin/env bash

# Dừng 2 API Backend & AI Vision đang chạy nền

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$PROJECT_DIR/start_apis.sh" stop
