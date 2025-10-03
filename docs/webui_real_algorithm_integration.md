# WebUI真实算法集成指南（方案B）

## 概述

本文档详细描述如何将WebUI与真实的电梯调度算法集成，使其能够运行OptimizedScanAlgorithm、RLDQNAlgorithm和HybridScanRLAlgorithm等真实算法，而不是使用Mock模拟数据。

## 当前状态

**已实现（方案C）**: MockSimulationEngine
- 提供预录制/生成的数据用于演示
- 不运行真实算法
- 适用于UI开发和演示

**待实现（方案B）**: RealSimulationEngine
- 运行真实的调度算法
- 使用elevator_saga内部API
- 提供真实的性能数据

## 架构分析

### elevator_saga包结构

```
elevator_saga/
├── core/
│   ├── models.py          # Elevator, Floor, Passenger数据模型
│   ├── simulation.py      # Simulation核心类
│   └── controller.py      # ElevatorController基类
├── server/
│   ├── simulator.py       # Flask服务器（不适合我们使用）
│   └── traffic.py         # Traffic数据加载工具
└── cli/
    └── main.py            # CLI工具
```

### 关键类和API

#### 1. Simulation类

```python
from elevator_saga.core.simulation import Simulation

# 创建模拟实例
simulation = Simulation(
    num_floors=10,
    num_elevators=3,
    elevator_capacity=8
)

# 添加traffic事件
simulation.add_passenger_call(
    floor=5,
    destination=1,
    tick=10
)

# 连接控制器
simulation.set_controller(algorithm_instance)

# 运行一个tick
simulation.tick()

# 获取当前状态
state = {
    "elevators": [
        {
            "floor": elev.current_floor,
            "passengers": elev.passengers,
            "target_floors": elev.target_floors
        }
        for elev in simulation.elevators
    ],
    "floors": {
        floor_num: {
            "waiting_passengers": floor.waiting_passengers
        }
        for floor_num, floor in simulation.floors.items()
    }
}
```

#### 2. ElevatorController基类

```python
from elevator_saga.core.controller import ElevatorController

class MyAlgorithm(ElevatorController):
    def on_init(self, elevators, floors):
        \"\"\"初始化时调用\"\"\"
        pass

    def on_passenger_call(self, floor_num, passenger):
        \"\"\"新乘客呼叫时调用\"\"\"
        # 返回分配的电梯ID
        return elevator_id

    def on_elevator_idle(self, elevator):
        \"\"\"电梯空闲时调用\"\"\"
        # 返回目标楼层
        return target_floor

    def on_elevator_approaching(self, elevator, floor_num):
        \"\"\"电梯接近楼层时调用\"\"\"
        # 返回是否停靠
        return should_stop
```

## 实现步骤

### Step 1: 研究elevator_saga内部API

**任务**: 深入理解Simulation类的工作原理

**方法**:
```python
# 创建测试脚本
import elevator_saga.core.simulation as sim
import elevator_saga.core.models as models

# 实验创建和运行simulation
s = sim.Simulation(num_floors=6, num_elevators=2, elevator_capacity=8)

# 查看可用方法
print(dir(s))

# 测试添加passenger
s.add_passenger_call(floor=1, destination=5, tick=0)

# 测试tick
s.tick()

# 检查状态
print(s.elevators[0].current_floor)
print(s.floors[1].waiting_passengers)
```

**关键问题需要回答**:
1. 如何从JSON场景加载traffic事件？
2. 如何在每个tick后提取完整状态？
3. 如何正确连接我们的算法实例？
4. Simulation类是否线程安全？

### Step 2: 创建RealSimulationEngine

**文件**: `webui/real_simulation.py`

