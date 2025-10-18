# Simulator 改进文档

本文档总结了项目根目录 `simulator.py` 相比原始 `elevator_saga/server/simulator.py` 的主要变化。

---

## 📋 变化概览

根目录的 `simulator.py` 是为了支持 **WebUI 动态 max_ticks 控制** 和 **场景动态加载** 而创建的增强版本。

---

## 🆕 新增功能

### 1. **用户可配置的 max_ticks** ⭐⭐⭐

**问题背景**：
- 原版：max_ticks 只能从场景文件的 `duration` 字段读取，用户无法动态调整
- 用户需求：希望通过 WebUI 动态设置模拟运行的最大时长

**解决方案**：
添加了 `user_max_ticks` 字段用于持久化用户设置：

```python
# 根目录 simulator.py 新增字段（第121行）
class ElevatorSimulation:
    user_max_ticks: int | None  # 用户配置的 max_ticks（优先级高于场景默认值）
```

**实现细节**：

#### a. 初始化时设为 None
```python
# 第131行
def __init__(self, traffic_dir: str, _init_only: bool = False):
    # ...
    self.user_max_ticks = None  # 没有用户覆盖，默认为None
```

#### b. 加载场景时优先使用用户设置
```python
# load_current_traffic() 方法（第188-194行）
if self.user_max_ticks is not None:
    self.max_duration_ticks = self.user_max_ticks
    server_debug_log(f"Using user-configured max_ticks: {self.user_max_ticks}")
else:
    self.max_duration_ticks = building_config["duration"]
    server_debug_log(f"Using scenario default duration: {self.max_duration_ticks}")
```

#### c. reset() 不再清空 max_duration_ticks
```python
# reset() 方法对比

# 原版（elevator_saga/server/simulator.py 第650-658行）
def reset(self) -> None:
    # ...
    self.max_duration_ticks = 0  # ❌ 会清空用户设置

# 根目录版本（第626-638行）
def reset(self) -> None:
    # ...
    # ✅ 不再设置 max_duration_ticks = 0
    # max_duration_ticks 由 load_current_traffic() 管理
```

#### d. 新增 API 端点：`/api/config/max_ticks`
```python
# 第736-762行
@app.route("/api/config/max_ticks", methods=["POST"])
def set_max_ticks() -> Response | tuple[Response, int]:
    """设置最大模拟时长（ticks）"""
    max_ticks_int = int(data.get("max_ticks"))

    # 存储用户偏好并立即应用
    simulation.user_max_ticks = max_ticks_int
    simulation.max_duration_ticks = max_ticks_int
```

**使用流程**：
1. 用户在 WebUI 输入 max_ticks = 500
2. WebUI 调用 `/api/config/max_ticks` 设置 `user_max_ticks = 500`
3. 后续加载任何场景时，都会使用 500 而非场景默认值
4. 即使调用 `reset()`，用户设置仍然保留

---

### 2. **动态场景加载** ⭐⭐⭐

**问题背景**：
- 原版：没有按名称加载指定场景的机制
- 用户需求：WebUI 需要在运行时切换不同的场景文件

**解决方案**：
新增 `/api/load_scenario` API 端点：

```python
# 第765-808行
@app.route("/api/load_scenario", methods=["POST"])
def load_scenario() -> Response | tuple[Response, int]:
    """加载指定场景文件"""
    scenario_name = data.get("scenario_name")

    # 查找场景文件（不含.json后缀）
    scenario_file = None
    for f in simulation.traffic_files:
        if f.stem == scenario_name:  # stem是不含扩展名的文件名
            scenario_file = f
            break

    if not scenario_file:
        available = [f.stem for f in simulation.traffic_files]
        return json_response({
            "error": f"Scenario '{scenario_name}' not found",
            "available_scenarios": available
        }, 404)

    # 设置索引并加载场景
    simulation.current_traffic_index = simulation.traffic_files.index(scenario_file)
    simulation.load_current_traffic()

    return json_response({
        "success": True,
        "scenario": scenario_name,
        "elevators": len(simulation.elevators),
        "floors": len(simulation.floors),
        "passengers": len(simulation.traffic_queue),
        "max_ticks": simulation.max_duration_ticks
    })
```

**使用场景**：
```javascript
// WebUI 调用示例
POST /api/load_scenario
{
    "scenario_name": "large_morning_rush"
}

// 响应
{
    "success": true,
    "scenario": "large_morning_rush",
    "elevators": 5,
    "floors": 20,
    "passengers": 320,
    "max_ticks": 300
}
```

---

### 3. **改进的乘客上梯逻辑** ⭐⭐

**变化对比**：

