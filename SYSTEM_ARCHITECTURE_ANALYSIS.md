# 电梯调度系统完整架构解析

**生成日期**: 2025-10-18
**更新日期**: 2025-10-18
**目的**: 详细解释 Simulator.py 的运行逻辑和算法交互机制

> **📌 最新更新**:
> - ✅ 添加了 WebUI 动态 max_ticks 控制
> - ✅ 添加了场景动态加载 API
> - ✅ 修复了所有核心算法（base_scan, optimized_scan, simple_fcfs）
> - ✅ 创建了算法实现指南 (ALGORITHM_IMPLEMENTATION_GUIDE.md)
> - 📄 详细改动见 SIMULATOR_CHANGES.md

---

## 一、整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                    WebUI (Port 8080)                         │
│               webui/direct_simulation.py                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  控制面板:                                              │ │
│  │   - 场景选择 (scenario_name)                           │ │
│  │   - 算法选择 (ScanController, OptimizedScanAlgorithm)  │ │
│  │   - ✨ max_ticks 动态设置 (可覆盖场景默认值)           │ │
│  │   - 速度控制                                           │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────┬─────────────────────────────────────────────────┘
             │
             ├─ ✨ 调用 /api/load_scenario (加载指定场景)
             ├─ ✨ 调用 /api/config/max_ticks (设置最大时长)
             ├─ 启动算法线程 (后台运行)
             │  └─ 事件驱动循环，调用 /api/step
             │
             └─ 启动轮询线程 (获取状态显示给前端)
                └─ 定期调用 /api/state

             ↓ HTTP REST API ↓

┌────────────────────────────────────────────────────────────┐
│            Simulator Server (Port 8000)                    │
│                   simulator.py                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │        ElevatorSimulation (核心引擎)                 │ │
│  │  - 电梯物理模拟                                       │ │
│  │  - 乘客队列管理                                       │ │
│  │  - 事件生成与分发                                     │ │
│  │  - ✨ user_max_ticks (用户自定义时长)                │ │
│  │  - ✨ 场景动态加载                                    │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  新增 API:                                                 │
│   - POST /api/load_scenario (加载指定场景)                │
│   - POST /api/config/max_ticks (设置最大时长)             │
└────────────────────────────────────────────────────────────┘
```

---

## 二、Simulator.py 核心逻辑

### 1. 核心数据结构

```python
class ElevatorSimulation:
    # 状态
    state: SimulationState
        ├─ tick: int                              # 当前时间刻
        ├─ elevators: List[ElevatorState]         # 所有电梯状态
        ├─ floors: List[FloorState]               # 所有楼层状态
        ├─ passengers: Dict[int, PassengerInfo]   # 所有乘客信息
        └─ events: List[SimulationEvent]          # 历史事件列表

    # 输入
    traffic_queue: List[TrafficEntry]  # 乘客到达队列（按时间排序）

    # ✨ 新增：时长控制
    max_duration_ticks: int            # 当前有效的最大时长
    user_max_ticks: int | None         # 用户配置的时长（优先级最高）

    # 场景管理
    current_traffic_index: int         # 当前加载的场景索引
    traffic_files: List[Path]          # 可用的场景文件列表
```

### 2. 电梯状态机

```python
ElevatorState:
    current_floor: int                    # 当前楼层 (整数，如 0, 1, 2...)
    position: FloatPosition               # 精确位置
        ├─ current_floor_float: float     # 浮点楼层 (如 1.5 表示在1-2层之间)
        ├─ floor_up_position: int         # 楼层内位置 (0-9，0表示恰好在楼层)
        └─ target_floor: int              # 目标楼层

    run_status: ElevatorStatus            # 运行状态
        ├─ STOPPED         # 停止
        ├─ START_UP        # 加速启动 (速度=1单位/tick)
        ├─ CONSTANT_SPEED  # 匀速 (速度=2单位/tick)
        └─ START_DOWN      # 减速 (速度=1单位/tick)

    target_floor_direction: Direction     # 目标方向（计算属性）
        ├─ UP              # 向上（current_floor < target_floor）
        ├─ DOWN            # 向下（current_floor > target_floor）
        └─ STOPPED         # 停止（current_floor == target_floor && floor_up_position == 0）

    last_tick_direction: Direction        # 上一tick的移动方向

    next_target_floor: int | None         # 下一个目标楼层（队列）
    passengers: List[int]                 # 电梯内乘客ID列表