```python
#!/usr/bin/env python3
\"\"\"
Real Simulation Engine - Runs actual scheduling algorithms using elevator_saga
\"\"\"

import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, List
from fastapi import WebSocket

# 导入elevator_saga内部API
from elevator_saga.core.simulation import Simulation
from elevator_saga.core.models import Passenger

import algo


class RealSimulationEngine:
    \"\"\"
    Real simulation engine that runs actual scheduling algorithms
    \"\"\"

    def __init__(
        self,
        algorithm_name: str,
        scenario_name: str,
        speed: float,
        websocket: WebSocket
    ):
        self.algorithm_name = algorithm_name
        self.scenario_name = scenario_name
        self.speed = speed
        self.websocket = websocket

        # State
        self.running = False
        self.paused = False
        self.current_tick = 0

        # Load scenario
        self.scenario_data = None
        self.building_config = None
        self.traffic_events = []
        self._load_scenario()

        # Simulation components
        self.simulation = None
        self.algorithm = None

    def _load_scenario(self):
        \"\"\"Load scenario from JSON file\"\"\"
        data_dir = Path(__file__).parent.parent / "data"
        scenario_file = data_dir / f"{self.scenario_name}.json"

        with open(scenario_file, 'r') as f:
            self.scenario_data = json.load(f)

        self.building_config = self.scenario_data.get("building", {})
        self.traffic_events = self.scenario_data.get("traffic", [])

    def _create_simulation(self):
        \"\"\"Create elevator_saga Simulation instance\"\"\"
        self.simulation = Simulation(
            num_floors=self.building_config.get("floors", 10),
            num_elevators=self.building_config.get("elevators", 3),
            elevator_capacity=self.building_config.get("capacity", 8)
        )

        # Pre-load all traffic events into simulation
        for event in self.traffic_events:
            self.simulation.add_passenger_call(
                floor=event.get("from_floor"),
                destination=event.get("to_floor"),
                tick=event.get("call_time")
            )

    def _create_algorithm(self):
        \"\"\"Create algorithm instance\"\"\"
        algorithm_class = getattr(algo, self.algorithm_name)

        # Note: Need to adapt our algorithms to work WITHOUT server_url
        # This requires modifying algo/base_algorithm.py
        self.algorithm = algorithm_class(
            enable_logging=False,
            # Don't pass server_url - we're using direct API
        )

        # Connect algorithm to simulation
        self.simulation.set_controller(self.algorithm)

    async def start(self):
        \"\"\"Start the real simulation\"\"\"
        self.running = True
        self.paused = False
        self.current_tick = 0

        # Send init state
        await self._send_init_state()

        # Create simulation and algorithm
        self._create_simulation()
        self._create_algorithm()

        # Run simulation loop
        await self._run_simulation()

    async def _send_init_state(self):
        \"\"\"Send initial configuration to client\"\"\"
        await self.websocket.send_json({
            "type": "init",
            "building": {
                "floors": self.building_config.get("floors"),
                "elevators": self.building_config.get("elevators"),
                "capacity": self.building_config.get("capacity"),
                "description": self.building_config.get("description", ""),
                "duration": self.building_config.get("duration")
            },
            "algorithm": self.algorithm_name,
            "scenario": self.scenario_name
        })

    async def _run_simulation(self):
        \"\"\"Main simulation loop\"\"\"
        max_duration = self.building_config.get("duration", 300)

        while self.running and self.current_tick < max_duration:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            # Run one simulation tick
            self.simulation.tick()

            # Extract and send state
            await self._send_state_update()

            self.current_tick += 1

            # Sleep based on speed
            await asyncio.sleep(0.1 / self.speed)

        # Send completion
        await self._send_completion()

    async def _send_state_update(self):
        \"\"\"Extract state from simulation and send to client\"\"\"
        # Extract elevator states
        elevators_state = []
        for i, elevator in enumerate(self.simulation.elevators):
            # Determine direction based on target floors
            direction = "idle"
            if elevator.target_floors:
                next_target = elevator.target_floors[0]
                if next_target > elevator.current_floor:
                    direction = "up"
                elif next_target < elevator.current_floor:
                    direction = "down"

            elevators_state.append({
                "id": i,
                "floor": elevator.current_floor,
                "direction": direction,
                "passengers": [
                    {
                        "id": p.id,
                        "from_floor": p.origin_floor,
                        "to_floor": p.destination_floor
                    }
                    for p in elevator.passengers
                ],
                "capacity": elevator.capacity
            })

        # Extract waiting passengers
        waiting_by_floor = {}
        for floor_num, floor in self.simulation.floors.items():
            waiting_by_floor[str(floor_num)] = [
                {
                    "id": p.id,
                    "from_floor": p.origin_floor,
                    "to_floor": p.destination_floor,
                    "call_time": p.call_time
                }
                for p in floor.waiting_passengers
            ]

        # Calculate statistics
        total_waiting = sum(len(floor.waiting_passengers)
                           for floor in self.simulation.floors.values())
        total_in_elevator = sum(len(e.passengers)
                               for e in self.simulation.elevators)

        state = {
            "type": "state_update",
            "tick": self.current_tick,
            "elevators": elevators_state,
            "waiting": waiting_by_floor,
            "stats": {
                "total_passengers": len(self.traffic_events),
                "waiting": total_waiting,
                "in_elevator": total_in_elevator,
                "completed": 0,  # Would need to track this
                "avg_wait_time": 0.0  # Would need to calculate
            }
        }

        await self.websocket.send_json(state)

    async def _send_completion(self):
        \"\"\"Send completion message\"\"\"
        await self.websocket.send_json({
            "type": "complete",
            "tick": self.current_tick,
            "stats": {
                "total_passengers": len(self.traffic_events),
                "avg_wait_time": 0.0  # Calculate from simulation
            }
        })

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        self.running = False

    def set_speed(self, speed: float):
        self.speed = max(0.1, min(10.0, speed))
```

### Step 3: 修改算法基类

**问题**: 当前算法依赖server_url参数连接到HTTP服务器

**解决**: 创建适配器模式，支持两种模式：
1. Server模式（当前）- 通过HTTP/WebSocket连接
2. Direct模式（新增）- 直接API调用

**文件**: `algo/base_algorithm.py`

