#!/usr/bin/env python3
"""
SCAN Elevator Scheduling Algorithm Implementation
by [Your Name/Team Name]
"""
## todo 还是应该衡量一下根据score派哪个电梯去，否则会出现上行高峰，刚开始停在0楼，但凡有人在高楼按了以后，都会马上空载上楼，尽管有电梯正在上行中

# -----------------------------------------------------------------------------
# 1. 导入 (Imports)
# -----------------------------------------------------------------------------
# 从框架中导入我们编写算法所需的所有核心工具和数据模型。
from typing import List, Dict, Set, Optional

from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import SimulationEvent
from .base_algorithm import BaseAlgorithm


# -----------------------------------------------------------------------------
# 2. 算法主类 (Algorithm Class)
# -----------------------------------------------------------------------------
# 我们创建一个名为 ScanController 的新类，它继承自框架提供的 ElevatorController。
# 这意味着我们的类自动拥有了 start(), stop() 等方法，我们只需要专注于实现事件回调。
class ScanController(BaseAlgorithm):
    """
    SCAN 算法控制器 (也常被称为电梯寻道算法)。

    核心思想:
    1.  **主方向**: 每部电梯都有一个主服务方向 (`up`, `down`, `idle`)。
    2.  **服务到底**: 电梯会沿着其主方向一直运行，直到该方向上再也没有任何请求（无论是接客还是送客）。
    3.  **端点掉头**: 当一个方向上的所有任务都完成后，电梯会掉头，开始为反方向服务。
    4.  **智能分配**: 新的乘客请求会被分配给最“合适”的电梯（空闲的，或正好顺路的）。
    """
    def __init__(self, server_url: str = "http://127.0.0.1:8000", enable_logging: bool = True):
        super().__init__(server_url, enable_logging)
    # -------------------------------------------------------------------------
    # 3. 初始化 (on_init)
    # -------------------------------------------------------------------------
    # on_init 是我们算法的构造函数，在模拟开始时仅调用一次。
    # 我们在这里准备好所有用于记录和决策所需的数据结构（我们的“小本本”）。
    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """
        初始化算法所需的所有数据结构。
        """
        print("--- SCAN Algorithm Initialized ---")
        self.elevators = elevators
        self.floors = floors
        self.num_floors = len(floors)

        # --- 核心数据结构 ---

        # a. 电梯的主方向记录 (逻辑状态)
        #    记录我们为每部电梯规划的宏观方向。
        self.elevator_direction: Dict[int, str] = {e.id: "idle" for e in elevators}

        # b. 全局外部呼叫记录 (公共任务池)
        #    记录所有楼层上还未被电梯接走的乘客请求。
        self.waiting_up: Dict[int, Set[int]] = {f.floor: set() for f in floors}
        self.waiting_down: Dict[int, Set[int]] = {f.floor: set() for f in floors}

        # c. 电梯的内部目标记录 (私有任务列表)
        #    只记录每部电梯内部乘客的目的地。
        self.internal_targets: Dict[int, Set[int]] = {e.id: set() for e in elevators}

        #用于记录已经被指派给某部空闲电梯，但电梯尚未到达的楼层呼叫
        self.assigned_calls: Set[int] = set()
        self.BYPASS_THRESHOLD = 0.8

        # 场景识别相关
        self.peak_mode: str = "unknown"  # "up_peak", "down_peak", "mixed", "unknown"
        self.pattern_detection_tick = 50  # 在第50个tick进行场景识别
        self.pattern_detected = False

    # -------------------------------------------------------------------------
    # 4. 核心事件处理 (Event Handlers)
    # -------------------------------------------------------------------------
    def on_event_execute_start(
            self, tick: int, events: List[SimulationEvent],
            elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """Handle event execution start - override if needed"""
        print(f"Tick {tick}: 即将处理 {len(events)} 个事件 {[e.type.value for e in events]}")
        for i in elevators:
            print(f"\t{i.id}[{i.target_floor_direction.value},{i.current_floor_float}/{i.target_floor}]" + "👦" * len(
                i.passengers), end="")
        print()
        pass

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """
        处理新的乘客呼叫请求。
        职责：记录请求，并尝试指派一部空闲的电梯。
        """
        floor_num = floor.floor
        print(f"--- Passenger Call (Tick {self.current_tick}) ---")
        print(f"  > Passenger {passenger.id} at floor {floor_num} requests {direction.upper()}.")

        # 1. 记录请求到全局任务池
        if direction == "up":
            self.waiting_up[floor_num].add(passenger.id)
        else:
            self.waiting_down[floor_num].add(passenger.id)

        # 2. 尝试将此任务分配给一部空闲的电梯
        # self._assign_call_to_idle_elevator()

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """
        处理乘客上电梯事件。
        职责：将乘客的目的地加入电梯的“内部目标”，并从“公共任务池”中移除该请求。
        """
        elevator_id = elevator.id
        origin_floor = passenger.origin
        destination = passenger.destination
        print(f"--- Passenger Board (Tick {self.current_tick}) ---")
        print(f"  > P{passenger.id} ({origin_floor}->{destination}) boarded E{elevator_id}.")

        # 1. 将乘客的目的地添加到电梯的内部目标集合
        self.internal_targets[elevator_id].add(destination)

        # 2. 从全局等待队列中移除已被服务的请求
        if passenger.travel_direction.value == "up":
            self.waiting_up[origin_floor].discard(passenger.id)
        else:
            self.waiting_down[origin_floor].discard(passenger.id)

        print(f"  > E{elevator_id} internal targets are now: {self.internal_targets[elevator_id]}")
        self.assigned_calls.discard(origin_floor)

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """
        【SCAN算法核心】处理电梯停靠事件。
        职责：处理下客和接客，并根据SCAN逻辑决定电梯的下一个目标。
        """
        floor_num = floor.floor
        elevator_id = elevator.id
        current_direction = self.elevator_direction[elevator_id]
        #耐心等待
        is_waiting_for_pickup = False
        if current_direction == "up" and self.waiting_up[floor_num]:
            is_waiting_for_pickup = True
        elif current_direction == "down" and self.waiting_down[floor_num]:
            is_waiting_for_pickup = True

        if is_waiting_for_pickup:
            ########## 改进 START：加入“打破平局”逻辑 ##########
            #
            # **改动**: 在决定启动接客前，增加一个仲裁机制。
            # **原因**: 解决多部电梯同时到达同一楼层，并同时尝试服务同一个呼叫的竞态条件。
            #         通过ID号进行仲裁，确保只有一个电梯会响应，避免其他电梯空载运行。
            #
            # 1. 找出所有“竞争者”：当前也停在这一层的其他电梯
            competitors = [e for e in self.elevators if
                           int(e.current_floor) == floor_num and e.target_floor_direction.value == "stopped"]

            # 2. 如果只有一个电梯（就是自己），或者自己的ID是竞争者中最小的，则自己负责接客
            if len(competitors) == 1 or elevator.id == min(e.id for e in competitors):
                print(f"  > E{elevator_id} will handle pickup at F{floor_num}. Kicking start to trigger boarding.")
                self.assigned_calls.discard(floor_num)

                # 向呼叫方向移动一层楼来“启动”电梯
                next_floor = floor_num + 1 if current_direction == "up" else floor_num - 1
                if 0 <= next_floor < self.num_floors:
                    elevator.go_to_floor(next_floor)
            else:
                # 3. 如果自己的ID不是最小的，则“礼让”，进入空闲状态
                winner_id = min(e.id for e in competitors)
                print(f"  > E{elevator_id} yields pickup at F{floor_num} to E{winner_id}. Becoming idle.")
                self.elevator_direction[elevator_id] = "idle"

            # 无论输赢，决策都已完成，直接返回
            return
            ########## 改进 END ##########
        ########## 检测代码 START (精确版) ##########
        #
        # **功能**: 检测乘客因电梯空间不足而无法上电梯的情况（预测）
        # **逻辑**: 当电梯停下时，我们计算出电梯的剩余可用空间，并获取当前楼层同方向的等候人数。
        #         如果“可用空间”小于“等候人数”，就可以预测将有乘客被留下。
        #
        waiting_passengers_count = 0
        # elevator_capacity = int(elevator.max_capacity * (1 - elevator.load_factor))
        if current_direction == "up" and self.waiting_up[floor_num]:
            waiting_passengers_count = len(self.waiting_up[floor_num])
        elif current_direction == "down" and self.waiting_down[floor_num]:
            waiting_passengers_count = len(self.waiting_down[floor_num])

        # 只有在有人等待时才需要判断
        if waiting_passengers_count > 0:
            available_space = elevator.max_capacity - len(elevator.passengers)

            if available_space < waiting_passengers_count:
                passengers_left_behind = waiting_passengers_count - available_space
                print(
                    f"  🔥 ALERT: E{elevator_id} at F{floor_num} has {available_space} space(s) for {waiting_passengers_count} waiting passenger(s).")
                print(f"           > Predicting {passengers_left_behind} passenger(s) will be left behind!")
        ###停止检测
        print(f"--- Elevator Stopped (Tick {self.current_tick}) ---")
        print(f"  > E{elevator_id} stopped at {floor_num}. Main direction: {current_direction}.")
        self.assigned_calls.discard(floor_num)

        # 1. 处理下客 (从内部目标移除)
        self.internal_targets[elevator_id].discard(floor_num)

        # 2. 处理同向接客 (由模拟器自动完成，我们只需做决策)
        #    如果停靠是为了接人，on_passenger_board 会处理后续

        # 3. 决策下一站
        next_target = self._find_next_target(elevator, floor_num, current_direction)

        if next_target is not None:
            # a. 如果当前方向还有任务，继续前进
            print(f"  > Decision: Continue {current_direction} to next target: {next_target}.")
            elevator.go_to_floor(next_target)
            if current_direction == "up" and len(self.waiting_up.get(floor_num, set())) <= (
                    1 - elevator.load_factor) * elevator.max_capacity:
                self.assigned_calls.add(next_target)
            elif current_direction == "down" and len(self.waiting_down.get(floor_num, set())) <= (
                    1 - elevator.load_factor) * elevator.max_capacity:
                self.assigned_calls.add(next_target)
        else:
            # b. 如果当前方向没任务了，尝试掉头
            opposite_direction = "down" if current_direction == "up" else "up"
            next_target_after_turn = self._find_next_target(elevator, floor_num, opposite_direction)

            if next_target_after_turn is not None:
                # 如果反向有任务，则更新方向并前往
                print(
                    f"  > Decision: No more {current_direction} targets. Reversing to {opposite_direction} for target {next_target_after_turn}.")
                self.elevator_direction[elevator_id] = opposite_direction
                elevator.go_to_floor(next_target_after_turn)
                if opposite_direction == "up" and len(self.waiting_up.get(floor_num, set())) <= (
                        1 - elevator.load_factor) * elevator.max_capacity:
                    self.assigned_calls.add(next_target)
                elif opposite_direction == "down" and len(self.waiting_down.get(floor_num, set())) <= (
                        1 - elevator.load_factor) * elevator.max_capacity:
                    self.assigned_calls.add(next_target)
            else:
                # c. 如果所有方向都没有任务了，进入空闲
                print(f"  > Decision: No targets in any direction. E{elevator_id} will become idle.")
                self.elevator_direction[elevator_id] = "idle"

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """
        处理电梯空闲事件。
        职责：为完全空闲的电梯寻找一个新的任务起点。
        """
        print(f"--- Elevator Idle (Tick {self.current_tick}) ---")
        print(f"  > E{elevator.id} at floor {elevator.current_floor} is now idle.")

        # 确保逻辑状态也更新为空闲
        self.elevator_direction[elevator.id] = "idle"

        # 尝试分配一个新任务
        # self._assign_call_to_idle_elevator()

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """
        处理电梯即将到达楼层事件，用于动态决策是否需要中途停靠。
        """
        floor_num = floor.floor
        elevator_id = elevator.id
        main_direction = self.elevator_direction[elevator_id]

        # 确保物理方向和逻辑方向一致
        if main_direction != direction:
            return

        # 决策1: 是否需要下客？
        if floor_num in self.internal_targets[elevator_id]:
            print(f"  > Approaching Decision: E{elevator_id} must stop at {floor_num} for passenger drop-off.")
            elevator.go_to_floor(floor_num, immediate=True)
            return

        # --- 决策优先级 2: 是否因满载而忽略外部呼叫？ ---
        # 如果电梯负载超过阈值，则不考虑接客，继续前往最终目的地。
        if elevator.load_factor >= self.BYPASS_THRESHOLD:
            # 确认当前楼层有呼叫，才打印忽略信息，避免不必要的日志
            is_call_waiting = (direction == "up" and self.waiting_up[floor_num]) or \
                              (direction == "down" and self.waiting_down[floor_num])
            if is_call_waiting:
                print(
                    f"  > Approaching Decision: E{elevator_id} is nearly full (load: {elevator.load_factor:.0%}). "
                    f"Bypassing pickup at F{floor_num}.")
            return  # 决策完成，不接客，函数结束

        # 决策3: 是否可以顺路接客？
        # 条件：电梯未满，且该楼层有同方向的、未被分配的请求
        should_pickup = False
        if elevator.load_factor < 1.0 and floor_num not in self.assigned_calls:
            if direction == "up" and self.waiting_up[floor_num]:
                should_pickup = True
            elif direction == "down" and self.waiting_down[floor_num]:
                should_pickup = True

        if should_pickup:
            print(f"  > Approaching Decision: E{elevator_id} will stop at {floor_num} for on-the-way pickup.")
            elevator.go_to_floor(floor_num, immediate=True)

    def on_event_execute_end(self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator],
                             floors: List[ProxyFloor]) -> None:
        # -------------------------------------------------------------------------
        # 【Tick 0 死锁检测和修复】
        # -------------------------------------------------------------------------
        # 问题：elevator-saga 的 tick 只在有电梯移动时推进
        # 如果 tick 0 时所有电梯都 stopped，tick 永远无法前进
        # 解决：在 tick 0 且无事件时，检测并启动电梯
        if tick == 0 and len(events) == 0:
            # 检查是否所有电梯都处于 stopped 状态
            all_stopped = all(
                e.target_floor_direction.value == "stopped"
                for e in elevators
            )

            if all_stopped and self.num_floors > 1:
                print("[KICKSTART] Tick 0 deadlock detected - activating elevators...")
                for i, elevator in enumerate(elevators):
                    # 将电梯分散到不同楼层
                    target_floor = min((i + 1) * 2, self.num_floors - 1)
                    elevator.go_to_floor(target_floor)
                    print(f"  > E{elevator.id} → F{target_floor} (kickstart)")
                # Kickstart 完成后直接返回，不执行正常分配逻辑
                return

        # -------------------------------------------------------------------------
        # 正常的事件处理逻辑
        # -------------------------------------------------------------------------

        # 在指定tick进行场景识别
        if tick >= self.pattern_detection_tick and not self.pattern_detected:
            self._detect_traffic_pattern()

        # 为空闲电梯分配任务
        self._assign_call_to_idle_elevator()

    # -------------------------------------------------------------------------
    # 5. 辅助函数 (Helper Functions)
    # -------------------------------------------------------------------------
    # 这些以下划线开头的方法是我们的内部工具，用来帮助主回调函数做决策。

    def _detect_traffic_pattern(self) -> None:
        """
        分析流量模式，识别高峰场景类型
        基于已完成的乘客流量判断是上行高峰、下行高峰还是混合场景
        """
        if self.pattern_detected:
            return

        # 统计所有等待乘客的流向
        up_count = 0
        down_count = 0
        inter_floor_count = 0  # 楼层间移动（非到达底层或顶层）

        # 统计等待队列中的乘客流向
        for floor_num in range(self.num_floors):
            # 上行队列
            for passenger_id in self.waiting_up.get(floor_num, set()):
                up_count += 1
                # 如果是从底层（0-2）出发，更可能是上行高峰
                if floor_num <= 2:
                    up_count += 0.5

            # 下行队列
            for passenger_id in self.waiting_down.get(floor_num, set()):
                down_count += 1
                # 如果是从高层出发到底层，更可能是下行高峰
                if floor_num >= self.num_floors - 3:
                    down_count += 0.5

        total = up_count + down_count
        if total == 0:
            return  # 没有足够数据，延迟判断

        # 判断场景类型
        up_ratio = up_count / total
        down_ratio = down_count / total

        if up_ratio >= 0.7:
            self.peak_mode = "up_peak"
            print(f"\n🔍 [场景识别] 检测到上行高峰模式 (上行占比: {up_ratio:.1%})")
        elif down_ratio >= 0.7:
            self.peak_mode = "down_peak"
            print(f"\n🔍 [场景识别] 检测到下行高峰模式 (下行占比: {down_ratio:.1%})")
        else:
            self.peak_mode = "mixed"
            print(f"\n🔍 [场景识别] 检测到混合场景 (上行:{up_ratio:.1%}, 下行:{down_ratio:.1%})")

        self.pattern_detected = True

    def _can_elevator_handle_on_the_way(self, elevator: ProxyElevator, floor: int, direction: str) -> bool:
        """
        判断一个工作中的电梯是否可以顺路处理某个呼叫

        条件：
        1. 电梯主方向与呼叫方向一致
        2. 电梯会经过该楼层（在当前位置和最远目标之间）
        3. 电梯未满载（load_factor < BYPASS_THRESHOLD）

        Args:
            elevator: 要检查的电梯
            floor: 呼叫楼层
            direction: 呼叫方向 ("up" or "down")

        Returns:
            True 如果电梯可以顺路处理该呼叫
        """
        elevator_id = elevator.id
        main_direction = self.elevator_direction[elevator_id]

        # 条件1: 方向必须一致
        if main_direction != direction:
            return False

        # 电梯必须是工作状态（非空闲）
        if main_direction == "idle":
            return False

        # 条件3: 电梯负载不能太高
        if elevator.load_factor >= self.BYPASS_THRESHOLD:
            return False

        # 条件2: 判断呼叫楼层是否在电梯的路径上
        targets = self.internal_targets[elevator_id].copy()

        if not targets:
            # 没有内部目标，无法判断路径
            return False

        current_floor = elevator.current_floor

        if main_direction == "up":
            # 上行：呼叫楼层应该在当前位置和最远目标之间
            max_target = max(targets)
            is_on_path = current_floor < floor <= max_target

            if is_on_path:
                print(f"    [顺路分析] E{elevator_id}上行(F{current_floor}→F{max_target})会经过F{floor}")
            return is_on_path

        else:  # down
            # 下行：呼叫楼层应该在最近目标和当前位置之间
            min_target = min(targets)
            is_on_path = min_target <= floor < current_floor

            if is_on_path:
                print(f"    [顺路分析] E{elevator_id}下行(F{current_floor}→F{min_target})会经过F{floor}")
            return is_on_path

    def _calculate_assignment_score(self, elevator: ProxyElevator, floor: int, heatmap: Dict[int, int]) -> float:
        """
        计算电梯-楼层配对的综合评分

        评分考虑因素：
        1. 热力值（等待人数）- 权重最高
        2. 距离惩罚
        3. 场景适应性加成（上行/下行高峰的位置优势）
        4. 电梯空载加成

        Returns:
            综合评分，分数越高越优先
        """
        heat = heatmap[floor]
        distance = abs(elevator.current_floor - floor)

        # 基础分：热力值（权重最高）
        # 每个等待乘客贡献100分
        score = heat * 100

        # 距离惩罚：每层楼扣10分
        score -= distance * 10

        # 场景适应性加成
        if self.peak_mode == "up_peak":
            # 上行高峰：优先使用底层区域(0-2层)的空闲电梯
            if elevator.current_floor <= 2:
                score += 25
                print(f"    [评分] E{elevator.id}在底层(F{elevator.current_floor})，上行高峰加成+25")
            # 如果电梯在目标楼层下方，顺路优势
            if elevator.current_floor < floor:
                score += 10

        elif self.peak_mode == "down_peak":
            # 下行高峰：优先使用高层区域的空闲电梯
            high_floor_threshold = self.num_floors - 3
            if elevator.current_floor >= high_floor_threshold:
                score += 25
                print(f"    [评分] E{elevator.id}在高层(F{elevator.current_floor})，下行高峰加成+25")
            # 如果电梯在目标楼层上方，顺路优势
            if elevator.current_floor > floor:
                score += 10

        # 空载加成：完全空的电梯更优先
        if elevator.load_factor == 0:
            score += 15
            print(f"    [评分] E{elevator.id}空载，加成+15")

        return score

    def _assign_call_to_idle_elevator(self):
        """
        扫描所有空闲电梯和所有待处理请求，进行最优匹配。
        【智能评分策略】：基于热力图、距离、场景特征和电梯状态进行综合评分。

        评分因素：
        1. 热力值（等待人数）- 权重最高 (100分/人)
        2. 距离惩罚 (-10分/层)
        3. 场景适应性加成 (+25分，根据上行/下行高峰调整)
        4. 空载加成 (+15分)
        """
        # 使用循环，因为在一个tick中我们可能需要进行多次分配
        while True:
            # 0. 【顺路优化】检查工作中的电梯是否可以顺路处理呼叫
            working_elevators = [e for e in self.elevators if self.elevator_direction[e.id] != 'idle']

            # 收集所有未分配呼叫
            all_unassigned_calls = set()
            for floor_num, passengers in self.waiting_up.items():
                if passengers and floor_num not in self.assigned_calls:
                    all_unassigned_calls.add(floor_num)
            for floor_num, passengers in self.waiting_down.items():
                if passengers and floor_num not in self.assigned_calls:
                    all_unassigned_calls.add(floor_num)

            # 识别可被顺路处理的呼叫
            calls_to_skip = set()
            for floor in all_unassigned_calls:
                # 判断该楼层的呼叫方向
                if self.waiting_up.get(floor):
                    call_direction = "up"
                elif self.waiting_down.get(floor):
                    call_direction = "down"
                else:
                    continue  # 没有等待乘客，跳过

                # 查找可顺路的工作电梯
                for elevator in working_elevators:
                    if self._can_elevator_handle_on_the_way(elevator, floor, call_direction):
                        calls_to_skip.add(floor)
                        print(f"  > 【顺路优化】F{floor}将由E{elevator.id}顺路接客，不派遣空闲电梯")
                        break  # 找到一个即可，不需要继续

            # 从未分配列表中移除可顺路处理的呼叫
            all_unassigned_calls -= calls_to_skip

            # 1. 寻找资源：哪些电梯空闲？还有哪些呼叫需要空闲电梯？
            idle_elevators = [e for e in self.elevators if self.elevator_direction[e.id] == 'idle']

            # 2. 如果没有空闲电梯或没有新请求，则分配结束
            if not idle_elevators or not all_unassigned_calls:
                if not idle_elevators and all_unassigned_calls:
                    print(
                        f"  > Assignment loop finished: No idle elevators available for {len(all_unassigned_calls)} call(s).")
                elif not all_unassigned_calls and idle_elevators:
                    print(
                        f"  > Assignment loop finished: No unassigned calls for {len(idle_elevators)} idle elevator(s).")
                elif not idle_elevators and not all_unassigned_calls:
                    print(f"  > Assignment loop finished: No idle elevators and no unassigned calls.")
                break

            # 3. 【热力图+智能评分策略】寻找最优匹配
            # 计算每个楼层的热力值（等待人数）
            floor_heatmap = {}
            for floor in all_unassigned_calls:
                heat = len(self.waiting_up.get(floor, set())) + len(self.waiting_down.get(floor, set()))
                floor_heatmap[floor] = heat

            best_elevator = None
            best_floor = -1
            best_score = float('-inf')  # 使用综合评分

            # 遍历所有电梯-楼层组合，计算综合评分
            for elevator in idle_elevators:
                for floor in all_unassigned_calls:
                    score = self._calculate_assignment_score(elevator, floor, floor_heatmap)

                    if score > best_score:
                        best_score = score
                        best_elevator = elevator
                        best_floor = floor

            # 4. 如果找到了匹配，则执行分配
            if best_elevator is not None:
                elevator_to_assign = best_elevator
                target_floor = best_floor
                heat = floor_heatmap[best_floor]
                distance = abs(best_elevator.current_floor - best_floor)

                print(
                    f"  > 【智能分配】: E{elevator_to_assign.id} → F{target_floor} "
                    f"(评分={best_score:.1f}, 热力={heat}人, 距离={distance}层, 模式={self.peak_mode})")

                # 5. 立即更新状态，为下一次循环（如果需要）做准备

                self.assigned_calls.add(target_floor)

                if target_floor > elevator_to_assign.current_floor:
                    self.elevator_direction[elevator_to_assign.id] = "up"
                elif target_floor < elevator_to_assign.current_floor:
                    self.elevator_direction[elevator_to_assign.id] = "down"
                else:  # 如果电梯恰好就在呼叫楼层
                    # 确定一个初始方向，优先响应同向请求
                    print(f"  > Assignment: E{elevator_to_assign.id} is already at call floor {target_floor}.")
                    if self.waiting_up[target_floor]:
                        self.elevator_direction[elevator_to_assign.id] = "up"
                        target_floor = best_elevator.current_floor + 1
                    else:
                        self.elevator_direction[elevator_to_assign.id] = "down"
                        target_floor = best_elevator.current_floor - 1
                if 0 <= target_floor < len(self.floors):
                    elevator_to_assign.go_to_floor(target_floor)
                else:
                    # 如果在顶层或底层无法移动，这是个极端情况。
                    # 此时电梯无法移动，但我们已将其逻辑状态设为活动，避免在下一轮被重复指派。
                    # 乘客依然可能无法上梯，但这已是当前框架下的最优处理。
                    pass


            else:
                # 理论上不会到这里，但作为安全出口
                break

    def _find_next_target(self, elevator: ProxyElevator, current_floor: int, direction: str) -> Optional[int]:
        """
        【已修正】在指定方向上为电梯寻找最合适的下一个停靠点。
        """
        elevator_id = elevator.id

        # 1. 收集所有可能的停靠点
        internal = self.internal_targets[elevator_id]

        # 【核心修正】: 不再只看同向请求，而是看所有楼层的请求，以找到真正的端点
        all_up_calls = {floor for floor, passengers in self.waiting_up.items() if passengers and floor not in self.assigned_calls}
        all_down_calls = {floor for floor, passengers in self.waiting_down.items() if passengers and floor not in self.assigned_calls}
        all_external_calls = all_up_calls | all_down_calls

        all_possible_stops = internal | all_external_calls

        # 2. 在指定方向上查找
        if direction == "up":
            # 寻找当前楼层之上的“最远”请求点作为扫描终点
            stops_above = [f for f in all_possible_stops if f > current_floor]
            return min(stops_above) if stops_above else None  # 仍然是去最近的，但现在考虑了所有请求

        elif direction == "down":
            stops_below = [f for f in all_possible_stops if f < current_floor]
            return max(stops_below) if stops_below else None

        return None



    # -------------------------------------------------------------------------
    # 6. 其他未使用的回调 (Unused Callbacks)
    # -------------------------------------------------------------------------
    # 保持这些为空，我们的算法暂时不需要它们。

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        pass

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        pass