```

**关键理解**：
- `target_floor` 是当前要去的楼层
- `next_target_floor` 是队列中的下一个目标（等当前目标完成后使用）
- `run_status` 是物理状态（停止/加速/匀速/减速）
- `target_floor_direction` 是逻辑方向（计算出来的，基于 current_floor 和 target_floor）

---

## 三、每个 Tick 的执行流程

每次调用 `/api/step` 时，Simulator 执行一个 tick：

```python
def step(num_ticks=1) -> List[SimulationEvent]:
    self.tick += 1
    events = self._process_tick()
    return events  # 返回这个tick产生的所有事件

def _process_tick() -> List[SimulationEvent]:
    # 1️⃣ 更新电梯状态机
    self._update_elevator_status()

    # 2️⃣ 处理新乘客到达
    self._process_arrivals()

    # 3️⃣ 移动电梯
    self._move_elevators()

    # 4️⃣ 处理电梯停靠（乘客上下）
    self._process_elevator_stops()

    return self.state.events[events_start:]  # 返回本tick生成的事件
```

### 详细流程：

#### **1️⃣ `_update_elevator_status()` - 状态机转换**

```python
for elevator in self.elevators:
    # 情况A: 电梯已到达目标，没有移动方向
    if elevator.target_floor_direction == Direction.STOPPED:
        if elevator.next_target_floor is not None:
            # 有排队的目标，设置为当前目标
            self._set_elevator_target_floor(elevator, elevator.next_target_floor)
            self._process_passenger_in(elevator)  # 处理乘客上车
            elevator.next_target_floor = None
            # 继续执行后续的状态转换
        else:
            continue  # 没有目标，跳过

    # 情况B: 电梯有目标，但处于停止状态 → 启动
    if elevator.run_status == ElevatorStatus.STOPPED:
        if elevator.target_floor_direction != Direction.STOPPED:
            elevator.run_status = ElevatorStatus.START_UP  # 🚀 启动！

    # 情况C: 加速状态 → 匀速
    elif elevator.run_status == ElevatorStatus.START_UP:
        elevator.run_status = ElevatorStatus.CONSTANT_SPEED
```

**关键点**：
- 这里处理从 `STOPPED` → `START_UP` 的转换
- 只有 `target_floor_direction != STOPPED` 时才启动

#### **2️⃣ `_process_arrivals()` - 新乘客到达**

```python
while self.traffic_queue and self.traffic_queue[0].tick <= self.tick:
    traffic_entry = self.traffic_queue.pop(0)
    passenger = PassengerInfo(...)
    self.passengers[passenger.id] = passenger

    # 根据目的地方向，加入楼层队列
    if passenger.destination > passenger.origin:
        self.floors[passenger.origin].up_queue.append(passenger.id)
        self._emit_event(EventType.UP_BUTTON_PRESSED, {...})  # 🔔 发送事件
    else:
        self.floors[passenger.origin].down_queue.append(passenger.id)
        self._emit_event(EventType.DOWN_BUTTON_PRESSED, {...})  # 🔔 发送事件
