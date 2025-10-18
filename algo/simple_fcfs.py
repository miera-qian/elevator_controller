#!/usr/bin/env python3
"""
简单的先进先出 (FCFS) 算法
用于测试电梯的基本运动功能
"""

from typing import List, Dict, Set
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from .base_algorithm import BaseAlgorithm


class SimpleFCFSAlgorithm(BaseAlgorithm):
    """
    最简单的电梯调度算法：
    1. 当有乘客叫梯时，分配给最近的空闲电梯
    2. 当乘客上梯后，电梯立即前往其目的地
    3. 没有复杂的优化，只是保证电梯能动起来
    """

    def __init__(self, server_url: str = "http://127.0.0.1:8000", enable_logging: bool = True):
        super().__init__(server_url, enable_logging)
        self.passenger_destinations: Dict[int, int] = {}  # 乘客 -> 目的地映射
        # ✅ FIX: Track internal targets (passenger destinations in each elevator)
        self.internal_targets: Dict[int, Set[int]] = {}

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """乘客按下按钮"""
        floor_num = floor.floor
        
        print(f"\n[ALGO-SIMPLE] 乘客 {passenger.id} 在 F{floor_num} 按下{direction.upper()}按钮 (目的地: F{passenger.destination})")
        
        # 找到最近的电梯
        best_elevator = None
        min_distance = float('inf')
        
        for elevator in self.elevators:
            distance = abs(elevator.current_floor - floor_num)
            if distance < min_distance:
                min_distance = distance
                best_elevator = elevator
        
        if best_elevator:
            print(f"  → 分配给电梯 E{best_elevator.id} (距离: {min_distance} 层)")
            # 立即告诉电梯去这个楼层
            best_elevator.go_to_floor(floor_num, immediate=True)

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """电梯空闲"""
        print(f"\n[ALGO-SIMPLE] 电梯 E{elevator.id} 空闲")
        # ✅ FIX: Try to find nearest waiting passenger and assign
        best_floor = self._find_nearest_waiting_call(elevator.current_floor)
        if best_floor is not None:
            print(f"  → 空闲电梯分配到楼层 {best_floor}")
            elevator.go_to_floor(best_floor, immediate=True)

    def _find_nearest_waiting_call(self, current_floor: int) -> int:
        """找到最近的等待乘客的楼层"""
        min_distance = float('inf')
        best_floor = None

        for floor_num in range(self.num_floors):
            if self.waiting_up[floor_num] or self.waiting_down[floor_num]:
                distance = abs(current_floor - floor_num)
                if distance < min_distance:
                    min_distance = distance
                    best_floor = floor_num

        return best_floor

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯即将经过某层"""
        # 不需要处理
        pass

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """电梯停止"""
        floor_num = floor.floor
        elevator_id = elevator.id

        print(f"\n[ALGO-SIMPLE] 电梯 E{elevator_id} 停止在 F{floor_num}")

        # ✅ FIX: Remove from internal targets (passengers alighting)
        self.internal_targets.get(elevator_id, set()).discard(floor_num)

        # ✅ FIX: If elevator has no more passengers, try to assign new task
        has_internal_targets = bool(self.internal_targets.get(elevator_id))

        if not has_internal_targets:
            print(f"  电梯 E{elevator_id} 没有内部目标，尝试分配新任务...")
            best_floor = self._find_nearest_waiting_call(elevator.current_floor)
            if best_floor is not None:
                print(f"  → 分配到楼层 {best_floor}")
                elevator.go_to_floor(best_floor, immediate=True)

        # 乘客会自动上下梯

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """乘客上梯"""
        destination = passenger.destination
        elevator_id = elevator.id
        floor_num = passenger.origin

        # ✅ FIX: Remove from waiting lists
        self.waiting_up[floor_num].discard(passenger.id)
        self.waiting_down[floor_num].discard(passenger.id)

        # ✅ FIX: Add destination to internal_targets
        if elevator_id not in self.internal_targets:
            self.internal_targets[elevator_id] = set()
        self.internal_targets[elevator_id].add(destination)

        print(f"\n[ALGO-SIMPLE] 乘客 {passenger.id} 上梯 E{elevator.id} (目的地: F{destination})")
        print(f"  电梯状态: floor={elevator.current_floor}, target={elevator.target_floor}, ")
        print(f"           direction={elevator.target_floor_direction.value}, status={elevator.run_status.value}")
        print(f"  内部目标: {self.internal_targets[elevator_id]}")

        # 🔑 关键：设置电梯的目标为乘客的目的地
        # 测试使用 immediate=False，让simulator在下一个tick的_update_elevator_status中处理
        print(f"  → 调用 go_to_floor({destination}, immediate=False)")
        result = elevator.go_to_floor(destination, immediate=False)
        print(f"  → 返回结果: {result}")

        # 记录这个乘客的目的地
        self.passenger_destinations[passenger.id] = destination
