# Elevator Scheduling Algorithm

优化的电梯调度算法，旨在最小化乘客等待时间的平均值和P95。

## 项目结构

```
elevator_homework/
├── main.py                   # CLI 入口程序
├── elevator_controller.py    # 传统入口程序
├── algo/                     # 算法实现目录
│   ├── __init__.py          # 包初始化
│   ├── base_algorithm.py    # 算法基类
│   ├── optimized_scan.py    # 优化SCAN算法
│   ├── rl_dqn.py            # 强化学习算法
│   ├── hybrid_scan_rl.py    # 混合算法（推荐）
│   └── README.md            # 算法扩展指南
├── webui/                    # Web 可视化界面 ⭐
│   ├── app.py               # FastAPI 应用
│   ├── mock_simulation.py   # Mock 模拟引擎
│   └── static/              # 前端资源
│       ├── index.html       # 主页面
│       ├── css/style.css    # 样式表
│       └── js/              # JavaScript
│           ├── app.js       # 应用逻辑
│           ├── renderer.js  # Canvas 渲染
│           └── websocket.js # WebSocket 管理
├── tests/                    # 测试工具目录
│   ├── generate_test_data.py # 测试数据生成器
│   ├── run_tests.py          # 批量测试工具（推荐）
│   └── batch_test.py         # 测试报告生成器
├── data/                     # 测试数据集（10个场景）
│   ├── small_morning_rush.json
│   ├── medium_inter_floor.json
│   ├── large_mixed.json
│   └── ...
├── traffic/                  # 示例流量数据
│   └── sample_traffic.json
├── docs/                     # 文档目录
│   ├── quick_start_guide.md        # 快速开发指南（英文）
│   ├── simulator_api_reference.md  # 模拟器API参考（所有可用数据和指标）
│   ├── algorithm.md                # 算法设计文档
│   ├── testing_guide.md            # 测试指南
│   ├── auto_test_usage.md          # 自动化测试快速使用
│   └── automated_testing_guide.md  # 自动化测试完整指南
├── test_results/            # 测试报告输出目录
├── pyproject.toml           # uv项目配置
└── README.md                # 本文件
```

## 算法架构

本项目采用模块化设计，算法实现位于 `algo/` 目录：

- **BaseAlgorithm**: 抽象基类，定义统一接口
- **OptimizedScanAlgorithm**: 优化SCAN算法（启发式）
- **RLDQNAlgorithm**: 强化学习Q-learning算法
- **HybridScanRLAlgorithm**: 混合SCAN-RL算法 ⭐ 推荐

### 已实现算法

#### 1. OptimizedScanAlgorithm (优化SCAN算法)

**类型**: 启发式算法

**特性**:
- SCAN算法：电梯持续向一个方向移动，直到该方向没有更多请求
- 最近邻分配：为空闲电梯分配最近的等待乘客
- 负载均衡：在多个电梯之间智能分配任务
- 智能评分系统：综合考虑距离、负载、方向匹配度

**适用场景**: 中小型建筑、混合流量模式、通用场景

#### 2. RLDQNAlgorithm (强化学习Q-learning算法)

**类型**: 机器学习算法

**特性**:
- Q-learning：通过试错学习最优策略
- 经验回放：存储历史经验用于训练
- Epsilon-greedy探索：平衡探索与利用
- 模型持久化：支持保存/加载学习结果

**适用场景**: 需要自适应学习、流量模式固定但未知、长期运行优化

**使用方法**:
```python
from algo import RLDQNAlgorithm

# 训练模式
algorithm = RLDQNAlgorithm(training_mode=True)
algorithm.start()
# 运行多次后保存模型
algorithm.save_model()

# 生产模式
algorithm = RLDQNAlgorithm(training_mode=False, model_path="models/rl_elevator.pkl")
algorithm.start()
```

#### 3. HybridScanRLAlgorithm (混合SCAN-RL算法) ⭐ 推荐

