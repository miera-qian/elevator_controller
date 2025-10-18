# 电梯调度系统 (Elevator Scheduling System)

一个基于事件驱动的电梯调度模拟系统，支持多种调度算法和 WebUI 可视化。

---

## 📋 目录

- [系统概述](#系统概述)
- [快速开始](#快速开始)
- [系统架构](#系统架构)
- [已实现算法](#已实现算法)
- [环境依赖](#环境依赖)
- [使用指南](#使用指南)
- [开发文档](#开发文档)

---

## 系统概述

本系统实现了一个完整的电梯调度模拟器，包含：

- **物理模拟引擎**: 精确模拟电梯运动（加速、匀速、减速）
- **事件驱动架构**: Simulator 产生事件，算法响应事件
- **多种调度算法**: SCAN、优化SCAN、FCFS 等
- **WebUI 可视化**: 实时显示电梯状态、乘客流动
- **灵活配置**: 支持动态场景加载、max_ticks 控制

### 核心特性

✅ **动态配置**: WebUI 可动态设置 max_ticks，覆盖场景默认值
✅ **场景管理**: 支持运行时切换场景，无需重启
✅ **算法可插拔**: 统一的算法接口，易于扩展
✅ **完善文档**: 详细的系统架构和算法实现指南
✅ **无头模式**: 支持命令行批量测试

---

## 快速开始

### 方式1: WebUI 模式（推荐）

启动 WebUI 和 Simulator：

```bash
bash start.sh
```

然后访问 http://127.0.0.1:8080

### 方式2: 无头模式

直接运行模拟，适合批量测试：

```bash
# 使用默认配置
bash start_no_gui.sh

# 指定场景和算法
bash start_no_gui.sh -s large_morning_rush -a ScanController -t 500

# 查看帮助
bash start_no_gui.sh -h
```

---

## 系统架构

### 整体设计

```
┌─────────────────────────────────────────────┐
│           WebUI (Port 8080)                 │
│     - 可视化界面                             │
│     - 动态配置 (场景、算法、max_ticks)       │
└──────────────┬──────────────────────────────┘
               │ HTTP REST API
               ↓
┌─────────────────────────────────────────────┐
│        Simulator Server (Port 8000)         │
│     - 物理模拟引擎                           │
│     - 事件生成与分发                         │
│     - 乘客队列管理                           │
└─────────────────────────────────────────────┘
               ↑
               │ Events
               ↓
┌─────────────────────────────────────────────┐
│          Scheduling Algorithm               │
│     - ScanController                        │
│     - OptimizedScanAlgorithm                │
│     - SimpleFCFSAlgorithm                   │
└─────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 路径 | 职责 |
|------|------|------|
| **Simulator** | `simulator.py` | 物理模拟、事件生成 |
| **WebUI** | `webui/` | 前端可视化、控制面板 |
| **Algorithms** | `algo/` | 调度算法实现 |
| **Models** | `elevator_saga/core/models.py` | 数据模型定义 |

### 关键改进

本项目相比原始 `elevator_saga` 进行了以下改进：

1. **动态 max_ticks 控制** (详见 [SIMULATOR_CHANGES.md](SIMULATOR_CHANGES.md))
   - 新增 `user_max_ticks` 字段，优先级高于场景默认值
   - 新增 `/api/config/max_ticks` API
   - 跨场景和 reset 保留用户设置

2. **场景动态加载** (详见 [SIMULATOR_CHANGES.md](SIMULATOR_CHANGES.md))
   - 新增 `/api/load_scenario` API
   - 支持按名称加载场景，返回元数据

3. **算法问题修复** (详见 [algo/ALGORITHM_IMPLEMENTATION_GUIDE.md](algo/ALGORITHM_IMPLEMENTATION_GUIDE.md))
   - 移除 `assigned_calls` 机制（解决多电梯死锁）
   - 修正 SCAN 算法端点逻辑
   - 完整的 `internal_targets` 跟踪

---

## 已实现算法

### 1. ScanController (SCAN 扫描算法)
- **文件**: `algo/base_scan.py`
- **原理**: 电梯在一个方向上扫描到端点，然后掉头
- **特点**:
  - ✅ 完全修复，100% 完成率
  - ✅ 支持大规模场景（320人，20层，5电梯）
  - ✅ 多电梯协同，无死锁

### 2. OptimizedScanAlgorithm (优化 SCAN)
- **文件**: `algo/optimized_scan.py`
- **原理**: SCAN + 智能评分系统
- **特点**:
  - 基于距离、负载、方向的评分
  - 负载均衡
  - 顺路接客

### 3. SimpleFCFSAlgorithm (先来先服务)
- **文件**: `algo/simple_fcfs.py`
- **原理**: 简单的先到先得策略
- **特点**:
  - 实现简单，易于理解
  - 适合小规模场景

### 算法实现指南

详见 [algo/ALGORITHM_IMPLEMENTATION_GUIDE.md](algo/ALGORITHM_IMPLEMENTATION_GUIDE.md)，包含：
- ❌ 4个常见陷阱
- ✅ 最小可行算法模板
- 🧪 测试检查清单
- 🐛 调试技巧

---

## 环境依赖

### 系统要求

- **Python**: 3.10+
- **包管理器**: [uv](https://docs.astral.sh/uv/) (推荐) 或 pip
- **操作系统**: Linux / macOS / Windows (WSL)

### Python 依赖

核心依赖（已在 `pyproject.toml` 中定义）：

```toml
dependencies = [
    "flask>=3.0.0",
    "requests>=2.31.0",
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "websockets>=12.0",
]
```

### 安装步骤

1. **安装 uv** (推荐):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **克隆项目**:
   ```bash
   git clone <repository-url>
   cd elevator_controller
   ```

3. **安装依赖**:
   ```bash
   uv sync
   ```

4. **运行系统**:
   ```bash
   bash start.sh
   ```

---

## 使用指南

### WebUI 模式

1. **启动系统**:
   ```bash
   bash start.sh
   ```

2. **打开浏览器**: http://127.0.0.1:8080

3. **配置模拟**:
   - 选择场景（如 `large_morning_rush`）
   - 选择算法（如 `ScanController`）
   - 设置 max_ticks（如 `500`，可覆盖场景默认值）
   - 调整速度（1x - 10x）

4. **运行模拟**:
   - 点击 "开始模拟"
   - 实时查看电梯状态、乘客流动
   - 查看统计数据（平均等待时间、完成率等）

### 无头模式

适合批量测试或自动化：

```bash
# 基本用法
bash start_no_gui.sh -s small_upward_rush -a ScanController

# 设置 max_ticks
bash start_no_gui.sh -s large_morning_rush -t 500

# 使用不同算法
bash start_no_gui.sh -s medium_bidirectional -a OptimizedScanAlgorithm
```

### 可用场景

| 场景名称 | 乘客数 | 楼层数 | 电梯数 | 描述 |
|---------|--------|--------|--------|------|
| `small_upward_rush` | 80 | 10 | 3 | 小型上行高峰 |
| `medium_bidirectional` | 160 | 15 | 4 | 中型双向流量 |
| `large_morning_rush` | 320 | 20 | 5 | 大型早高峰 |

场景文件位于 `traffic/` 目录。

---

## 开发文档

### 📖 核心文档

1. **[SYSTEM_ARCHITECTURE_ANALYSIS.md](SYSTEM_ARCHITECTURE_ANALYSIS.md)**
   - 完整的系统架构解析
   - Simulator 运行逻辑
   - 事件驱动机制
   - 时序图和流程图

2. **[SIMULATOR_CHANGES.md](SIMULATOR_CHANGES.md)**
   - Simulator 相比原版的所有改进
   - 7个主要新增功能
   - 代码对比和使用示例

3. **[algo/ALGORITHM_IMPLEMENTATION_GUIDE.md](algo/ALGORITHM_IMPLEMENTATION_GUIDE.md)**
   - 算法实现最佳实践
   - 常见陷阱和解决方案
   - 最小可行算法模板
   - 调试技巧

### 🛠️ API 文档

#### Simulator API (Port 8000)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/state` | GET | 获取当前模拟状态 |
| `/api/step` | POST | 推进模拟 N 个 tick |
| `/api/reset` | POST | 重置模拟 |
| `/api/load_scenario` | POST | 加载指定场景 |
| `/api/config/max_ticks` | POST | 设置最大时长 |
| `/api/elevators/<id>/go_to_floor` | POST | 控制电梯前往楼层 |

#### WebUI API (Port 8080)

WebUI 通过 WebSocket 连接到后端：
- `/ws/simulation` - WebSocket 连接
- 消息类型: `start`, `pause`, `resume`, `stop`, `set_speed`

### 🎯 开发建议

#### 添加新算法

1. 继承 `BaseAlgorithm`:
   ```python
   from .base_algorithm import BaseAlgorithm

   class MyAlgorithm(BaseAlgorithm):
       def on_passenger_call(self, passenger, floor, direction):
           # 实现你的逻辑
           pass
   ```

2. 遵循最佳实践（见 `ALGORITHM_IMPLEMENTATION_GUIDE.md`）:
   - ✅ 跟踪 `internal_targets`
   - ✅ 空闲时分配任务
   - ❌ 不使用楼层级 `assigned_calls`

3. 在 `algo/__init__.py` 中导出:
   ```python
   from .my_algorithm import MyAlgorithm
   __all__ = [..., 'MyAlgorithm']
   ```

#### 添加新场景

在 `traffic/` 目录创建 JSON 文件：

```json
{
  "building": {
    "floors": 15,
    "elevators": 4,
    "elevator_capacity": 10,
    "duration": 300
  },
  "traffic": [
    {"tick": 0, "origin": 0, "destination": 5},
    {"tick": 1, "origin": 0, "destination": 10}
  ]
}
```

---

## 故障排查

### 常见问题

**Q: Simulator 无法启动**
```bash
# 检查端口占用
lsof -i :8000
# 或更换端口
uv run python simulator.py --port 8001
```

**Q: WebUI 连接失败**
```bash
# 确保 Simulator 先启动
curl http://127.0.0.1:8000/api/state
```

**Q: 算法卡住不动**
- 检查是否实现了所有必要的回调函数
- 查看 `logs/direct_simulation.log`
- 参考 `ALGORITHM_IMPLEMENTATION_GUIDE.md`

### 调试模式

启用详细日志：

```bash
# Simulator
uv run python simulator.py --debug

# 查看算法日志
tail -f logs/direct_simulation.log
```

---

## 许可证

[待补充]

---

## 致谢

- 基于 [elevator-saga](https://github.com/magwo/elevatorsaga) 项目
- 感谢所有贡献者

---

**最后更新**: 2025-10-18
**维护者**: [Your Name]
