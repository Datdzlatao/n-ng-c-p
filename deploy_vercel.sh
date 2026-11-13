#!/usr/bin/env bash

# Script tự động deploy Frontend lên Vercel kèm toàn bộ API keys / biến môi trường
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR/frontend"

echo "=========================================================="
echo "▲ BẮT ĐẦU DEPLOY FRONTEND LÊN VERCEL BẰNG VERCEL CLI"
echo "=========================================================="

SUPABASE_URL="https://sopqsxhuitqcmnvosjeq.supabase.co"
SUPABASE_ANON_KEY="sb_publishable_PdB8mBs-zLvYDpEXP-ds4A_YSktC8lm"
API_URL="https://dat-latitude-5590-2.tail2bda46.ts.net:8443"
WS_URL="wss://dat-latitude-5590-2.tail2bda46.ts.net:8443/ws"
FACE_API_URL="https://dat-latitude-5590-2.tail2bda46.ts.net:10000"

# Kiểm tra nếu chưa link dự án thì hướng dẫn hoặc link
if [ ! -d ".vercel" ]; then
    echo "🔗 Dự án chưa liên kết với Vercel. Đang liên kết..."
    npx vercel link
fi

echo "🚀 Đang tiến hành build & deploy Production kèm toàn bộ biến môi trường..."
npx vercel --prod \
    --build-env NEXT_PUBLIC_SUPABASE_URL="$SUPABASE_URL" \
    --build-env NEXT_PUBLIC_SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY" \
    --build-env NEXT_PUBLIC_API_URL="$API_URL" \
    --build-env NEXT_PUBLIC_WS_URL="$WS_URL" \
    --build-env NEXT_PUBLIC_FACE_API_URL="$FACE_API_URL" \
    --env NEXT_PUBLIC_SUPABASE_URL="$SUPABASE_URL" \
    --env NEXT_PUBLIC_SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY" \
    --env NEXT_PUBLIC_API_URL="$API_URL" \
    --env NEXT_PUBLIC_WS_URL="$WS_URL" \
    --env NEXT_PUBLIC_FACE_API_URL="$FACE_API_URL"

echo ""
echo "=========================================================="
echo "🎉 DEPLOY LÊN VERCEL HOÀN TẤT!"
echo "=========================================================="
