#!/usr/bin/env python3
"""
公交车式电梯调度算法示例
电梯像公交车一样运营，按固定路线循环停靠每一层
"""
from typing import Dict, List

from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import SimulationEvent, Direction


class ElevatorBusController(ElevatorController):
    """
    公交车式电梯调度算法
    电梯像公交车一样按固定路线循环运行，在每层都停
    """

    def __init__(self, server_url: str = "http://127.0.0.1:8000", debug: bool = False):
        """初始化控制器"""
        super().__init__(server_url, debug)
        self.elevator_directions: Dict[int, str] = {}  # 记录每个电梯的当前方向
        self.max_floor = 0  # 最大楼层数

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """初始化公交车式电梯算法"""
        print("🚌 公交车式电梯算法初始化")
        print(f"   管理 {len(elevators)} 部电梯")
        print(f"   服务 {len(floors)} 层楼")
        # 获取最大楼层数
        self.max_floor = len(floors) - 1
        # 初始化每个电梯的方向 - 开始都向上
        for elevator in elevators:
            self.elevator_directions[elevator.id] = "up"
        # 简单的初始分布 - 均匀分散到不同楼层
        for i, elevator in enumerate(elevators):
            # 计算目标楼层 - 均匀分布在不同楼层
            target_floor = (i * (len(floors) + 1)) // len(elevators)
            # 立刻移动到目标位置并开始循环
            elevator.go_to_floor(target_floor, immediate=True)#elevator1 begin moving

    def on_event_execute_start(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """事件执行前的回调"""
        print(f"Tick {tick}: 即将处理 {len(events)} 个事件 {[e.type.value for e in events]}")
        for i in elevators:
            print(f"\t{i.id}[{i.target_floor_direction.value},{i.current_floor_float}/{i.target_floor}]" + "👦" * len(i.passengers), end="")
        print()

    def on_event_execute_end(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        # latest_state = self.api_client.get_state(force_reload=True)
        # all_passengers = latest_state.passengers
        # for passenger_id, passenger_info in all_passengers.items():
        #     # 我们只关心那些还在等待的乘客
        #     if passenger_info.status.value == 'waiting':
        #         print(f"  乘客 P{passenger_info.id}: "
        #               f"  arrive_tick: {passenger_info.arrive_tick}, "
        #               f"  pickup_tick: {passenger_info.pickup_tick}  <-- 在这里观察！")
        #
        # print("--------------------------------------------------\n")
        """事件执行后的回调"""
        # print(f"✅ Tick {tick}: 已处理 {len(events)} 个事件")
        pass

    def on_passenger_call(self, passenger:ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """
        乘客呼叫时的回调
        公交车模式下，电梯已经在循环运行，无需特别响应呼叫
        """
        print(f"乘客 {passenger.id} F{floor.floor} 请求 {passenger.origin} -> {passenger.destination} ({direction})")

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """
        电梯空闲时的回调
        让空闲的电梯继续执行公交车循环路线，每次移动一层楼
        """
        print(f"🛑 电梯 E{elevator.id} 在 F{elevator.current_floor} 层空闲")
        # 设置指示器让乘客知道电梯的行进方向
        if self.elevator_directions[elevator.id] == "down" and elevator.current_floor != 0:
            elevator.go_to_floor(elevator.current_floor - 1, immediate=True)
            # elevator.set_up_indicator(True)
        elevator.go_to_floor(1)
        # current_direction = self.elevator_directions[elevator.id]
        # if current_direction == "up":
        #     elevator.set_up_indicator(True)
        #     elevator.set_down_indicator(False)
        # else:
        #     elevator.set_up_indicator(False)
        #     elevator.set_down_indicator(True)

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """
        电梯停靠时的回调
        公交车模式下，在每一层都停下，然后继续下一站
        需要注意的是，stopped会比idle先触发
        """
        print(f"🛑 电梯 E{elevator.id} 停靠在 F{floor.floor}")
        if self.elevator_directions[elevator.id] == "up" and elevator.current_floor == self.max_floor:
            elevator.go_to_floor(elevator.current_floor - 1, immediate=True)
            self.elevator_directions[elevator.id] = "down"
        elif self.elevator_directions[elevator.id] == "down" and elevator.current_floor == 0:
            elevator.go_to_floor(elevator.current_floor + 1, immediate=True)
            self.elevator_directions[elevator.id] = "up"
        elif self.elevator_directions[elevator.id] == "up":
            # if elevator.id == 0:
            #     raise ValueError("这里故意要求0号电梯不可能触发非两端停止，通过on_elevator_approaching实现")
            elevator.go_to_floor(elevator.current_floor + 1, immediate=True)
        # 这里故意少写下降的情况，用于了解stopped会先于idle触发
        elif self.elevator_directions[elevator.id] == "down":
            elevator.go_to_floor(elevator.current_floor - 1, immediate=True)
            self.elevator_directions[elevator.id] = "down"

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """
        乘客上梯时的回调
        打印乘客上梯信息
        """
        print(
            f" 乘客{passenger.id} E{elevator.id}⬆️ F{elevator.current_floor} -> F{passenger.destination}"
        )

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        """
        乘客下车时的回调
        打印乘客下车信息
        """
        print(f" 乘客{passenger.id} E{elevator.id}⬇️ F{floor.floor}")

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """
        电梯经过楼层时的回调
        打印经过楼层的信息
        """
        print(f"🔄 电梯 E{elevator.id} 经过 F{floor.floor} (方向: {direction})")

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """
        电梯即将到达时的回调 (START_DOWN事件)
        电梯开始减速，即将到达目标楼层
        """
        print(f"🎯 电梯 E{elevator.id} 即将到达 F{floor.floor} (方向: {direction})")
        if elevator.target_floor == floor.floor and elevator.target_floor_direction == Direction.UP:  # 电梯的目标楼层就是即将停靠的楼层
            if elevator.id == 0:  # 这里为了测试，让0号电梯往上一层就新加一层，上行永远不会开门
                elevator.go_to_floor(elevator.target_floor + 1, immediate=True)
                print(f" 不让0号电梯上行停站，设定新目标楼层 {elevator.target_floor + 1}")

if __name__ == "__main__":
    algorithm = ElevatorBusController(debug=True)
    algorithm.start()
