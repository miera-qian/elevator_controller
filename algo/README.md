# Elevator Scheduling Algorithms

本目录包含各种电梯调度算法的实现。所有算法都继承自 `BaseAlgorithm` 基类，提供统一的接口。

## 目录结构

```
algo/
├── __init__.py              # 包初始化，导出可用算法
├── base_algorithm.py        # 抽象基类
├── optimized_scan.py        # 优化的SCAN算法（默认）
└── README.md               # 本文件
```

## 已实现的算法

### 1. OptimizedScanAlgorithm (优化SCAN算法)

**文件**: `optimized_scan.py`

**特性**:
- SCAN算法：电梯持续向一个方向移动直到无更多请求
- 智能评分系统：综合考虑距离、负载、方向匹配度
- 最近邻策略：空闲电梯前往最近的等待乘客
- 负载均衡：避免单部电梯过载

**适用场景**:
- 中小型建筑（6-20层）
- 混合流量模式
- 通用场景

**性能**:
- 平均等待时间：良好
- P95等待时间：优秀
- 吞吐量：高

---

## 如何添加新算法

### 步骤1: 创建算法文件

在 `algo/` 目录下创建新文件，例如 `my_algorithm.py`:

```python
#!/usr/bin/env python3
"""
My Custom Algorithm

Description of your algorithm here.
"""

from typing import List
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from .base_algorithm import BaseAlgorithm


class MyCustomAlgorithm(BaseAlgorithm):
    """
    Your algorithm description.
    """

    def __init__(self, server_url: str = "http://127.0.0.1:8000", enable_logging: bool = True):
        super().__init__(server_url, enable_logging)
        # Add custom state variables here

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """Handle new passenger call"""
        # Your implementation
        pass

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """Handle idle elevator"""
        # Your implementation
        pass

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """Decide whether to stop at approaching floor"""
        # Your implementation
        pass

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """Handle elevator stopped"""
        # Your implementation
        pass

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """Handle passenger boarding"""
        # Your implementation
        pass
```

### 步骤2: 导出算法

在 `algo/__init__.py` 中添加导出:

```python
from .optimized_scan import OptimizedScanAlgorithm
from .my_algorithm import MyCustomAlgorithm  # 新增

__all__ = ['OptimizedScanAlgorithm', 'MyCustomAlgorithm']  # 新增
```

### 步骤3: 使用新算法

在 `elevator_controller.py` 中切换算法:

```python
from algo import MyCustomAlgorithm

if __name__ == "__main__":
    algorithm = MyCustomAlgorithm()  # 使用新算法
    algorithm.start()
```

---

## 基类说明

### BaseAlgorithm

所有算法都必须继承 `BaseAlgorithm` 类。

**提供的基础设施**:

```python
# 等待乘客追踪
self.waiting_up: Dict[int, Set[int]]      # 每层等待上行的乘客ID
self.waiting_down: Dict[int, Set[int]]    # 每层等待下行的乘客ID

# 电梯目标追踪
self.elevator_targets: Dict[int, List[int]]  # 每部电梯的目标楼层列表

# 系统状态
self.elevators: List[ProxyElevator]       # 所有电梯
self.floors: List[ProxyFloor]             # 所有楼层
self.num_floors: int                      # 楼层数
self.num_elevators: int                   # 电梯数
```

**必须实现的方法**:

1. `on_passenger_call()` - 处理新的乘客呼叫
2. `on_elevator_idle()` - 处理空闲电梯
3. `on_elevator_approaching()` - 决定是否在即将到达的楼层停靠
4. `on_elevator_stopped()` - 处理电梯停靠
5. `on_passenger_board()` - 处理乘客上车

**可选实现的方法**:

- `on_init()` - 初始化（可override扩展）
- `on_event_execute_start()` - 事件执行开始
- `on_event_execute_end()` - 事件执行结束
- `on_elevator_passing_floor()` - 电梯经过楼层
- `on_passenger_alight()` - 乘客下车

---

## 算法设计建议

### 1. 关键性能指标

- **平均等待时间**: 主要优化目标
- **P95等待时间**: 避免极端等待
- **完成率**: 应始终100%
- **能耗**: 减少空驶和换向

### 2. 常见策略

#### FCFS (First Come First Serve)
- 最简单
- 公平性好
- 效率一般

#### SCAN / LOOK
- 减少换向
- 效率高
- 可能有饥饿问题

#### Shortest Seek Time First (SSTF)
- 优先服务最近请求
- 效率高
- 可能有饥饿问题

#### Elevator Algorithm with Zones
- 将建筑分区
- 电梯负责特定区域
- 适合大型建筑

### 3. 优化技巧

#### 智能评分系统
- 综合多个因素
- 距离、负载、方向等
- 权重可调

