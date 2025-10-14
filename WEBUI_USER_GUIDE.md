# 电梯调度系统 WebUI 使用指南

## 目录
- [快速开始](#快速开始)
- [WebUI 使用说明](#webui-使用说明)
- [如何添加新算法](#如何添加新算法)
- [如何添加新场景](#如何添加新场景)
- [项目架构说明](#项目架构说明)
- [常见问题](#常见问题)

---

## 快速开始

### 1. 启动 WebUI

```bash
# 方法一：使用启动脚本
./scripts/run_webui.sh

# 方法二：直接运行
uv run python -m webui.app
```

### 2. 访问界面

打开浏览器访问：http://localhost:8000

---

## WebUI 使用说明

### 界面布局

WebUI 分为三个主要区域：

#### 左侧控制面板
- **算法选择区**：选择要测试的调度算法
- **场景选择区**：选择测试场景
- **速度控制**：调整模拟速度（0.1x - 5.0x）
- **控制按钮**：开始、暂停、继续、停止
- **统计信息**：实时显示模拟数据

#### 右侧可视化区域
- 实时显示电梯运行状态
- 显示乘客等待和移动情况
- 动态更新楼层和电梯信息

### 基本操作流程

1. **选择算法**
   - 在"选择算法"下拉框中选择一个调度算法
   - 下方会显示算法的类型和描述

2. **选择场景**
   - 在"选择场景"下拉框中选择一个测试场景
   - 下方会显示场景的详细信息（楼层数、电梯数、乘客数等）

3. **调整速度**（可选）
   - 拖动速度滑块调整模拟速度
   - 速度范围：0.1x（慢速）到 5.0x（快速）
   - 默认速度：1.0x

4. **开始模拟**
   - 点击"开始模拟"按钮
   - 观察右侧可视化区域的实时动画
   - 查看左侧统计信息面板的实时数据

5. **控制模拟**
   - **暂停**：临时暂停模拟
   - **继续**：从暂停处继续运行
   - **停止**：完全停止模拟并重置

6. **查看结果**
   - 模拟完成后，统计信息会显示最终结果
   - 主要指标包括：
     - 总乘客数
     - 已完成数
     - 平均等待时间

---

## 如何添加新算法

### 步骤 1：实现算法类

在 `algo/` 目录下创建新的算法文件，例如 `my_algorithm.py`：

```python
from algo.base_algorithm import BaseAlgorithm

class MyAlgorithm(BaseAlgorithm):
    """
    我的自定义电梯调度算法
    """

    def __init__(self):
        super().__init__()
        # 初始化算法特定的状态

    def schedule(self, elevator_states, requests):
        """
        核心调度逻辑

        Args:
            elevator_states: 电梯状态列表
            requests: 当前请求列表

        Returns:
            dict: {elevator_id: decision} 每部电梯的决策
        """
        decisions = {}

        # 实现你的调度逻辑
        for elevator in elevator_states:
            # 为每部电梯做出决策
            decision = self._make_decision(elevator, requests)
            decisions[elevator['id']] = decision

        return decisions

    def _make_decision(self, elevator, requests):
        """实现具体的决策逻辑"""
        # 你的算法逻辑
        pass
```

### 步骤 2：注册算法

在 `algo/__init__.py` 中注册新算法：

```python
from .my_algorithm import MyAlgorithm

__all__ = [
    "OptimizedScanAlgorithm",
    "RLDQNAlgorithm",
    "HybridScanRLAlgorithm",
    "ScanController",
    "MyAlgorithm",  # 添加你的算法
]
```

### 步骤 3：添加算法元数据

在 `webui/models/algorithm.py` 中添加算法信息：

```python
class AlgorithmRepository:
    ALGORITHM_METADATA: Dict[str, AlgorithmInfo] = {
        # ... 现有算法 ...

        "MyAlgorithm": AlgorithmInfo(
            name="MyAlgorithm",
            display_name="我的算法",
            description="这是我的自定义电梯调度算法",
            type="Heuristic"  # 或 "Machine Learning" 或 "Hybrid"
        ),
    }
```

### 步骤 4：测试算法

1. 重启 WebUI 服务器
2. 刷新浏览器页面
3. 在算法选择框中应该能看到新添加的算法
4. 选择一个测试场景，点击"开始模拟"进行测试

---

## 如何添加新场景

### 场景文件格式

场景文件是 JSON 格式，保存在 `data/` 目录下。

### 步骤 1：创建场景文件

在 `data/` 目录下创建新的 JSON 文件，例如 `custom_scenario.json`：

```json
{
  "building": {
    "floors": 10,
    "elevators": 3,
    "elevator_capacity": 8,
    "scenario": "custom",
    "scale": "medium",
    "description": "自定义测试场景 - 10层楼，3部电梯",
    "expected_passengers": 50,
    "duration": 300
  },
  "traffic": [
    {
      "id": 1,
      "origin": 0,
      "destination": 5,
      "tick": 0
    },
    {
      "id": 2,
      "origin": 0,
      "destination": 8,
      "tick": 5
    },
    {
      "id": 3,
      "origin": 3,
      "destination": 7,
      "tick": 10
    }
  ]
}
```

### 场景文件字段说明

#### building 对象（建筑配置）
- `floors` (int)：楼层数（包括底层，从 0 开始计数）
- `elevators` (int)：电梯数量
- `elevator_capacity` (int)：每部电梯的容量（默认 8 人）
- `scenario` (string)：场景类型（如 "morning_rush", "lunch_rush", "mixed" 等）
- `scale` (string)：规模（"small", "medium", "large", "xlarge"）
- `description` (string)：场景描述（会显示在 WebUI 中）
- `expected_passengers` (int)：预期乘客数量
- `duration` (int)：模拟持续时间（时间步数）

#### traffic 数组（乘客请求）
每个乘客请求包含：
- `id` (int)：乘客唯一标识符
- `origin` (int)：出发楼层（0 表示底层）
- `destination` (int)：目标楼层
- `tick` (int)：出现时间（时间步）

### 场景设计建议

#### 1. 常见场景类型

**上班高峰（Morning Rush）**
```json
{
  "building": {
    "scenario": "morning_rush",
    "description": "上班高峰 - 大量乘客从底层上楼"
  },
  "traffic": [
    // 大部分请求 origin=0, destination 为各个楼层
  ]
}
```

**午餐高峰（Lunch Rush）**
```json
{
  "building": {
    "scenario": "lunch_rush",
    "description": "午餐高峰 - 乘客往返底层"
  },
  "traffic": [
    // 前半段：各楼层 -> 底层
    // 后半段：底层 -> 各楼层
  ]
}
```

**楼层间移动（Inter-floor）**
```json
{
  "building": {
    "scenario": "inter_floor",
    "description": "楼层间移动 - 随机楼层之间的移动"
  },
  "traffic": [
    // origin 和 destination 都是随机楼层（非底层）
  ]
}
```

**混合场景（Mixed）**
```json
{
  "building": {
    "scenario": "mixed",
    "description": "混合场景 - 各种移动模式的组合"
  },
  "traffic": [
    // 各种类型的请求混合
  ]
}
```

#### 2. 规模建议

- **small**：6-10 层，2 部电梯，50-200 人
- **medium**：10-20 层，3-4 部电梯，200-500 人
- **large**：20-30 层，4-6 部电梯，500-1000 人
- **xlarge**：30+ 层，6+ 部电梯，1000+ 人

#### 3. 时间设计

- **duration**：应该足够长以完成所有乘客请求
  - 经验公式：`duration = passengers * 2 + 100`

- **tick 分布**：
  - 突发流量：在短时间内大量请求（如 tick 0-50）
  - 均匀流量：请求均匀分布在整个时间段
  - 周期性流量：特定时间段出现流量高峰

### 步骤 2：验证场景文件

创建场景文件后，可以使用 Python 验证格式：

```python
import json
from pathlib import Path

# 加载场景文件
with open('data/custom_scenario.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 验证必需字段
assert 'building' in data
assert 'traffic' in data
assert 'floors' in data['building']
assert 'elevators' in data['building']

print(f"场景验证通过！")
print(f"楼层数: {data['building']['floors']}")
print(f"电梯数: {data['building']['elevators']}")
print(f"乘客数: {len(data['traffic'])}")
```

### 步骤 3：测试场景

1. 将场景文件保存到 `data/` 目录
2. 重启 WebUI 服务器
3. 刷新浏览器页面
4. 在场景选择框中应该能看到新添加的场景
5. 选择一个算法，点击"开始模拟"进行测试

### 示例：创建渐进式测试场景

```json
{
  "building": {
    "floors": 8,
    "elevators": 2,
    "elevator_capacity": 8,
    "scenario": "progressive_test",
    "scale": "small",
    "description": "渐进式测试 - 逐步增加负载",
    "expected_passengers": 100,
    "duration": 500
  },
  "traffic": [
    // 第一阶段：轻负载 (tick 0-100)
    {"id": 1, "origin": 0, "destination": 5, "tick": 10},
    {"id": 2, "origin": 0, "destination": 3, "tick": 20},

    // 第二阶段：中等负载 (tick 100-200)
    {"id": 21, "origin": 0, "destination": 7, "tick": 110},
    {"id": 22, "origin": 0, "destination": 4, "tick": 112},
    {"id": 23, "origin": 0, "destination": 6, "tick": 115},

    // 第三阶段：高负载 (tick 200-300)
    {"id": 51, "origin": 0, "destination": 2, "tick": 210},
    {"id": 52, "origin": 0, "destination": 5, "tick": 211},
    {"id": 53, "origin": 0, "destination": 7, "tick": 212},
    {"id": 54, "origin": 0, "destination": 3, "tick": 213},
    {"id": 55, "origin": 0, "destination": 6, "tick": 214}
  ]
}
```

---

## 项目架构说明

### 目录结构

```
elevator_controller/
├── algo/                      # 算法实现
│   ├── __init__.py           # 算法注册
│   ├── base_algorithm.py     # 算法基类
│   ├── optimized_scan.py     # 优化 SCAN 算法
│   ├── rl_dqn.py             # 强化学习算法
│   └── hybrid_scan_rl.py     # 混合算法
│
├── data/                      # 场景数据
│   ├── small_*.json          # 小型场景
│   ├── medium_*.json         # 中型场景
│   ├── large_*.json          # 大型场景
│   └── xlarge_*.json         # 超大型场景
│
├── webui/                     # Web 界面（MVC 架构）
│   ├── app.py                # 应用入口
│   │
│   ├── models/               # 数据模型层
│   │   ├── algorithm.py      # 算法数据模型
│   │   └── scenario.py       # 场景数据模型
│   │
│   ├── services/             # 业务逻辑层
│   │   ├── algorithm_service.py
│   │   ├── scenario_service.py
│   │   └── simulation_service.py
│   │
│   ├── controllers/          # 控制器层
│   │   ├── algorithm_controller.py
│   │   ├── scenario_controller.py
│   │   └── simulation_controller.py
│   │
│   ├── static/               # 前端资源
│   │   ├── css/
│   │   │   └── style.css
│   │   ├── js/
│   │   │   ├── models/       # 前端数据模型
│   │   │   │   ├── AlgorithmModel.js
│   │   │   │   └── ScenarioModel.js
│   │   │   ├── views/        # 前端视图
│   │   │   │   ├── ControlPanelView.js
│   │   │   │   └── VisualizationView.js
│   │   │   ├── controllers/  # 前端控制器
│   │   │   │   └── SimulationController.js
│   │   │   ├── websocket.js  # WebSocket 管理
│   │   │   ├── renderer.js   # Canvas 渲染
│   │   │   └── app.js        # 应用入口
│   │   └── index.html
│   │
│   ├── real_simulation.py    # 真实模拟引擎
│   └── mock_simulation.py    # 模拟引擎（用于测试）
│
├── simulator.py              # 核心模拟器
├── elevator_controller.py    # 电梯控制器
└── scripts/
    └── run_webui.sh          # 启动脚本
```

### MVC 架构说明

#### 后端 MVC

1. **Model（模型层）**
   - `webui/models/algorithm.py`：算法数据和访问逻辑
   - `webui/models/scenario.py`：场景数据和文件加载

2. **Service（业务逻辑层）**
   - `webui/services/algorithm_service.py`：算法业务逻辑
   - `webui/services/scenario_service.py`：场景业务逻辑
   - `webui/services/simulation_service.py`：模拟引擎管理

3. **Controller（控制器层）**
   - `webui/controllers/algorithm_controller.py`：处理算法 API 请求
   - `webui/controllers/scenario_controller.py`：处理场景 API 请求
   - `webui/controllers/simulation_controller.py`：处理 WebSocket 连接

#### 前端 MVC

1. **Model（模型层）**
   - `AlgorithmModel.js`：管理算法数据
   - `ScenarioModel.js`：管理场景数据

2. **View（视图层）**
   - `ControlPanelView.js`：控制面板 UI
   - `VisualizationView.js`：可视化显示

3. **Controller（控制器层）**
   - `SimulationController.js`：协调 Model 和 View，处理用户交互

### API 接口

#### HTTP 接口

- `GET /api/algorithms`：获取所有可用算法
  ```json
  {
    "algorithms": [
      {
        "name": "OptimizedScanAlgorithm",
        "display_name": "Optimized SCAN",
        "description": "优化SCAN算法",
        "type": "Heuristic"
      }
    ]
  }
  ```

- `GET /api/scenarios`：获取所有可用场景
  ```json
  {
    "scenarios": [
      {
        "name": "small_morning_rush",
        "display_name": "小型建筑上班高峰",
        "floors": 6,
        "elevators": 2,
        "passengers": 160,
        "duration": 200,
        "capacity": 8,
        "scale": "small",
        "type": "morning_rush"
      }
    ]
  }
  ```

#### WebSocket 接口

连接：`ws://localhost:8000/ws/simulation`

**客户端 -> 服务器消息**

1. 开始模拟
```json
{
  "type": "start",
  "algorithm": "OptimizedScanAlgorithm",
  "scenario": "small_morning_rush",
  "speed": 1.0
}
```

2. 暂停模拟
```json
{
  "type": "pause"
}
```

3. 继续模拟
```json
{
  "type": "resume"
}
```

4. 停止模拟
```json
{
  "type": "stop"
}
```

5. 设置速度
```json
{
  "type": "set_speed",
  "speed": 2.0
}
```

**服务器 -> 客户端消息**

1. 初始化消息
```json
{
  "type": "init",
  "algorithm": "OptimizedScanAlgorithm",
  "scenario": "small_morning_rush",
  "building": {
    "floors": 6,
    "elevators": 2,
    "capacity": 8
  }
}
```

2. 状态更新
```json
{
  "type": "state_update",
  "tick": 42,
  "elevators": [
    {
      "id": 0,
      "floor": 3.5,
      "direction": "UP",
      "passengers": [1, 3, 5],
      "target_floor": 5
    }
  ],
  "waiting_passengers": {
    "0": [2, 4, 6],
    "3": [7]
  },
  "stats": {
    "total_passengers": 160,
    "waiting": 4,
    "in_elevator": 3,
    "completed": 153,
    "avg_wait_time": 12.5
  }
}
```

3. 完成消息
```json
{
  "type": "complete",
  "tick": 200,
  "stats": {
    "total_passengers": 160,
    "completed": 160,
    "avg_wait_time": 11.8
  }
}
```

4. 错误消息
```json
{
  "type": "error",
  "message": "算法不存在"
}
```

---

## 常见问题

### Q1: WebUI 无法启动，提示端口被占用

**A:** 8000 端口已被其他程序占用，可以：
- 关闭占用端口的程序
- 或修改 `webui/app.py` 中的端口号

### Q2: 添加了新算法，但在 WebUI 中看不到

**A:** 检查以下几点：
1. 算法是否在 `algo/__init__.py` 中注册
2. 算法元数据是否添加到 `webui/models/algorithm.py`
3. 是否重启了 WebUI 服务器
4. 浏览器是否刷新了页面

### Q3: 添加了新场景，但在 WebUI 中看不到

**A:** 检查以下几点：
1. JSON 文件格式是否正确
2. 文件是否保存在 `data/` 目录下
3. 文件扩展名是否为 `.json`
4. 是否重启了 WebUI 服务器
5. 浏览器是否刷新了页面

### Q4: 模拟运行很慢，如何加快速度？

**A:**
- 使用速度滑块调整到 2.0x - 5.0x
- 选择规模较小的场景进行测试
- 确保浏览器性能良好

### Q5: 如何保存模拟结果？

**A:** 目前 WebUI 不支持自动保存结果，可以：
- 手动记录统计信息面板的数据
- 使用浏览器的截图功能保存可视化结果
- 或扩展代码添加数据导出功能

### Q6: 可以同时运行多个模拟吗？

**A:** 不可以。当前架构一次只支持一个模拟运行。如需运行多个模拟，请：
- 等待当前模拟完成后再开始新的模拟
- 或在不同的终端和端口启动多个 WebUI 实例

### Q7: 如何调试自己的算法？

**A:**
1. 在算法代码中添加 `print()` 语句
2. 查看终端输出（运行 WebUI 的终端）
3. 使用 Python 调试器（pdb 或 IDE 调试功能）
4. 选择小型场景进行测试，便于观察

### Q8: 场景文件中的 tick 是什么单位？

**A:** tick 是模拟器的时间步单位，不代表实际时间。每个 tick：
- 电梯可以移动一定距离（取决于速度设置）
- 可以开关门、上下乘客
- 是模拟器最小的时间单位

### Q9: 如何创建高峰时段的场景？

**A:**
- 在短时间内（如 tick 0-50）创建大量请求
- 让大部分请求的 origin 或 destination 相同
- 例如上班高峰：origin=0, destination=随机楼层

### Q10: 电梯容量可以超过 8 人吗？

**A:** 可以。在场景文件的 `building.elevator_capacity` 中设置任意值。常见值：
- 小型电梯：6-8 人
- 标准电梯：8-13 人
- 大型电梯：15-20 人

---

## 技术支持

如有问题或建议，请：
- 查看项目文档和代码注释
- 检查终端输出的错误信息
- 提交 Issue 到项目仓库

---

## 更新日志

### v2.0 (2024)
- 完整 MVC 架构重构
- 前后端分离
- 实时 WebSocket 通信
- 响应式可视化界面

### v1.0 (2024)
- 初始版本
- 基础算法实现
- 简单的 Web 界面