```

**产生的事件**：
- `UP_BUTTON_PRESSED` 或 `DOWN_BUTTON_PRESSED`
- 算法会收到这些事件，并调用 `on_passenger_call()`

#### **3️⃣ `_move_elevators()` - 物理移动**

```python
for elevator in self.elevators:
    # 根据 run_status 获取移动速度
    if elevator.run_status == ElevatorStatus.START_UP:
        movement_speed = 1
    elif elevator.run_status == ElevatorStatus.CONSTANT_SPEED:
        movement_speed = 2
    elif elevator.run_status == ElevatorStatus.START_DOWN:
        movement_speed = 1
    else:  # STOPPED
        movement_speed = 0

    # 根据方向移动
    if elevator.target_floor_direction == Direction.UP:
        new_floor = elevator.position.floor_up_position_add(movement_speed)
    elif elevator.target_floor_direction == Direction.DOWN:
        new_floor = elevator.position.floor_up_position_add(-movement_speed)

    # 发送移动事件
    self._emit_event(EventType.ELEVATOR_MOVE, {...})

    # 检查是否需要减速
    if elevator.run_status == ElevatorStatus.CONSTANT_SPEED:
        if self._should_start_deceleration(elevator):
            elevator.run_status = ElevatorStatus.START_DOWN

        # 即将到达楼层，发送APPROACHING事件
        if self._near_next_stop(elevator):
            self._emit_event(EventType.ELEVATOR_APPROACHING, {...})  # 🔔

    # 检查是否到达目标
    if target_floor == new_floor and elevator.position.floor_up_position == 0:
        elevator.run_status = ElevatorStatus.STOPPED
        self._emit_event(EventType.STOPPED_AT_FLOOR, {...})  # 🔔
```

**产生的事件**：
- `ELEVATOR_MOVE` - 每次移动
- `ELEVATOR_APPROACHING` - 即将到达某层
- `PASSING_FLOOR` - 经过某层
- `STOPPED_AT_FLOOR` - 到达目标楼层

#### **4️⃣ `_process_elevator_stops()` - 处理停靠**

```python
for elevator in self.elevators:
    # 只处理刚刚停下的电梯（run_status == STOPPED）
    if elevator.run_status != ElevatorStatus.STOPPED:
        continue

    # 如果已经完全停止（方向也是STOPPED），发送IDLE事件
    if elevator.last_tick_direction == Direction.STOPPED:
        self._emit_event(EventType.IDLE, {...})  # 🔔
        continue

    # 让乘客下车
    passengers_to_remove = []
    for passenger_id in elevator.passengers:
        passenger = self.passengers[passenger_id]
        if passenger.destination == current_floor:
            passenger.dropoff_tick = self.tick
            passenger.arrived = True
            passengers_to_remove.append(passenger_id)

    for passenger_id in passengers_to_remove:
        elevator.passengers.remove(passenger_id)
        self._emit_event(EventType.PASSENGER_ALIGHT, {...})  # 🔔
```

**产生的事件**：
- `PASSENGER_ALIGHT` - 乘客下车
- `IDLE` - 电梯空闲

---

## 四、算法如何控制电梯

### 算法的输入：**事件 (Events)**

算法通过 `ElevatorController` 基类连接到 Simulator：

```python
class OptimizedScanAlgorithm(BaseAlgorithm):
    # 算法通过以下回调函数接收事件：

    def on_passenger_call(passenger, floor, direction):
        # 输入：新乘客按按钮
        # 事件：UP_BUTTON_PRESSED / DOWN_BUTTON_PRESSED

    def on_elevator_approaching(elevator, floor, direction):
        # 输入：电梯即将到达某层
        # 事件：ELEVATOR_APPROACHING

    def on_elevator_stopped(elevator, floor):
        # 输入：电梯到达目标楼层
        # 事件：STOPPED_AT_FLOOR

    def on_passenger_board(elevator, passenger):
        # 输入：乘客上车
        # 事件：PASSENGER_BOARD

    def on_elevator_idle(elevator):
        # 输入：电梯空闲
        # 事件：IDLE
```

### 算法的输出：**命令 (Commands)**

算法通过调用 `elevator.go_to_floor()` 来控制电梯：

```python
# 方式1: 立即设置目标（immediate=True）
elevator.go_to_floor(floor=5, immediate=True)
# → 调用 simulator.elevator_go_to_floor(elevator_id, 5, immediate=True)
# → 调用 simulator._set_elevator_target_floor(elevator, 5)
# → 直接设置 elevator.target_floor = 5