#### 原版 `_process_passenger_in()`（第283-324行）
```python
def _process_passenger_in(self, elevator: ElevatorState) -> None:
    current_floor = elevator.current_floor
    # 只有电梯停止时才允许乘客上电梯
    if elevator.target_floor_direction != Direction.STOPPED:
        return
```

#### 根目录版本（第283-335行）
```python
def _process_passenger_in(self, elevator: ElevatorState) -> None:
    """
    处理乘客上梯
    前置条件：电梯必须停止在某个楼层
    """
    current_floor = elevator.current_floor

    # ✅ 改进：使用 run_status 而非 target_floor_direction 判断
    if elevator.run_status != ElevatorStatus.STOPPED:
        server_debug_log(
            f"✗ 电梯 E{elevator.id} 不能上梯：电梯未停止 (状态: {elevator.run_status.value})"
        )
        return

    # ✅ 新增：容量检查
    available_capacity = elevator.max_capacity - len(elevator.passengers)
    if available_capacity <= 0:
        server_debug_log(f"✗ 电梯 E{elevator.id} 已满，无法上梯")
        return
```

**改进点**：
1. 使用 `run_status` 判断更准确（区分物理停止和逻辑方向）
2. 添加了容量检查，避免超载
3. 添加了详细的调试日志

---

### 4. **改进的电梯状态更新** ⭐

#### 原版 `_update_elevator_status()`（第326-356行）
```python
def _update_elevator_status(self) -> None:
    """更新电梯运行状态"""
    for elevator in self.elevators:
        # 处理next_target_floor: 如果电梯已停止且没有当前目标方向
        if elevator.target_floor_direction == Direction.STOPPED:
            if elevator.next_target_floor is not None:
                self._set_elevator_target_floor(elevator, elevator.next_target_floor)
                self._process_passenger_in(elevator)  # ❌ 在这里调用上梯
                elevator.next_target_floor = None
```

#### 根目录版本（第336-360行）
```python
def _update_elevator_status(self) -> None:
    """
    更新电梯运行状态机：STOPPED → START_UP → CONSTANT_SPEED → START_DOWN → STOPPED
    只处理状态转移，不处理乘客上下梯逻辑
    """
    for elevator in self.elevators:
        # ✅ 改进：只处理有运动方向的电梯
        if elevator.target_floor_direction == Direction.STOPPED:
            continue  # 停止的电梯不需要状态转移

        # 有运动方向的电梯才需要启动状态转移
        if elevator.run_status == ElevatorStatus.STOPPED:
            elevator.run_status = ElevatorStatus.START_UP
```

**改进点**：
1. 职责更清晰：只处理状态转移，不处理乘客上下梯
2. 上梯逻辑移到了 `_process_elevator_stops()` 中统一处理
3. 添加了详细的状态转移日志

---

### 5. **改进的电梯停靠处理** ⭐⭐

#### 原版 `_process_elevator_stops()`（第446-482行）
```python
def _process_elevator_stops(self) -> None:
    # 处理下客和接客

    # 在这里处理乘客上梯
    self._process_passenger_in(elevator)

    # 如果电梯已经完全停止，发送IDLE事件
    if elevator.last_tick_direction == Direction.STOPPED:
        self._emit_event(EventType.IDLE, {...})

    # Note: next_target_floor is now handled in _update_elevator_status()
```

#### 根目录版本（第448-490行）
```python
def _process_elevator_stops(self) -> None:
    """
    处理停止状态的电梯：下梯 → 上梯 → 发出IDLE事件
    只在电梯处于STOPPED运行状态时执行
    """
    # 第一步：乘客下梯
    # ... 下梯逻辑 ...

    # 第二步：乘客上梯
    self._process_passenger_in(elevator)

    # ✅ 第三步：判断是否发出IDLE事件
    floor = self.floors[current_floor]
    has_waiting_passengers = len(floor.up_queue) > 0 or len(floor.down_queue) > 0

    if elevator.next_target_floor is None and not has_waiting_passengers:
        self._emit_event(EventType.IDLE, {"elevator": elevator.id, "floor": current_floor})

    # ✅ 第四步：处理下一个目标楼层
    if elevator.next_target_floor is not None:
        self._set_elevator_target_floor(elevator, elevator.next_target_floor)
        elevator.next_target_floor = None
```

**改进点**：
1. 明确了处理顺序：下梯 → 上梯 → IDLE检查 → 下一目标
2. IDLE 事件只在确实没有等待乘客时发出
3. `next_target_floor` 处理移回到这里（更符合逻辑）

---

### 6. **改进的 `_set_elevator_target_floor()`** ⭐⭐