**类型**: 混合算法（启发式 + 机器学习）

**核心理念**: 结合两种算法的优势，消除冷启动问题

**工作流程**:
1. **冷启动阶段** (初期)
   - 使用 SCAN 算法提供立即可用的良好性能
   - 同时在后台训练 RL 代理
   - 持续监控两个算法的性能表现

2. **性能监控** (运行中)
   - 记录 SCAN 和 RL 的平均等待时间
   - 当 RL 性能达到阈值（默认 85% SCAN 性能）时触发切换
   - 需要最少样本数（默认 50 个乘客）以确保统计可靠

3. **智能切换** (自动)
   - 满足条件时自动从 SCAN 切换到 RL
   - 记录切换时刻和冷启动持续时间
   - 提供详细的切换日志

4. **自动回退** (可选)
   - 持续监控 RL 性能
   - 如果 RL 性能显著下降（> 120% SCAN），自动回退
   - 确保系统始终保持良好性能

**特性**:
- ✅ **零冷启动成本**: 初期使用成熟的 SCAN 算法
- ✅ **自适应学习**: RL 在后台持续学习优化
- ✅ **智能切换**: 基于性能指标自动决策
- ✅ **性能保障**: 自动回退机制防止性能下降
- ✅ **透明监控**: 详细的性能统计和切换日志

**适用场景**:
- 🎯 **生产环境首选**: 需要稳定性和适应性
- 🎯 长期运行的系统（RL 有足够时间学习）
- 🎯 流量模式可能变化的场景
- 🎯 无法接受冷启动性能下降的场景

**配置参数**:
```python
from algo import HybridScanRLAlgorithm

algorithm = HybridScanRLAlgorithm(
    training_mode=True,              # 是否训练 RL（False=仅使用已训练模型）
    switch_threshold=0.85,           # RL切换阈值（RL等待 <= 0.85 * SCAN等待）
    min_samples_before_switch=50,    # 切换前最少样本数
    enable_fallback=True,            # 是否启用自动回退
    model_path="models/hybrid_rl.pkl" # RL 模型保存路径
)

algorithm.start()

# 查看统计信息
algorithm.print_statistics()
```

**性能统计输出示例**:
```
============================================================
HYBRID ALGORITHM STATISTICS
============================================================
Active Algorithm: RL
Has Switched to RL: True
Switch Tick: 850
Cold Start Duration: 850 ticks

Passengers Handled:
  Total: 160
  By SCAN: 75 (46.9%)
  By RL: 85 (53.1%)

Performance:
  SCAN Average Wait: 122.5 ticks
  RL Average Wait: 98.3 ticks
  Performance Ratio (RL/SCAN): 0.80
============================================================
```

**与其他算法对比**:

| 特性 | OptimizedScan | RLDQNAlgorithm | HybridScanRL ⭐ |
|------|---------------|----------------|----------------|
| 启动性能 | ✅ 优秀 | ❌ 差（需训练） | ✅ 优秀 |
| 长期性能 | ⚠️ 固定 | ✅ 可优化 | ✅ 可优化 |
| 适应性 | ❌ 无 | ✅ 强 | ✅ 强 |
| 稳定性 | ✅ 高 | ⚠️ 中等 | ✅ 高（有回退） |
| 生产就绪 | ✅ 是 | ⚠️ 需训练 | ✅ 是 |
| 推荐指数 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### 扩展新算法

查看 [algo/README.md](algo/README.md) 了解如何添加自定义算法。

## 快速开始 🚀

**完全零基础？** 查看 [快速上手指南](快速上手指南.md)，10分钟从安装到测试一步到位！

### 环境要求

- Python >= 3.12
- uv (依赖管理工具)

### 安装