#### 预测与学习
- 学习历史流量模式
- 预测未来请求
- 前瞻性部署电梯

#### 场景识别
- 识别上下班高峰
- 午餐时段等
- 针对性策略

#### 负载均衡
- 避免某部电梯过载
- 提高系统吞吐量
- 减少平均等待

---

## 测试新算法

### 1. 单场景测试

```bash
# 启动模拟器
uv run python -m elevator_saga.server.simulator

# 运行算法
uv run python elevator_controller.py
```

### 2. 批量测试

```bash
# 使用测试工具
uv run python tests/run_tests.py
```

### 3. 性能对比

创建多个算法实例，在相同场景下测试：

```python
# 对比测试示例
from algo import OptimizedScanAlgorithm, MyCustomAlgorithm

algorithms = [
    OptimizedScanAlgorithm(),
    MyCustomAlgorithm(),
]

for algo in algorithms:
    print(f"Testing {algo.__class__.__name__}...")
    # 运行测试
    # 记录结果
```

---

## 算法示例

### 示例1: 简单FCFS算法

```python
class SimpleFCFSAlgorithm(BaseAlgorithm):
    """First Come First Serve - 最简单的调度算法"""

    def __init__(self, server_url: str = "http://127.0.0.1:8000", enable_logging: bool = True):
        super().__init__(server_url, enable_logging)
        self.request_queue = []  # 请求队列

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        floor_num = floor.floor
        self.request_queue.append((floor_num, direction))

        # 分配第一部空闲电梯
        for elevator in self.elevators:
            if elevator.is_idle:
                elevator.go_to_floor(floor_num)
                break

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        # 处理队列中的下一个请求
        if self.request_queue:
            floor_num, _ = self.request_queue.pop(0)
            elevator.go_to_floor(floor_num)

    # ... 实现其他必需方法
```

### 示例2: 基于区域的算法

```python
class ZoneBasedAlgorithm(BaseAlgorithm):
    """将建筑分区，电梯负责特定区域"""

    def __init__(self, server_url: str = "http://127.0.0.1:8000", enable_logging: bool = True):
        super().__init__(server_url, enable_logging)
        self.zones = {}  # elevator_id -> (floor_min, floor_max)

    def on_init(self, elevators, floors):
        super().on_init(elevators, floors)

        # 分配区域
        floors_per_zone = self.num_floors // self.num_elevators
        for i, elevator in enumerate(elevators):
            floor_min = i * floors_per_zone
            floor_max = floor_min + floors_per_zone - 1
            if i == len(elevators) - 1:  # 最后一部电梯覆盖剩余楼层
                floor_max = self.num_floors - 1
            self.zones[elevator.id] = (floor_min, floor_max)

    def on_passenger_call(self, passenger, floor, direction):
        floor_num = floor.floor

        # 找到负责该楼层的电梯
        for elevator in self.elevators:
            floor_min, floor_max = self.zones[elevator.id]
            if floor_min <= floor_num <= floor_max:
                elevator.go_to_floor(floor_num)
                break

    # ... 实现其他必需方法
```

---

## 调试技巧

### 1. 启用日志

```python
algorithm = MyCustomAlgorithm(enable_logging=True)
```

### 2. 添加调试输出

```python
def on_passenger_call(self, passenger, floor, direction):
    print(f"[DEBUG] Passenger {passenger.id} called at floor {floor.floor} going {direction}")
    # Your implementation
```

### 3. 状态检查

```python
def _print_state(self):
    """打印当前状态"""
    print(f"Waiting up: {self.waiting_up}")
    print(f"Waiting down: {self.waiting_down}")
    for elevator in self.elevators:
        print(f"Elevator {elevator.id}: Floor {elevator.current_floor}, "
              f"Direction {elevator.last_tick_direction}, Load {elevator.load_factor}")
```

---

## 参考资源

### 经典算法论文
- SCAN Algorithm (Elevator Algorithm)
- LOOK Algorithm
- C-SCAN (Circular SCAN)

### 相关项目
- [elevator-py框架文档](https://zgca-forge.github.io/Elevator)
- [算法设计文档](../docs/algorithm.md)

---

## 贡献指南

欢迎贡献新的算法实现！

1. Fork 项目
2. 创建新算法文件
3. 实现并测试算法
4. 更新本README
5. 提交Pull Request

### 算法命名规范

- 文件名：小写下划线分隔，如 `my_algorithm.py`
- 类名：大驼峰，如 `MyCustomAlgorithm`
- 应包含清晰的文档字符串

### 代码质量要求

- 遵循PEP 8规范
- 添加类型注解
- 编写文档字符串
- 实现所有必需方法
- 通过基本测试场景