#### 原版（第483-504行）
```python
def _set_elevator_target_floor(self, elevator: ElevatorState, floor: int) -> None:
    elevator.position.target_floor = floor
    server_debug_log(f"电梯 E{elevator.id} 被设定为前往 F{floor}")

    # 检查是否需要减速/加速调整
    new_target_floor_should_accel = self._should_start_deceleration(elevator)
    if not new_target_floor_should_accel:
        if elevator.run_status == ElevatorStatus.START_DOWN:
            elevator.run_status = ElevatorStatus.CONSTANT_SPEED
    # ...
```

#### 根目录版本（第491-512行）
```python
def _set_elevator_target_floor(self, elevator: ElevatorState, floor: int) -> None:
    """
    设置电梯目标楼层，并确保电梯能够正确启动移动
    这是最关键的函数 - 它确保电梯从停止状态启动
    """
    # ✅ 新增：楼层范围验证
    if not (0 <= floor < len(self.floors)):
        server_debug_log(f"❌ 电梯 E{elevator.id} 目标楼层 F{floor} 超出范围")
        return

    elevator.position.target_floor = floor

    # 🔑 关键改进：如果电梯停止且目标楼层不同，立即启动电梯
    if elevator.run_status == ElevatorStatus.STOPPED and elevator.current_floor != floor:
        elevator.run_status = ElevatorStatus.START_UP
        server_debug_log(
            f"✓ 电梯 E{elevator.id} 启动！状态: STOPPED → START_UP"
        )
```

**改进点**：
1. 添加了楼层范围验证，防止越界
2. 简化了逻辑：移除了复杂的加速/减速调整
3. **核心改进**：确保停止的电梯能立即启动（解决了乘客上梯后电梯不动的问题）

---

### 7. **改进的 `elevator_go_to_floor()`** ⭐⭐

#### 原版（第532-548行）
```python
def elevator_go_to_floor(self, elevator_id: int, floor: int, immediate: bool = False) -> None:
    if 0 <= elevator_id < len(self.elevators) and 0 <= floor < len(self.floors):
        elevator = self.elevators[elevator_id]
        if immediate:
            self._set_elevator_target_floor(elevator, floor)
        else:
            elevator.next_target_floor = floor
            server_debug_log(f"电梯 E{elevator_id} 下一目的地设定为 F{floor}")

            # 如果电梯已经停止且在目标楼层，立即处理乘客上车
            if elevator.target_floor_direction == Direction.STOPPED and elevator.current_floor == floor:
                server_debug_log(f"电梯 E{elevator_id} 已在目标楼层 F{floor}，处理乘客上车")
                self._process_passenger_in(elevator)
```

#### 根目录版本（第540-572行）
```python
def elevator_go_to_floor(self, elevator_id: int, floor: int, immediate: bool = False) -> None:
    """
    设置电梯去向，是生命周期开始，分配目的地

    Args:
        elevator_id: 电梯ID
        floor: 目标楼层
        immediate: 如果为True，立即设置目标；如果为False，存储为next_target_floor待处理
    """
    # ✅ 新增：更详细的参数验证和错误日志
    if not (0 <= elevator_id < len(self.elevators)):
        server_debug_log(f"❌ 电梯ID {elevator_id} 超出范围")
        return

    if not (0 <= floor < len(self.floors)):
        server_debug_log(f"❌ 目标楼层 F{floor} 超出范围 [0, {len(self.floors)-1}]")
        return

    elevator = self.elevators[elevator_id]

    if immediate:
        self._set_elevator_target_floor(elevator, floor)
        server_debug_log(f"✓ 电梯 E{elevator_id} 立即设定目标 F{floor}")
    else:
        elevator.next_target_floor = floor
        server_debug_log(f"✓ 电梯 E{elevator_id} 下一目的地设定为 F{floor}")

        # 如果电梯已在目标楼层，立即处理上车
        if elevator.target_floor_direction == Direction.STOPPED and elevator.current_floor == floor:
            server_debug_log(f"✓ 电梯 E{elevator_id} 已在目标楼层 F{floor}，处理乘客上车")
            self._process_passenger_in(elevator)
```

**改进点**：
1. 添加了详细的参数验证
2. 改进了错误处理（提前返回而非静默失败）
3. 添加了更详细的调试日志

---

## 🔧 代码质量改进

### 1. **更好的文档注释**

所有关键方法都添加了详细的文档字符串：

```python
# 根目录版本
def _process_passenger_in(self, elevator: ElevatorState) -> None:
    """
    处理乘客上梯
    前置条件：电梯必须停止在某个楼层
    """
```

### 2. **更好的调试日志**

使用了更清晰的日志格式：

