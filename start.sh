#!/bin/bash
# 电梯调度系统 - WebUI 模式启动脚本
# 同时启动 Simulator 服务器和 WebUI 前端

set -e

echo "=========================================="
echo "  电梯调度系统 - WebUI 模式"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "错误: 未找到 uv 命令"
    echo "请先安装 uv: https://docs.astral.sh/uv/"
    exit 1
fi

# 清理函数
cleanup() {
    echo ""
    echo "正在关闭服务..."
    kill $SIMULATOR_PID 2>/dev/null || true
    kill $WEBUI_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# 启动 Simulator 服务器
echo -e "${BLUE}[1/2]${NC} 启动 Simulator 服务器 (端口 8000)..."
uv run python simulator.py --host 127.0.0.1 --port 8000 --debug &
SIMULATOR_PID=$!
echo -e "${GREEN}✓${NC} Simulator 已启动 (PID: $SIMULATOR_PID)"

# 等待 Simulator 启动
echo "等待 Simulator 就绪..."
sleep 3

# 启动 WebUI
echo -e "${BLUE}[2/2]${NC} 启动 WebUI 前端 (端口 8080)..."
uv run python -m webui.app &
WEBUI_PID=$!
echo -e "${GREEN}✓${NC} WebUI 已启动 (PID: $WEBUI_PID)"

echo ""
echo "=========================================="
echo -e "${GREEN}✓ 系统启动完成！${NC}"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  - WebUI:     http://127.0.0.1:8080"
echo "  - Simulator: http://127.0.0.1:8000"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 等待进程
wait $SIMULATOR_PID $WEBUI_PID
