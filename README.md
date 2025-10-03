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

### 当前算法特性

OptimizedScanAlgorithm 实现了以下优化策略：

1. **SCAN算法**：电梯持续向一个方向移动，直到该方向没有更多请求
2. **最近邻分配**：为空闲电梯分配最近的等待乘客
3. **负载均衡**：在多个电梯之间智能分配任务
4. **智能评分系统**：
   - 优先选择已经朝着目标方向移动的电梯
   - 优先选择距离更近的电梯
   - 优先选择负载较轻的电梯

### 扩展新算法

查看 [algo/README.md](algo/README.md) 了解如何添加自定义算法。

## 环境要求

- Python >= 3.12
- uv (依赖管理工具)

## 安装

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

### 快速开始测试

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

- [算法扩展指南](algo/README.md) - 如何添加和实现自定义算法
- [算法设计文档](docs/algorithm.md) - 详细的算法设计、评分系统、复杂度分析
- [测试指南](docs/testing_guide.md) - 完整的测试使用说明、故障排除、最佳实践

## 参考文档

- [Elevator项目文档](https://zgca-forge.github.io/Elevator)
- [GitHub仓库](https://github.com/ZGCA-Forge/Elevator)