```python
# 原版
server_debug_log(f"电梯{elevator.id} 状态:{old_status}->{elevator.run_status.value}")

# 根目录版本
server_debug_log(
    f"✓ 电梯{elevator.id} 状态转移: STOPPED → START_UP, 目标: F{elevator.target_floor}, "
    f"方向: {elevator.target_floor_direction.value}"
)
```

### 3. **清晰的职责分离**

- `_update_elevator_status()`: 只处理状态转移
- `_process_elevator_stops()`: 只处理停靠时的上下客
- `_set_elevator_target_floor()`: 只设置目标楼层

---

## 📊 对比总结表

| 特性 | 原版 (elevator_saga/server) | 根目录版本 |
|------|---------------------------|-----------|
| **max_ticks 配置** | ❌ 只能从场景文件读取 | ✅ 支持用户动态设置（user_max_ticks） |
| **场景加载** | ❌ 只能按索引切换 | ✅ 支持按名称加载（/api/load_scenario） |
| **上梯条件判断** | `target_floor_direction == STOPPED` | `run_status == STOPPED` (更准确) |
| **容量检查** | ❌ 无 | ✅ 上梯前检查容量 |
| **状态转移逻辑** | 混合在多处 | ✅ 集中在 `_update_elevator_status()` |
| **电梯启动** | 需要手动调整状态 | ✅ 自动启动（在 `_set_elevator_target_floor` 中） |
| **参数验证** | 基本验证 | ✅ 详细验证+错误日志 |
| **调试日志** | 基本日志 | ✅ 详细的状态转移日志 |
| **reset() 行为** | 清空 max_duration_ticks | ✅ 保留用户设置 |

---

## 🎯 核心改进

### 最重要的3个改进：

1. **user_max_ticks 机制** ⭐⭐⭐
   - 允许用户通过 WebUI 动态控制模拟时长
   - 设置持久化，跨场景和 reset 保留

2. **动态场景加载 API** ⭐⭐⭐
   - WebUI 可以按名称切换场景
   - 返回场景详细信息（电梯数、楼层数、乘客数）

3. **电梯启动逻辑优化** ⭐⭐⭐
   - 确保停止的电梯在设置目标后能立即启动
   - 解决了"乘客上梯后电梯不动"的问题

---

## 🚀 使用场景

### 场景1：用户想运行500 ticks而非默认的200

```javascript
// 1. 设置 max_ticks
POST /api/config/max_ticks
{ "max_ticks": 500 }

// 2. 加载场景
POST /api/load_scenario
{ "scenario_name": "large_morning_rush" }

// 3. 运行模拟
// 此时模拟会运行到 500 ticks（而非场景默认的 200）
```

### 场景2：连续测试多个场景，使用相同的 max_ticks

```javascript
// 1. 设置一次 max_ticks
POST /api/config/max_ticks
{ "max_ticks": 500 }

// 2. 测试场景A
POST /api/load_scenario
{ "scenario_name": "scenario_a" }
// 运行模拟... (500 ticks)

// 3. 测试场景B（max_ticks 仍为 500）
POST /api/load_scenario
{ "scenario_name": "scenario_b" }
// 运行模拟... (500 ticks)

// 4. 测试场景C（max_ticks 仍为 500）
POST /api/load_scenario
{ "scenario_name": "scenario_c" }
// 运行模拟... (500 ticks)
```

---

## 📝 注意事项

1. **user_max_ticks 优先级**：
   - 如果设置了 `user_max_ticks`，将始终使用该值
   - 如果未设置（None），则使用场景文件的 `duration`

2. **reset() 行为变化**：
   - 原版会清空 `max_duration_ticks`
   - 新版不会清空，由 `load_current_traffic()` 管理

3. **场景加载时机**：
   - WebUI 必须在启动模拟前调用 `/api/load_scenario`
   - 否则 simulator 使用的是上一次加载的场景

---

## 🔍 调试建议

### 查看 max_ticks 来源：

根据日志可以判断使用的是哪个值：

```
# 使用用户设置
[SERVER-DEBUG] Using user-configured max_ticks: 500

# 使用场景默认值
[SERVER-DEBUG] Using scenario default duration: 200
```

### 查看电梯启动状态：

```
# 成功启动
[SERVER-DEBUG] ✓ 电梯 E0 启动！状态: STOPPED → START_UP, 目标方向: up

# 启动失败（通常是目标楼层越界）
[SERVER-DEBUG] ❌ 电梯 E0 目标楼层 F25 超出范围 [0, 19]
```

---

**最后更新**：2025-10-18
**对比版本**：elevator_saga/server/simulator.py vs 根目录/simulator.py
