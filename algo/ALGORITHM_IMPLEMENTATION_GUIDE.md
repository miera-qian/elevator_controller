# 电梯调度算法实现指南

本文档总结了在实现电梯调度算法时的**关键注意事项**和**常见陷阱**，基于base_scan算法的调试经验。

---

## 核心原则

### 1. 理解模拟器的自动机制

**✅ 正确理解**：
- 模拟器会**自动处理boarding（上客）**
- 电梯停靠后，如果有空间，同方向的乘客会自动上车
- 算法只需要决策"电梯的下一个目标楼层"

**❌ 常见错误**：
- 认为需要手动触发boarding
- 使用"踢一脚"机制（go_to_floor到相邻楼层）来触发上客
- 这会导致电梯在楼层间反复横跳

**建议**：
```python
# ❌ 不推荐：踢一脚
def on_elevator_stopped(self, elevator, floor):
    if has_waiting_passengers:
        next_floor = floor + 1  # 踢一脚触发boarding
        elevator.go_to_floor(next_floor)
        return

# ✅ 推荐：信任模拟器
def on_elevator_stopped(self, elevator, floor):
    # 乘客会自动上车，直接决策下一站
    next_target = self._find_next_target(...)
    if next_target:
        elevator.go_to_floor(next_target)
```

---

## 常见陷阱

### 陷阱1：使用楼层级别的"已分配"标记 🔥🔥🔥

**问题描述**：
使用 `assigned_calls: Set[int]` 按楼层标记已分配的呼叫。

**为什么这是错误的**：
- 一个楼层可能有**100个乘客等待**
- 一台电梯只能载**8-15人**
- 一旦一台电梯分配到该楼层，楼层被"锁定"
- 其他电梯认为"已有人负责"，不再响应
- **结果**：100人等待，只有1台电梯工作，其他4台idle

**实际案例**：
```python
# ❌ 错误实现
self.assigned_calls: Set[int] = set()

def _assign_call_to_idle_elevator(self):
    for floor, passengers in self.waiting_up.items():
        if passengers and floor not in self.assigned_calls:  # ❌
            # 分配第一台电梯
            elevator.go_to_floor(floor)
            self.assigned_calls.add(floor)  # ❌ 楼层被锁定
            break

# 问题：F0有100人，E0被分配后，F0被标记
#      E1/E2/E3/E4 看到F0已分配，跳过
#      结果：只有E0工作
```

**✅ 正确实现**：
```python
# 方案A：完全移除assigned_calls
def _assign_call_to_idle_elevator(self):
    for floor, passengers in self.waiting_up.items():
        if passengers:  # ✅ 只要有人等，就可以分配
            elevator.go_to_floor(floor)
            # 不标记！允许多台电梯响应同一楼层

# 方案B：使用电梯级别的目标标记
self.elevator_targets: Dict[int, int] = {}  # elevator_id -> target_floor

def _assign_call_to_idle_elevator(self):
    # 检查某楼层是否已有足够电梯前往
    elevators_going_to_floor = count_elevators_going_to(floor)
    passengers_waiting = len(self.waiting_up[floor])
    if elevators_going_to_floor * AVG_CAPACITY < passengers_waiting:
        # 还需要更多电梯
        assign_elevator_to(floor)
```

**检查清单**：
- [ ] 是否使用了 `Set[int]` 存储已分配楼层？ → 考虑移除
- [ ] 是否检查 `floor not in assigned_calls`？ → 改为只检查是否有人等待
- [ ] 是否考虑了一个楼层可能需要多台电梯？

---

### 陷阱2：算法逻辑与目标选择不一致 🔥🔥

**问题描述**：
算法声称实现某种策略，但 `_find_next_target()` 的实现不符合该策略。

**SCAN算法案例**：

**SCAN算法的本质**：
- "电梯扫描算法"，类似磁盘调度的SCAN
- 电梯在一个方向上**扫描到端点**（最高或最低楼层）
- 然后掉头，开始反方向扫描

