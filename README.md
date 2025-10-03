# Elevator Scheduling Algorithm

优化的电梯调度算法，旨在最小化乘客等待时间的平均值和P95。

## 项目结构

```
elevator_homework/
├── elevator_controller.py    # 主入口程序
├── algo/                     # 算法实现目录
│   ├── __init__.py          # 包初始化
│   ├── base_algorithm.py    # 算法基类
│   ├── optimized_scan.py    # 优化SCAN算法（默认）
│   └── README.md            # 算法扩展指南
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
│   ├── algorithm.md         # 算法设计文档
│   └── testing_guide.md     # 测试指南
├── test_results/            # 测试报告输出目录
├── pyproject.toml           # uv项目配置
└── README.md                # 本文件
```

## 算法架构

本项目采用模块化设计，算法实现位于 `algo/` 目录：

- **BaseAlgorithm**: 抽象基类，定义统一接口
- **OptimizedScanAlgorithm**: 默认算法实现（优化SCAN）
- **RLDQNAlgorithm**: 强化学习Q-learning算法

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

### 1. 启动电梯模拟器服务

在一个终端窗口中运行：

```bash
uv run python -m elevator_saga.server.simulator
```

服务将在 http://127.0.0.1:8000 启动。

### 2. 运行电梯控制算法

在另一个终端窗口中运行：

```bash
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
- [算法扩展指南](algo/README.md) - 如何添加和实现自定义算法
- [算法设计文档](docs/algorithm.md) - 详细的算法设计、评分系统、复杂度分析

### 测试相关
- 📖 [快速上手指南](快速上手指南.md) - **新手必读**，从安装到测试的完整流程
- 📘 [自动化测试快速使用](docs/auto_test_usage.md) - 使用方法、故障排查、性能优化、常见问题
- 📙 [自动化测试完整指南](docs/automated_testing_guide.md) - 系统架构、组件详解、配置定制、技术细节
- 📗 [测试指南](docs/testing_guide.md) - 手动测试使用说明、批量测试工具、最佳实践

## 参考文档

- [Elevator项目文档](https://zgca-forge.github.io/Elevator)
- [GitHub仓库](https://github.com/ZGCA-Forge/Elevator)