# 方式2: 排队设置目标（immediate=False，默认）
elevator.go_to_floor(floor=5, immediate=False)
# → 调用 simulator.elevator_go_to_floor(elevator_id, 5, immediate=False)
# → 设置 elevator.next_target_floor = 5
# → 在下一个tick的_update_elevator_status()中处理
```

**关键理解**：
- `immediate=True`: 立即设置 `target_floor`，但 `run_status` 不会立即改变
- `immediate=False`: 设置 `next_target_floor`，等电梯停止后再处理
- 无论哪种方式，电梯启动都需要等到下一个 tick 的 `_update_elevator_status()`

---

## 五、算法执行流程

```
1. WebUI 启动算法线程
   ↓
2. 算法调用 run() 方法（来自 ElevatorController）
   ↓
3. 进入事件循环:
   while True:
       ├─ 调用 simulator.step()  → 获取事件列表
       │
       ├─ 遍历事件:
       │   for event in events:
       │       if event.type == "up_button_pressed":
       │           on_passenger_call(passenger, floor, "up")
       │       elif event.type == "passenger_board":
       │           on_passenger_board(elevator, passenger)
       │       elif event.type == "elevator_idle":
       │           on_elevator_idle(elevator)
       │       ...
       │
       └─ 继续下一个tick
```

### 事件 → 回调映射

```python
EventType.UP_BUTTON_PRESSED    → on_passenger_call(passenger, floor, "up")
EventType.DOWN_BUTTON_PRESSED  → on_passenger_call(passenger, floor, "down")
EventType.PASSENGER_BOARD      → on_passenger_board(elevator, passenger)
EventType.PASSENGER_ALIGHT     → on_passenger_alight(elevator, passenger, floor)
EventType.STOPPED_AT_FLOOR     → on_elevator_stopped(elevator, floor)
EventType.IDLE                 → on_elevator_idle(elevator)
EventType.ELEVATOR_APPROACHING → on_elevator_approaching(elevator, floor, direction)
EventType.PASSING_FLOOR        → on_elevator_passing_floor(elevator, floor, direction)
```

---

## 六、完整时序示例

### 场景：1个乘客从F0到F5

```
Tick 1: 乘客到达
  ┌─────────────────────────────────────────────────────┐
  │ Simulator:                                          │
  │  _process_arrivals():                               │
  │   - 从 traffic_queue 中取出乘客1                     │
  │   - 添加到 floors[0].up_queue                       │
  │   - 发送事件: UP_BUTTON_PRESSED(floor=0, psg=1)     │
  └─────────────────────────────────────────────────────┘
           ↓ 事件传递给算法
  ┌─────────────────────────────────────────────────────┐
  │ Algorithm:                                          │
  │  on_passenger_call(psg=1, floor=0, direction="up")  │
  │   - 选择电梯E0（最近且空闲）                         │
  │   - 调用: E0.go_to_floor(0, immediate=True)         │
  └─────────────────────────────────────────────────────┘
           ↓ API调用
  ┌─────────────────────────────────────────────────────┐
  │ Simulator:                                          │
  │  elevator_go_to_floor(0, 0, immediate=True)         │
  │   - _set_elevator_target_floor(E0, 0)               │
  │   - E0.target_floor = 0                             │
  │   - E0.target_floor_direction = STOPPED (已在F0)    │
  │   - E0.run_status 仍然是 STOPPED                    │
  └─────────────────────────────────────────────────────┘