**❌ 错误实现**：
```python
def _find_next_target(self, elevator, current_floor, direction):
    all_possible_stops = internal_targets | external_calls

    if direction == "up":
        stops_above = [f for f in all_possible_stops if f > current_floor]
        return min(stops_above)  # ❌ 返回最近的！

    # 问题：这不是SCAN，这是"最近优先"
    # 电梯会在中间楼层反复停靠，无法"扫描到端点"
```

**实际后果**：
```
E0上行，载着P1→F19, P2→F18
F5有外部呼叫
_find_next_target返回: min(5, 18, 19) = 5

E0去F5接客，然后继续找next_target
如果F5-F19之间还有其他呼叫，E0会一直在中间停
可能永远到不了F19 → 车内乘客无法下车
```

**✅ 正确实现**：
```python
def _find_next_target(self, elevator, current_floor, direction):
    all_possible_stops = internal_targets | external_calls

    if direction == "up":
        stops_above = [f for f in all_possible_stops if f > current_floor]
        return max(stops_above)  # ✅ 返回最高的（端点）

    elif direction == "down":
        stops_below = [f for f in all_possible_stops if f < current_floor]
        return min(stops_below)  # ✅ 返回最低的（端点）

    # 这样电梯会扫描到端点，途中会在on_elevator_approaching中停靠接客
```

**通用原则**：
| 算法类型 | 目标选择逻辑 |
|---------|------------|
| SCAN | 方向上的**最远点**（端点） |
| FCFS | **最早呼叫**的楼层 |
| SSTF | **最近**的楼层 |
| LOOK | 方向上的**最远点**，但不必到顶/底 |
| 分区算法 | 电梯**责任区内**的目标 |

**检查清单**：
- [ ] 算法名称是SCAN/LOOK吗？ → `_find_next_target`应返回max/min（端点）
- [ ] 算法名称是FCFS吗？ → 应按时间排序
- [ ] 算法名称是最近优先吗？ → 应返回距离最小的

---

### 陷阱3：电梯变idle后不主动寻找任务 🔥

**问题描述**：
电梯完成所有任务变idle后，只是设置状态，不主动寻找新任务。

**❌ 错误实现**：
```python
def on_elevator_stopped(self, elevator, floor):
    next_target = self._find_next_target(...)

    if next_target:
        elevator.go_to_floor(next_target)
    else:
        # 没有任务了，变idle
        self.elevator_direction[elevator.id] = "idle"
        # ❌ 没有调用分配函数
```

**实际后果**：
```
Tick 200: E0完成所有任务，变idle，停在F10
         F15有2位乘客在等待（最后几位）
         E0: idle, 不动

Tick 201-300: F15的乘客继续等待...
             直到 on_event_execute_end 才可能分配
             但如果模拟即将结束，这2位乘客永远等不到
```

**✅ 正确实现**：
```python
def on_elevator_stopped(self, elevator, floor):
    next_target = self._find_next_target(...)

    if next_target:
        elevator.go_to_floor(next_target)
    else:
        # 没有任务了，变idle
        self.elevator_direction[elevator.id] = "idle"
        # ✅ 立即尝试分配新任务
        self._assign_call_to_idle_elevator()
```

**额外建议**：
也在 `on_elevator_idle()` 中调用分配函数：
```python
def on_elevator_idle(self, elevator):
    self.elevator_direction[elevator.id] = "idle"
    # ✅ 尝试分配任务
    self._assign_call_to_idle_elevator()
```

**检查清单**：
- [ ] `on_elevator_stopped` 中是否在变idle时调用分配？
- [ ] `on_elevator_idle` 中是否调用分配？
- [ ] `on_passenger_call` 中是否调用分配（给空闲电梯）？

---

### 陷阱4：忘记在内部目标集合中包含车内乘客目的地 🔥

**问题描述**：
`_find_next_target()` 只考虑外部呼叫，不考虑车内乘客的目的地。

**❌ 错误实现**：
```python
def _find_next_target(self, elevator, current_floor, direction):
    # ❌ 只看外部呼叫
    external_calls = {floor for floor, passengers in self.waiting_up.items() if passengers}

    if direction == "up":
        return max([f for f in external_calls if f > current_floor])

    # 问题：车内有乘客要去F19，但如果F19没有外部呼叫
    #      _find_next_target不会返回F19
    #      乘客无法下车！
```

