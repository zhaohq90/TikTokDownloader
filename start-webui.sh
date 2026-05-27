#!/bin/bash
# ============================================================
# TikTokDownloader Web UI 一键启动脚本
# ============================================================

# 项目根目录（脚本所在目录）
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

VENV_DIR="$PROJECT_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python3"

# 检查虚拟环境
if [ ! -f "$VENV_PYTHON" ]; then
    echo "[错误] 未找到虚拟环境 Python: $VENV_PYTHON"
    echo "请先创建: python3.12 -m venv venv && ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

echo "[信息] 虚拟环境 Python: $VENV_PYTHON"
echo "[信息] Python 版本: $($VENV_PYTHON --version 2>&1)"

# 启动 Web UI
echo "[信息] 启动 Web UI..."
echo "----------------------------------------"
exec "$VENV_PYTHON" webui.py