1. 安装uv（如果尚未安装）：
```bash
# macOS
brew install uv

# 或使用通用安装脚本
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. 同步项目依赖：
```bash
uv sync
```

3. 运行快速测试验证安装：
```bash
uv run python tests/auto_test.py --scenarios small_morning_rush
```

## 使用方法

### 方式一：Web 可视化界面（推荐）⭐⭐⭐

**图形化展示电梯调度过程，实时查看运行状态**：

```bash
# 启动 WebUI 服务器
uv run python -m webui.app
```

然后在浏览器中访问 http://localhost:8080

**WebUI 特性**：
- ✅ 实时可视化电梯运行状态
- ✅ Canvas 2D 渲染电梯、乘客和楼层
- ✅ 支持暂停、继续、停止操作
- ✅ 可调节模拟速度（0.1x - 5x）
- ✅ 实时统计信息展示（等待/运行中/已完成）
- ✅ 选择不同测试场景（10+ 预设场景）
- ✅ WebSocket 实时通信
- ✅ 页面加载时自动显示默认配置
- ✅ 左对齐可视化区域，优化布局
- ✅ 模拟结束后电梯自动归位到1层

**使用方式**：
1. 访问 http://localhost:8080，页面自动加载默认电梯配置
2. （可选）在左侧边栏选择测试场景（会立即更新可视化）
3. （可选）调整模拟速度（0.1x - 5x）
4. 点击"开始模拟"按钮
5. 在右侧Canvas区域观察电梯实时运行
6. 使用暂停/继续/停止按钮控制模拟
7. 查看左下方统计面板中的实时性能指标

**注意事项**：
- ⚠️ 当前使用 Mock 模拟引擎，采用简化的调度逻辑（最近电梯分配策略）
- ⚠️ 不运行真实的调度算法（OptimizedScan/RL/Hybrid）
- ⚠️ 性能数据仅供参考，不适用于算法对比研究
- ℹ️ 主要用于演示、UI开发和教学目的
- ℹ️ 如需运行真实算法并获得准确性能指标，请使用"方式二：CLI工具"或"方式三：手动启动"

### 方式二：使用 CLI 工具

**一键运行，无需手动启动服务器**：

```bash
# 查看所有可用算法
uv run python main.py list-algorithms

# 运行混合算法（默认，推荐）
uv run python main.py run

# 运行指定算法
uv run python main.py run --algorithm OptimizedScanAlgorithm

# 运行 RL 算法并启用训练
uv run python main.py run -a RLDQNAlgorithm --training

# 查看算法详细信息
uv run python main.py info HybridScanRLAlgorithm

# 查看帮助
uv run python main.py run --help
```

**CLI 特性**：
- ✅ 美观的表格输出（使用 Rich）
- ✅ 支持所有算法参数配置
- ✅ 详细的帮助文档
- ✅ 算法信息查询
- ✅ 错误处理和友好提示

### 方式三：手动启动（传统方式）

#### 1. 启动电梯模拟器服务

在一个终端窗口中运行：

```bash
uv run -m elevator server
```

服务将在 http://127.0.0.1:8000 启动。

#### 2. 运行电梯控制算法

在另一个终端窗口中运行：

```bash
# 使用 main.py（支持命令行参数）
uv run python main.py run