Tick 2: 电梯在F0，乘客上车
  ┌─────────────────────────────────────────────────────┐
  │ Simulator:                                          │
  │  _update_elevator_status():                         │
  │   - E0.target_floor_direction == STOPPED            │
  │   - E0.next_target_floor == None                    │
  │   - 跳过（电梯已在目标楼层）                         │
  │                                                     │
  │  _process_elevator_stops():                         │
  │   - E0.run_status == STOPPED                        │
  │   - E0.last_tick_direction == STOPPED               │
  │   - 发送事件: IDLE(elevator=0, floor=0)             │
  └─────────────────────────────────────────────────────┘
           ↓ IDLE事件传递给算法
  ┌─────────────────────────────────────────────────────┐
  │ Algorithm:                                          │
  │  on_elevator_idle(E0)                               │
  │   - 发现F0有等待乘客                                 │
  │   - 调用: E0.go_to_floor(0, immediate=False)        │
  └─────────────────────────────────────────────────────┘
           ↓ API调用
  ┌─────────────────────────────────────────────────────┐
  │ Simulator:                                          │
  │  elevator_go_to_floor(0, 0, immediate=False)        │
  │   - E0.next_target_floor = 0                        │
  │   - 检测到 E0 已在F0 且 direction==STOPPED           │
  │   - 调用 _process_passenger_in(E0)                  │
  │     - 乘客1上车                                      │
  │     - 发送事件: PASSENGER_BOARD(elev=0, psg=1)      │
  └─────────────────────────────────────────────────────┘
           ↓ PASSENGER_BOARD事件传递给算法
  ┌─────────────────────────────────────────────────────┐
  │ Algorithm:                                          │
  │  on_passenger_board(E0, psg=1)                      │
  │   - 获取乘客目的地: destination=5                    │
  │   - 调用: E0.go_to_floor(5, immediate=True)         │
  └─────────────────────────────────────────────────────┘
           ↓ API调用
  ┌─────────────────────────────────────────────────────┐
  │ Simulator:                                          │
  │  elevator_go_to_floor(0, 5, immediate=True)         │
  │   - _set_elevator_target_floor(E0, 5)               │
  │   - E0.target_floor = 5                             │
  │   - E0.target_floor_direction = UP                  │
  │   - E0.run_status 仍然是 STOPPED ⚠️                 │
  └─────────────────────────────────────────────────────┘

Tick 3: 电梯启动
  ┌─────────────────────────────────────────────────────┐
  │ Simulator:                                          │
  │  _update_elevator_status():                         │
  │   - E0.target_floor_direction == UP (不是STOPPED)   │
  │   - 跳过第一个if分支                                 │
  │   - E0.run_status == STOPPED                        │
  │   - E0.target_floor_direction != STOPPED            │
  │   - ✅ E0.run_status = START_UP                     │
  │                                                     │
  │  _move_elevators():                                 │
  │   - movement_speed = 1 (START_UP状态)               │
  │   - E0.position: 0.0 → 0.1                          │
  │   - 发送事件: ELEVATOR_MOVE                         │
  └─────────────────────────────────────────────────────┘

Tick 4: 电梯加速完成，进入匀速
  ┌─────────────────────────────────────────────────────┐
  │ Simulator:                                          │
  │  _update_elevator_status():                         │
  │   - E0.run_status == START_UP                       │
  │   - ✅ E0.run_status = CONSTANT_SPEED               │
  │                                                     │
  │  _move_elevators():                                 │
  │   - movement_speed = 2 (CONSTANT_SPEED状态)         │
  │   - E0.position: 0.1 → 0.3                          │
  └─────────────────────────────────────────────────────┘

... (继续移动直到到达F5)

Tick N: 电梯到达F5
  ┌─────────────────────────────────────────────────────┐
  │ Simulator:                                          │
  │  _move_elevators():                                 │
  │   - E0到达F5，position = 5.0                        │
  │   - E0.run_status = STOPPED                         │
  │   - 发送事件: STOPPED_AT_FLOOR(elev=0, floor=5)     │
  │                                                     │
  │  _process_elevator_stops():                         │
  │   - 检查乘客目的地                                   │
  │   - 乘客1目的地是F5                                  │
  │   - 乘客1下车                                        │
  │   - 发送事件: PASSENGER_ALIGHT(elev=0, psg=1)       │
  └─────────────────────────────────────────────────────┘
