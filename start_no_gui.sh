#!/bin/bash
# 电梯调度系统 - 无头模式启动脚本
# 直接运行算法，不启动 WebUI

set -e

# 默认配置
SCENARIO="small_upward_rush"
ALGORITHM="ScanController"
MAX_TICKS=""
SERVER_URL="http://127.0.0.1:8000"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 显示帮助信息
show_help() {
    cat << EOF
电梯调度系统 - 无头模式

用法:
    $0 [选项]

选项:
    -s, --scenario SCENARIO      场景名称 (默认: small_upward_rush)
    -a, --algorithm ALGORITHM    算法名称 (默认: ScanController)
    -t, --max-ticks TICKS        最大时长 (默认: 使用场景默认值)
    -u, --url URL                Simulator 服务器地址 (默认: http://127.0.0.1:8000)
    -h, --help                   显示此帮助信息

可用场景:
    - small_upward_rush          小型上行高峰 (80人, 10层, 3电梯)
    - medium_bidirectional       中型双向流量 (160人, 15层, 4电梯)
    - large_morning_rush         大型早高峰 (320人, 20层, 5电梯)

可用算法:
    - ScanController             SCAN 扫描算法 (默认)
    - OptimizedScanAlgorithm     优化 SCAN 算法
    - SimpleFCFSAlgorithm        简单先来先服务

示例:
    # 使用默认配置运行
    $0

    # 运行大型场景，最多500 ticks
    $0 -s large_morning_rush -t 500

    # 使用优化算法运行中型场景
    $0 -s medium_bidirectional -a OptimizedScanAlgorithm

EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--scenario)
            SCENARIO="$2"
            shift 2
            ;;
        -a|--algorithm)
            ALGORITHM="$2"
            shift 2
            ;;
        -t|--max-ticks)
            MAX_TICKS="$2"
            shift 2
            ;;
        -u|--url)
            SERVER_URL="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "  电梯调度系统 - 无头模式"
echo "=========================================="
echo ""
echo "配置:"
echo "  场景:    $SCENARIO"
echo "  算法:    $ALGORITHM"
if [[ -n "$MAX_TICKS" ]]; then
    echo "  最大时长: $MAX_TICKS ticks"
else
    echo "  最大时长: (使用场景默认值)"
fi
echo "  服务器:  $SERVER_URL"
echo ""

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "错误: 未找到 uv 命令"
    echo "请先安装 uv: https://docs.astral.sh/uv/"
    exit 1
fi

# 清理函数
cleanup() {
    echo ""
    echo "正在关闭 Simulator..."
    kill $SIMULATOR_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# 启动 Simulator 服务器（后台）
echo -e "${BLUE}[1/2]${NC} 启动 Simulator 服务器..."
uv run python simulator.py --host 127.0.0.1 --port 8000 --debug > /dev/null 2>&1 &
SIMULATOR_PID=$!

# 等待 Simulator 启动
echo "等待 Simulator 就绪..."
sleep 3

# 检查 Simulator 是否启动成功
if ! curl -s "$SERVER_URL/api/state" > /dev/null 2>&1; then
    echo -e "${YELLOW}警告:${NC} 无法连接到 Simulator"
    echo "请确保 Simulator 在 $SERVER_URL 上运行"
    echo ""
    echo "提示: 可以在另一个终端手动启动 Simulator:"
    echo "  uv run python simulator.py"
    kill $SIMULATOR_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}✓${NC} Simulator 已就绪"
echo ""

# 构建 Python 命令
PYTHON_CMD="from algo import $ALGORITHM; import sys; "
PYTHON_CMD+="algo = $ALGORITHM(server_url='$SERVER_URL', enable_logging=True); "

# 如果指定了 max_ticks，需要先设置
if [[ -n "$MAX_TICKS" ]]; then
    PYTHON_CMD+="import requests; "
    PYTHON_CMD+="requests.post('$SERVER_URL/api/config/max_ticks', json={'max_ticks': $MAX_TICKS}); "
fi

# 加载场景
PYTHON_CMD+="import requests; "
PYTHON_CMD+="resp = requests.post('$SERVER_URL/api/load_scenario', json={'scenario_name': '$SCENARIO'}); "
PYTHON_CMD+="print(f'场景已加载: {resp.json()}') if resp.status_code == 200 else sys.exit(f'加载场景失败: {resp.text}'); "

# 启动算法
PYTHON_CMD+="print('开始运行模拟...'); "
PYTHON_CMD+="algo.start(); "
PYTHON_CMD+="print('模拟完成！')"

# 运行算法
echo -e "${BLUE}[2/2]${NC} 启动算法: $ALGORITHM"
echo "=========================================="
echo ""

uv run python -c "$PYTHON_CMD"

EXIT_CODE=$?

# 清理
cleanup

exit $EXIT_CODE