# 或使用 elevator_controller.py（需修改代码切换算法）
uv run python elevator_controller.py
```

## 流量配置

示例流量文件位于 `traffic/sample_traffic.json`，包含60个乘客的楼层间流量模式。

流量文件格式：
```json
{
  "building": {
    "floors": 6,
    "elevators": 2,
    "elevator_capacity": 8,
    "duration": 200
  },
  "traffic": [
    {
      "id": 1,
      "origin": 5,
      "destination": 1,
      "tick": 0
    }
  ]
}
```

## 算法说明

### 核心方法

- `on_passenger_call()`: 处理乘客呼叫，分配最优电梯
- `on_elevator_idle()`: 处理空闲电梯，分配到最近的等待乘客
- `on_elevator_approaching()`: 决定是否在即将到达的楼层停靠
- `on_passenger_board()`: 注册乘客目的地楼层
- `_find_best_elevator()`: 使用评分系统找到最佳电梯
- `_score_elevator()`: 为电梯分配评分（越低越好）

### 评分系统

电梯评分考虑以下因素：
- 距离：基础评分
- 负载：已载乘客数/容量 × 10
- 方向匹配：同向且会经过目标楼层，评分×0.5
- 方向冲突：反向移动，评分+20

## 批量测试

### 测试数据集

项目包含10个测试场景，涵盖不同建筑规模和流量模式：

**小型建筑 (6层)**
- `small_morning_rush.json` - 上班高峰 (160人) ★★★☆☆
- `small_evening_rush.json` - 下班高峰 (160人) ★★★☆☆
- `small_burst_traffic.json` - 突发流量 (73人) ★★☆☆☆

**中型建筑 (10层)**
- `medium_inter_floor.json` - 楼层间流量 (120人) ★★★☆☆
- `medium_lunch_rush.json` - 午餐高峰 (180人) ★★★★☆
- `medium_high_freq_burst.json` - 高频突发 (137人) ★★★★☆
- `medium_bottom_heavy.json` - 底层密集 (200人) ★★★★☆

**大型建筑 (15-25层)**
- `large_mixed.json` - 混合场景 (297人) ★★★★★
- `large_morning_rush.json` - 大规模上班高峰 (320人) ★★★★★
- `xlarge_stress_test.json` - 极限压力测试 (360人) ★★★★★

### 自动化测试（推荐）⭐

**🚀 完全自动化，一键测试所有场景**

自动化测试脚本会自动管理服务器生命周期，为每个测试提供完全隔离的环境，确保结果准确可靠。

#### 快速开始

```bash
# 完整测试 - 测试所有算法在所有场景下的表现
uv run python tests/auto_test.py

# 快速验证 - 只测试小型场景（5-10分钟）
uv run python tests/auto_test.py --scenarios small_morning_rush,small_evening_rush,small_burst_traffic

# 单算法测试 - 验证特定算法
uv run python tests/auto_test.py --algorithms OptimizedScanAlgorithm

# 组合筛选 - 灵活组合算法和场景
uv run python tests/auto_test.py \
    --algorithms OptimizedScanAlgorithm,RLDQNAlgorithm \
    --scenarios small_morning_rush,medium_inter_floor
```

#### 核心特性

| 特性 | 说明 |
|------|------|
| 🔄 自动服务器管理 | 自动启动/停止服务器，无需手动操作 |
| 🔒 完全隔离测试 | 每个测试独立服务器实例，确保无相互影响 |
| 📊 自动报告生成 | 生成 JSON 和 Markdown 格式的详细报告 |
| 🎯 灵活筛选 | 支持按算法、场景过滤，加速开发迭代 |
| ⚡ 健壮性保证 | 完善的错误处理、超时保护、自动清理 |

#### 输出内容

测试完成后自动生成：

1. **JSON 原始数据**: `test_results/auto_test_YYYYMMDD_HHMMSS.json`
   - 完整的性能指标
   - 场景信息
   - 测试状态

2. **Markdown 报告**: `docs/auto_test_report_YYYYMMDD_HHMMSS.md`
   - 算法性能对比表
   - 成功率统计
   - 可读性强，易于分享

#### 典型使用场景

```bash
# 场景1: 开发新算法，快速验证
uv run python tests/auto_test.py \
    --algorithms MyNewAlgorithm \
    --scenarios small_morning_rush

# 场景2: 提交前完整回归测试
uv run python tests/auto_test.py

# 场景3: 对比两个算法的表现
uv run python tests/auto_test.py \
    --algorithms OptimizedScanAlgorithm,RLDQNAlgorithm