```

---

## 七、关键时序问题

### 问题：为什么Tick 2设置目标后，电梯在Tick 3才启动？

**原因**：事件处理和状态转换的时序

1. **Tick 2 的执行顺序**：
   ```
   _update_elevator_status()  // 此时还没有设置target_floor
   ↓
   _process_arrivals()
   ↓
   _move_elevators()
   ↓
   _process_elevator_stops()  // 乘客上车
     ↓ 发送 PASSENGER_BOARD 事件
     ↓ 算法收到事件
     ↓ 算法调用 go_to_floor(5, immediate=True)
     ↓ 设置 target_floor = 5
   ```

   **关键**：`_update_elevator_status()` 已经执行完了，所以状态转换要等下一个tick！

2. **Tick 3**：
   ```
   _update_elevator_status()  // 检测到 target_floor=5，设置 run_status=START_UP
   ↓
   _move_elevators()         // 开始移动！
   ```

### immediate=True vs immediate=False

| 特性 | immediate=True | immediate=False |
|-----|----------------|-----------------|
| 设置时机 | 当前tick立即设置 `target_floor` | 设置 `next_target_floor`，等待处理 |
| 生效时机 | 下一tick的 `_update_elevator_status()` | 电梯停止后的 `_update_elevator_status()` |
| 适用场景 | 紧急改变目标（如乘客上车后去目的地） | 排队多个目标 |

---

## 八、已实现的调度算法

### 1. SimpleFCFSAlgorithm (简单先来先服务)
- **文件**: `algo/simple_fcfs.py`
- **原理**: 最简单的调度策略
- **实现**:
  - 新乘客呼叫 → 分配最近的电梯
  - 乘客上车 → 立即前往目的地
  - 电梯空闲 → 前往最近等待的乘客
- **✅ 已修复**: 添加 internal_targets 跟踪、空闲任务分配

### 2. ScanController (SCAN电梯算法)
- **文件**: `algo/base_scan.py`
- **原理**: 电梯在一个方向上扫描到端点，然后掉头
- **实现**:
  - 电梯向上扫描 → 返回 max(上方目标) 作为下一站
  - 到达最高目标后 → 转向向下
  - 途中通过 on_elevator_approaching 停靠接客
  - 智能分配：最近的空闲电梯响应新呼叫
- **✅ 已修复**:
  - 移除了 assigned_calls 机制（允许多电梯服务同一楼层）
  - 修正了 _find_next_target 返回端点而非最近点
  - 空闲时立即分配新任务
  - 完整的 internal_targets 跟踪

### 3. OptimizedScanAlgorithm (优化SCAN)
- **文件**: `algo/optimized_scan.py`
- **原理**: 基于 SCAN + 智能评分系统
- **实现**:
  - 使用评分函数选择最佳电梯（考虑距离、负载、方向）
  - 顺路接客（approaching 时判断）
  - 负载均衡
- **✅ 已修复**: 添加 internal_targets 跟踪、空闲任务分配

### 📚 算法实现最佳实践

详见 `algo/ALGORITHM_IMPLEMENTATION_GUIDE.md`，包含：
- ❌ 4个常见陷阱
- ✅ 最小可行算法模板
- 🧪 测试检查清单
- 🐛 调试技巧

**关键原则**:
1. ❌ 不使用 `assigned_calls: Set[int]` (楼层级标记会导致死锁)
2. ✅ 跟踪 `internal_targets: Dict[int, Set[int]]` (车内乘客目的地)
3. ✅ 空闲时立即调用 `_assign_call_to_idle_elevator()`
4. ✅ SCAN 算法返回端点 (max/min)，而非最近点

---

## 九、调试技巧

### 1. 启用服务器调试日志
```bash
python simulator.py --debug
```

### 2. 关键日志点
- `_update_elevator_status()`: 查看状态转换
- `_move_elevators()`: 查看移动逻辑
- `_process_elevator_stops()`: 查看乘客上下车

### 3. 检查状态一致性
```python
print(f"E{elevator.id}: floor={current_floor}, target={target_floor}, "
      f"direction={target_floor_direction}, status={run_status}")
