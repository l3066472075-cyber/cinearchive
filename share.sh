#!/usr/bin/env bash
# 影境档案 · 一键分享脚本
# 作用：① 确保后端在跑  ② 用 autossh 开启公网隧道（断了自动重连）
# 用法：在 cinelib 目录下执行  ./share.sh
set -e
cd "$(dirname "$0")/backend"

# 1) 确保后端服务在运行
if curl -s -o /dev/null http://127.0.0.1:8000/api/v1/health; then
  echo "✔ 后端服务已在运行"
else
  echo "▶ 启动后端服务 ..."
  nohup .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 \
    > /tmp/cinelib_server.log 2>&1 &
  sleep 3
  echo "✔ 后端已启动"
fi

# 2) 开启公网隧道（autossh 断线自动重连）
echo "▶ 开启公网隧道，几秒后下方会打印分享网址（形如 https://xxxx.lhr.life）..."
echo "   （按 Ctrl+C 可退出；网址只在本次会话有效）"
echo ""
exec autossh -M 0 \
  -o "ServerAliveInterval 20" \
  -o "ServerAliveCountMax 3" \
  -o "ExitOnForwardFailure=yes" \
  -R 80:localhost:8000 nokey@localhost.run \
  -o StrictHostKeyChecking=no