# 场景4: 测试算法在极限场景下的表现
uv run python tests/auto_test.py \
    --scenarios large_mixed,xlarge_stress_test
```

#### 预计时间

| 测试范围 | 预计时间 | 推荐场景 |
|---------|---------|---------|
| 3个小型场景 | 5-10分钟 | 快速验证、开发迭代 |
| 所有场景（10个） | 20-40分钟 | 完整测试、提交前检查 |
| 单算法所有场景 | 10-20分钟 | 新算法验证 |

#### 进阶使用

**查看详细文档**:
- 📖 [完整指南](docs/automated_testing_guide.md) - 系统架构、技术细节、最佳实践
- 📘 [快速使用说明](docs/auto_test_usage.md) - 常见问题、故障排查、性能优化

**集成到 CI/CD**:

```yaml
# .github/workflows/test.yml
- name: Run automated tests
  run: |
    uv sync
    uv run python tests/auto_test.py
  timeout-minutes: 60
```

### 手动测试

如需手动控制测试过程：

1. **启动模拟器**（终端1）：
```bash
uv run python -m elevator_saga.server.simulator
```

2. **运行批量测试**（终端2）：
```bash
uv run python tests/run_tests.py
```

3. **按照提示操作**：
   - 查看每个场景信息
   - 运行控制器测试
   - 复制性能指标输出
   - 自动生成测试报告

### 测试报告

测试完成后会生成：
- `test_results/results_TIMESTAMP.json` - JSON格式原始数据
- `test_results/report_TIMESTAMP.md` - Markdown格式详细报告

报告内容包括：
- 总体统计（平均值、中位数）
- 详细结果表格
- 按场景类型分类分析
- 性能分析与改进建议
- 最佳/最差表现场景识别

### 生成自定义测试数据

```bash
# 编辑 tests/generate_test_data.py 添加场景
# 然后运行
uv run python tests/generate_test_data.py
```

### 性能指标说明

- **平均等待时间** (Average Wait Time) - 乘客从呼叫到上电梯的平均时间
- **P95等待时间** (P95 Wait Time) - 95%乘客的等待时间上限
- **平均系统时间** (Average System Time) - 从呼叫到到达目的地的平均时间
- **完成率** (Completion Rate) - 完成服务的乘客比例

### 性能基准参考

| 场景规模 | 优秀 | 良好 | 可接受 | 需改进 |
|---------|------|------|--------|--------|
| 小型（6层） | <80 | 80-120 | 120-180 | >180 |
| 中型（10层） | <100 | 100-150 | 150-220 | >220 |
| 大型（15-20层） | <140 | 140-200 | 200-280 | >280 |
| 超大（25层+） | <180 | 180-250 | 250-350 | >350 |

*单位: ticks (平均等待时间)*

## 详细文档

### 算法相关
- 📘 [Quick Start Guide](docs/quick_start_guide.md) - **快速开发指南**，15分钟添加自定义算法（推荐新手）
- 🔧 [Simulator API Reference](docs/simulator_api_reference.md) - **模拟器API完整参考**，所有可用数据和指标说明
- [算法扩展指南](algo/README.md) - 如何添加和实现自定义算法（详细版）
- [算法设计文档](docs/algorithm.md) - 详细的算法设计、评分系统、复杂度分析

### 测试相关
- 📖 [快速上手指南](快速上手指南.md) - **新手必读**，从安装到测试的完整流程
- 📘 [自动化测试快速使用](docs/auto_test_usage.md) - 使用方法、故障排查、性能优化、常见问题
- 📙 [自动化测试完整指南](docs/automated_testing_guide.md) - 系统架构、组件详解、配置定制、技术细节
- 📗 [测试指南](docs/testing_guide.md) - 手动测试使用说明、批量测试工具、最佳实践

## 参考文档

- [Elevator项目文档](https://zgca-forge.github.io/Elevator)
- [GitHub仓库](https://github.com/ZGCA-Forge/Elevator)