**✅ 正确实现**：
```python
def _find_next_target(self, elevator, current_floor, direction):
    # ✅ 同时考虑内部和外部目标
    internal = self.internal_targets[elevator.id]  # 车内乘客目的地
    external = {floor for floor, passengers in self.waiting_up.items() if passengers}

    all_possible_stops = internal | external

    if direction == "up":
        return max([f for f in all_possible_stops if f > current_floor])
```

**维护internal_targets**：
```python
def on_passenger_board(self, elevator, passenger):
    # ✅ 乘客上车时添加目的地
    self.internal_targets[elevator.id].add(passenger.destination)

def on_elevator_stopped(self, elevator, floor):
    # ✅ 电梯停靠时移除该楼层（乘客已下车）
    self.internal_targets[elevator.id].discard(floor.floor)
```

**检查清单**：
- [ ] `_find_next_target` 是否包含 `internal_targets`？
- [ ] `on_passenger_board` 是否添加目的地到 `internal_targets`？
- [ ] `on_elevator_stopped` 是否从 `internal_targets` 移除当前楼层？

---

## 推荐的算法结构

### 最小可行算法模板

```python
from typing import List, Dict, Set, Optional
from .base_algorithm import BaseAlgorithm

class MyAlgorithm(BaseAlgorithm):
    def __init__(self, server_url: str = "http://127.0.0.1:8000", enable_logging: bool = True):
        super().__init__(server_url, enable_logging)

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """初始化"""
        super().on_init(elevators, floors)

        # 算法特定的状态
        self.elevator_direction: Dict[int, str] = {e.id: "idle" for e in elevators}
        self.internal_targets: Dict[int, Set[int]] = {e.id: set() for e in elevators}

        # ❌ 不要：self.assigned_calls = set()

    def on_passenger_call(self, passenger, floor, direction):
        """乘客呼叫"""
        # 记录到waiting队列（BaseAlgorithm已提供）
        # ✅ 立即尝试分配空闲电梯
        self._assign_call_to_idle_elevator()

    def on_passenger_board(self, elevator, passenger):
        """乘客上车"""
        # ✅ 记录内部目标
        self.internal_targets[elevator.id].add(passenger.destination)

    def on_elevator_stopped(self, elevator, floor):
        """电梯停靠"""
        floor_num = floor.floor

        # ✅ 移除内部目标
        self.internal_targets[elevator.id].discard(floor_num)

        # ✅ 决策下一站
        next_target = self._find_next_target(elevator, floor_num)

        if next_target:
            elevator.go_to_floor(next_target)
        else:
            self.elevator_direction[elevator.id] = "idle"
            # ✅ 立即尝试分配
            self._assign_call_to_idle_elevator()

    def on_elevator_idle(self, elevator):
        """电梯空闲"""
        self.elevator_direction[elevator.id] = "idle"
        # ✅ 尝试分配任务
        self._assign_call_to_idle_elevator()

    def _find_next_target(self, elevator, current_floor) -> Optional[int]:
        """找到下一个目标 - 根据算法逻辑实现"""
        # ✅ 同时考虑内部和外部
        internal = self.internal_targets[elevator.id]
        external = self._get_external_calls()

        all_targets = internal | external

        # 根据算法类型选择目标
        # SCAN: 返回方向上的最远点
        # FCFS: 返回最早呼叫
        # 等等...
        return self._select_target(all_targets, current_floor)

    def _assign_call_to_idle_elevator(self):
        """分配呼叫给空闲电梯"""
        idle_elevators = [e for e in self.elevators if self.elevator_direction[e.id] == 'idle']

        # ❌ 不要：if floor not in self.assigned_calls
        # ✅ 要：只要有人等待，就尝试分配
        for floor, passengers in self.waiting_up.items():
            if passengers and idle_elevators:
                # 找最近的电梯
                best_elevator = min(idle_elevators, key=lambda e: abs(e.current_floor - floor))
                best_elevator.go_to_floor(floor)
                self.elevator_direction[best_elevator.id] = "up"
                idle_elevators.remove(best_elevator)
```