```python
class BaseAlgorithm(ElevatorController, ABC):
    def __init__(self, server_url=None, enable_logging=True, direct_mode=False):
        \"\"\"
        Args:
            server_url: HTTP server URL (for server mode)
            enable_logging: Enable logging
            direct_mode: Use direct API instead of server (for WebUI)
        \"\"\"
        self.server_url = server_url
        self.enable_logging = enable_logging
        self.direct_mode = direct_mode

        if direct_mode:
            # Direct mode - simulation will call our methods
            pass
        else:
            # Server mode - we connect to HTTP server
            super().__init__(server_url=server_url)

    def start(self):
        if self.direct_mode:
            # In direct mode, don't start - simulation will drive us
            pass
        else:
            # Server mode - connect and run
            super().start()
```

### Step 4: 测试集成

**创建测试脚本**: `webui/test_real_simulation.py`

```python
#!/usr/bin/env python3
import asyncio
from mock import Mock
from real_simulation import RealSimulationEngine

async def test():
    # Mock WebSocket
    websocket = Mock()
    messages = []

    async def send_json(msg):
        messages.append(msg)
        print(f"Sent: {msg['type']}")

    websocket.send_json = send_json

    # Create engine
    engine = RealSimulationEngine(
        algorithm_name="OptimizedScanAlgorithm",
        scenario_name="small_morning_rush",
        speed=10.0,  # Fast for testing
        websocket=websocket
    )

    # Run
    await engine.start()

    # Check results
    print(f"Total messages: {len(messages)}")
    print(f"Ticks simulated: {engine.current_tick}")

if __name__ == "__main__":
    asyncio.run(test())
```

### Step 5: 集成到WebUI

**修改**: `webui/app.py`

```python
# Add configuration option
USE_REAL_SIMULATION = False  # Set to True when ready

@app.websocket("/ws/simulation")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    if USE_REAL_SIMULATION:
        from .real_simulation import RealSimulationEngine
        EngineClass = RealSimulationEngine
    else:
        from .mock_simulation import MockSimulationEngine
        EngineClass = MockSimulationEngine

    engine = None

    while True:
        message = await websocket.receive_json()

        if message.get("type") == "start":
            engine = EngineClass(...)
            await engine.start()
        # ... rest of handlers
```

## 挑战和解决方案

### 挑战1: elevator_saga API未文档化

**解决**:
- 阅读源代码 (`elevator_saga/core/`)
- 创建小型测试脚本实验
- 查看CLI工具如何使用API

### 挑战2: 算法设计为服务器模式

**解决**:
- 添加`direct_mode`参数
- 在direct模式下跳过HTTP连接
- 让Simulation直接调用算法的回调方法

### 挑战3: 状态提取

**解决**:
- 遍历`simulation.elevators`列表
- 遍历`simulation.floors`字典
- 提取所有相关属性

### 挑战4: 性能统计

**解决**:
- 在RealSimulationEngine中跟踪passenger lifecycle
- 记录call_time, pickup_time, dropoff_time
- 计算等待时间分布

## 预期工作量

- **研究elevator_saga API**: 4-6小时
- **实现RealSimulationEngine**: 6-8小时
- **修改算法基类**: 2-4小时
- **测试和调试**: 4-6小时
- **总计**: 16-24小时

## 成功标准

1. ✅ 能够加载任意场景JSON文件
2. ✅ 运行真实的OptimizedScanAlgorithm
3. ✅ 电梯按照算法决策移动
4. ✅ 乘客正确上下电梯
5. ✅ 统计数据准确
6. ✅ 支持暂停/继续/停止
7. ✅ 支持速度调节

## 参考资料

### elevator_saga包

- GitHub: https://github.com/magwo/elevatorsaga (原始JavaScript版本)
- PyPI: elevator-py包（Python实现）

### 相关文件

- `algo/base_algorithm.py` - 算法基类
- `algo/optimized_scan.py` - SCAN算法实现
- `main.py` - CLI工具（参考如何运行算法）
- `tests/auto_test.py` - 自动化测试（参考如何加载场景）

## 下一步行动

1. **Phase 1**: 研究和实验
   ```bash
   # 创建研究脚本
   touch webui/research_elevator_saga.py

   # 实验Simulation API
   python webui/research_elevator_saga.py
   ```

2. **Phase 2**: 实现骨架
   ```bash
   # 创建RealSimulationEngine
   touch webui/real_simulation.py

   # 实现基本结构（不含算法集成）
   ```

3. **Phase 3**: 算法适配
   ```bash
   # 修改base_algorithm.py添加direct_mode
   # 测试单个算法
   ```

4. **Phase 4**: 完整集成
   ```bash
   # 在app.py中添加切换开关
   # 端到端测试
   ```

5. **Phase 5**: 优化和完善
   ```bash
   # 添加统计计算
   # 性能优化
   # 错误处理
   ```

## 总结

方案B能够提供真实的算法运行和准确的性能数据，但需要：
1. 深入理解elevator_saga内部API
2. 修改算法基类以支持direct模式
3. 实现状态提取和统计计算

相比方案C（Mock模拟），方案B需要更多的开发时间，但能提供真实的算法性能对比和准确的优化指标，适合生产环境和学术研究使用。