```

---

## 十、WebUI 工作流程

### 启动新模拟的完整流程

```javascript
// 1. 用户在 WebUI 选择配置
scenario: "large_morning_rush"
algorithm: "ScanController"
max_ticks: 500  // ✨ 用户自定义（可覆盖场景默认的200）

// 2. WebUI 建立 WebSocket 连接
ws.connect()

// 3. WebUI 发送启动消息
ws.send({
    type: "start",
    scenario: "large_morning_rush",
    algorithm: "ScanController",
    max_ticks: 500  // ✨ 传递给后端
})

// 4. direct_simulation.py 处理启动
async def start():
    # 4.1 ✨ 加载场景
    POST /api/load_scenario
    { "scenario_name": "large_morning_rush" }

    # 4.2 ✨ 设置 max_ticks
    POST /api/config/max_ticks
    { "max_ticks": 500 }

    # 4.3 启动算法线程
    algorithm_thread.start()  // 在后台调用 algorithm.start()

    # 4.4 启动轮询循环
    while running:
        state = GET /api/state
        ws.send({ type: "state_update", ...state })
        await asyncio.sleep(0.2 / speed)

// 5. 算法线程运行
while True:
    events = POST /api/step { "ticks": 1 }
    for event in events:
        dispatch_to_callbacks(event)

// 6. 模拟结束条件
if completed_passengers >= total_passengers:
    # 所有乘客完成
    ws.send({ type: "complete", stats: {...} })
elif tick >= max_ticks:
    # 达到最大时长
    ws.send({ type: "complete", stats: {...} })
```

---

## 十一、最新改进总结

### ✨ 新增功能

#### 1. 动态 max_ticks 控制
- **问题**: 用户无法动态调整模拟时长
- **解决**: 添加 `user_max_ticks` 机制
- **使用**: WebUI 可设置 max_ticks，优先级高于场景默认值
- **持久化**: 跨场景和 reset 保留用户设置

#### 2. 场景动态加载
- **问题**: 无法在运行时切换场景
- **解决**: 新增 `/api/load_scenario` API
- **使用**: WebUI 按名称加载场景，返回场景元数据

#### 3. 算法问题修复
- **问题**:
  - 最后几位乘客无法下电梯
  - 大规模场景电梯卡住
  - 多台电梯只有一台工作
- **解决**:
  - ✅ 移除 assigned_calls 机制
  - ✅ 修正 SCAN 返回端点逻辑
  - ✅ 空闲时立即分配任务
  - ✅ 完整的 internal_targets 跟踪

#### 4. 开发文档完善
- **SIMULATOR_CHANGES.md**: Simulator 详细改动对比
- **ALGORITHM_IMPLEMENTATION_GUIDE.md**: 算法实现最佳实践

### 🔧 代码质量改进
- 更详细的调试日志
- 更清晰的职责分离
- 完整的参数验证
- 改进的错误处理

---

## 十二、总结

### Simulator的核心职责
1. **物理模拟**：电梯移动、加减速
2. **事件生成**：将状态变化转换为事件
3. **乘客管理**：上下车、队列管理
4. **✨ 配置管理**: max_ticks、场景加载

### 算法的核心职责
1. **监听事件**：通过回调函数接收事件
2. **决策**：根据事件做出调度决策
3. **发送命令**：通过 `go_to_floor()` 控制电梯
4. **✅ 状态跟踪**: internal_targets、waiting 队列

### 关键设计原则
- **事件驱动**：Simulator产生事件，算法响应事件
- **状态分离**：物理状态（run_status）和逻辑状态（target_floor_direction）分离
- **时序明确**：状态转换在tick开始，事件处理在tick结束
- **✨ 用户优先**: user_max_ticks 优先于场景默认值

### 🎯 推荐阅读顺序
1. **本文档** - 理解整体架构和工作流程
2. **SIMULATOR_CHANGES.md** - 了解最新改进
3. **ALGORITHM_IMPLEMENTATION_GUIDE.md** - 学习算法实现最佳实践
4. **源码** - 深入理解实现细节