---

## 测试检查清单

实现算法后，用以下场景测试：

### 测试1：1楼大量乘客
```
场景：F0有100个乘客上行，5台电梯
期望：所有5台电梯都工作
检查：是否只有1台电梯在动？ → assigned_calls问题
```

### 测试2：最后几位乘客
```
场景：小规模场景，160个乘客
期望：100%完成率，最后一位乘客也能到达
检查：是否有乘客卡在电梯里？ → internal_targets问题
```

### 测试3：大规模压力测试
```
场景：large_morning_rush，320个乘客
期望：无电梯卡住，所有电梯持续工作
检查：是否有电梯长时间idle？ → 分配机制问题
```

### 测试4：多楼层分布
```
场景：乘客分布在多个楼层
期望：电梯合理分配，不扎堆
检查：是否所有电梯都去同一楼层？ → 分配策略问题
```

---

## 调试技巧

### 1. 添加详细日志

```python
def on_elevator_stopped(self, elevator, floor):
    print(f"[TICK {self.current_tick}] E{elevator.id} stopped at F{floor.floor}")
    print(f"  Internal targets: {self.internal_targets[elevator.id]}")
    print(f"  Waiting up: {[(f, len(p)) for f, p in self.waiting_up.items() if p]}")
    print(f"  Direction: {self.elevator_direction[elevator.id]}")
```

### 2. 检查不变量

```python
def _validate_state(self):
    """验证算法状态的一致性"""
    # 检查1：internal_targets中的楼层应该是有效的
    for elevator_id, targets in self.internal_targets.items():
        for floor in targets:
            assert 0 <= floor < self.num_floors, f"Invalid internal target: {floor}"

    # 检查2：waiting队列中的乘客应该还在等待
    for floor, passengers in self.waiting_up.items():
        for pid in passengers:
            # 验证乘客确实在等待...
            pass
```

### 3. 可视化电梯状态

```python
def print_elevator_status(self):
    """打印所有电梯的状态"""
    print(f"\n{'='*60}")
    print(f"TICK {self.current_tick} - Elevator Status")
    print(f"{'='*60}")
    for e in self.elevators:
        status = f"E{e.id}: F{e.current_floor} "
        status += f"[{self.elevator_direction[e.id]}] "
        status += f"→{e.target_floor} "
        status += f"Load:{len(e.passengers)}/{e.max_capacity} "
        status += f"Targets:{self.internal_targets[e.id]}"
        print(status)
```

---

## 常见问题FAQ

### Q: 为什么我的电梯一直在两个楼层间来回？
A: 检查是否使用了"踢一脚"机制。移除它，信任模拟器的自动boarding。

### Q: 为什么只有第一台电梯在工作？
A: 检查是否使用了 `assigned_calls: Set[int]`。考虑移除或改为更智能的分配。

### Q: 为什么车内乘客无法到达目的地？
A: 检查 `_find_next_target` 是否包含了 `internal_targets`。

### Q: 为什么大规模场景会卡住？
A: 检查电梯变idle时是否立即调用了 `_assign_call_to_idle_elevator()`。

### Q: 我的SCAN算法为什么不像SCAN？
A: 检查 `_find_next_target` 是否返回 `max()`（上行）或 `min()`（下行），而不是最近的。

---

## 总结

关键要点：
1. ✅ **移除assigned_calls按楼层标记**，或改为智能分配
2. ✅ **目标选择要符合算法本质**（SCAN→端点，FCFS→最早）
3. ✅ **idle时立即分配任务**
4. ✅ **包含internal_targets**在目标选择中
5. ✅ **信任模拟器的自动boarding**

遵循这些原则，你的算法将能够：
- 高效利用所有电梯
- 确保所有乘客到达目的地
- 在大规模场景下不卡住
- 符合算法的理论设计

---

最后更新：2025-10-18
基于：base_scan算法的完整调试经验
