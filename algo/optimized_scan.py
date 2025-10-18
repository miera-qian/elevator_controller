#!/usr/bin/env python3
"""
Optimized SCAN Algorithm

Advanced elevator scheduling algorithm using SCAN algorithm with intelligent scoring.
Goal: Minimize average and P95 passenger wait times.
"""

from typing import List
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from .base_algorithm import BaseAlgorithm


class OptimizedScanAlgorithm(BaseAlgorithm):
    """
    Advanced elevator scheduling algorithm using:
    1. SCAN algorithm (elevator continues in direction until no more requests)
    2. Nearest-neighbor assignment for idle elevators
    3. Load balancing across multiple elevators
    4. Intelligent scoring system for elevator assignment
    """

    def __init__(self, server_url: str = "http://127.0.0.1:8000", enable_logging: bool = True):
        super().__init__(server_url, enable_logging)
        # Track internal targets (passenger destinations in each elevator)
        self.internal_targets = {}

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """Handle new passenger call"""
        floor_num = floor.floor
        passenger_id = passenger.id
        # --- DEBUG PRINT ---
        print(f"--- PASSENGER CALL (Tick: {self.current_tick}) ---")
        print(
            f"  > Passenger {passenger_id} at floor {floor_num} requests to go {direction.upper()}. (Destination: {passenger.destination})")
        print(f"  > Calling _assign_elevator_to_call({floor_num}, {direction})")
        # --- END DEBUG ---

        # Track waiting passenger
        if direction == "up":
            self.waiting_up[floor_num].add(passenger_id)
        else:
            self.waiting_down[floor_num].add(passenger_id)

        # Assign elevator to pick up passenger
        self._assign_elevator_to_call(floor_num, direction)

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """Handle idle elevator by assigning it to nearest waiting passenger"""
        # Find nearest waiting passenger
        best_floor = self._find_nearest_waiting_call(elevator.current_floor)

        if best_floor is not None:
            # 立即设置目标，确保电梯能够启动前往该楼层
            elevator.go_to_floor(best_floor, immediate=True)
            if best_floor not in self.elevator_targets[elevator.id]:
                self.elevator_targets[elevator.id].append(best_floor)

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """
        Decide whether to stop at approaching floor.
        Stop if: passengers need to alight OR passengers waiting in same direction.
        """
        floor_num = floor.floor
        # --- DEBUG PRINT ---
        print(f"--- ELEVATOR APPROACHING (Tick: {self.current_tick}) ---")
        print(f"  > Elevator E{elevator.id} is approaching floor {floor_num} while moving {direction.upper()}.")
        # --- END DEBUG ---
        # Check if any passenger wants to get off at this floor
        # If so, the elevator will automatically stop (handled by simulator)

        # Check if passengers waiting in same direction and add floor as target
        if direction == "up" and self.waiting_up[floor_num]:
            elevator.go_to_floor(floor_num, immediate=True)
        elif direction == "down" and self.waiting_down[floor_num]:
            elevator.go_to_floor(floor_num, immediate=True)

        # If at end of range, also pick up passengers waiting in opposite direction
        if floor_num == self.num_floors - 1 and self.waiting_down[floor_num]:
            elevator.go_to_floor(floor_num, immediate=True)
        elif floor_num == 0 and self.waiting_up[floor_num]:
            elevator.go_to_floor(floor_num, immediate=True)## todo print state when passing

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """Handle elevator stopped at floor"""
        floor_num = floor.floor
        elevator_id = elevator.id

        # --- DEBUG PRINT ---
        print(f"--- ELEVATOR STOPPED (Tick: {self.current_tick}) ---")
        print(f"  > Elevator E{elevator.id} has stopped at floor {floor_num}.")
        # --- END DEBUG ---

        # Remove from targets (both internal and external)
        if floor_num in self.elevator_targets.get(elevator.id, []):
            self.elevator_targets[elevator.id].remove(floor_num)

        # ✅ FIX: Remove from internal targets (passengers alighting)
        self.internal_targets.get(elevator_id, set()).discard(floor_num)

        # ✅ FIX: If elevator has no more tasks, try to assign new ones
        has_internal_targets = bool(self.internal_targets.get(elevator_id))
        has_external_targets = bool(self.elevator_targets.get(elevator_id))

        if not has_internal_targets and not has_external_targets:
            print(f"  > Elevator E{elevator_id} has no more targets, trying to assign new task...")
            # Try to find and assign nearest waiting call
            best_floor = self._find_nearest_waiting_call(elevator.current_floor)
            if best_floor is not None:
                elevator.go_to_floor(best_floor, immediate=True)
                if best_floor not in self.elevator_targets[elevator.id]:
                    self.elevator_targets[elevator.id].append(best_floor)
                print(f"  > Assigned E{elevator_id} to floor {best_floor}")

        # Passengers will be handled automatically by on_passenger_board

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """Handle passenger boarding - register destination and update tracking"""
        floor_num = passenger.origin
        passenger_id = passenger.id
        destination = passenger.destination
        elevator_id = elevator.id

        # Remove from waiting lists
        self.waiting_up[floor_num].discard(passenger_id)
        self.waiting_down[floor_num].discard(passenger_id)

        # ✅ FIX: Add destination to internal_targets
        if elevator_id not in self.internal_targets:
            self.internal_targets[elevator_id] = set()
        self.internal_targets[elevator_id].add(destination)

        # 立即设置目的地（immediate=True），确保电梯能够正确启动
        # 注意：电梯已经停在乘客上梯的楼层，现在需要前往乘客目的地
        elevator.go_to_floor(destination, immediate=True)

        if destination not in self.elevator_targets[elevator.id]:
            self.elevator_targets[elevator.id].append(destination)

        # --- DEBUG PRINT ---
        print(f"--- PASSENGER BOARD (Tick: {self.current_tick}) ---")
        print(f"  > Passenger {passenger_id} has boarded Elevator E{elevator.id} at floor {floor_num}.")
        print(f"  > Their destination is floor {destination}.")
        print(f"  > 立即设置目标 (immediate=True) 确保电梯启动")
        print(f"  > Elevator E{elevator.id}'s target list is now: {self.elevator_targets[elevator.id]}")
        print(f"  > Internal targets: {self.internal_targets[elevator_id]}")
        # --- END DEBUG ---

    # Private helper methods

    def _assign_elevator_to_call(self, floor_num: int, direction: str) -> None:
        """Assign best elevator to handle a call"""
        best_elevator = self._find_best_elevator(floor_num, direction)
        
        print(f"  > _assign_elevator_to_call: best_elevator = {best_elevator}")
        if best_elevator:
            print(f"  > Calling best_elevator.go_to_floor({floor_num}, immediate=True)")
            # 立即设置目标，确保电梯能够正确启动前往该楼层接客
            result = best_elevator.go_to_floor(floor_num, immediate=True)
            print(f"  > go_to_floor returned: {result}")
            if floor_num not in self.elevator_targets[best_elevator.id]:
                self.elevator_targets[best_elevator.id].append(floor_num)
        else:
            print(f"  > No best elevator found!")

    def _find_best_elevator(self, target_floor: int, direction: str) -> ProxyElevator:
        """
        Find best elevator to handle call using scoring system:
        - Prefer elevators already heading in same direction
        - Prefer closer elevators
        - Prefer less loaded elevators
        """
        best_elevator = None
        best_score = float('inf')

        for elevator in self.elevators:
            score = self._score_elevator(elevator, target_floor, direction)

            if score < best_score:
                best_score = score
                best_elevator = elevator

        return best_elevator

    def _score_elevator(self, elevator: ProxyElevator, target_floor: int, direction: str) -> float:
        """
        Score elevator for assignment (lower is better).

        Scoring formula:
        - Base: distance to target floor
        - Penalty: load factor * 10
        - Bonus: direction match (×0.5)
        - Penalty: direction conflict (+20)
        """
        distance = abs(elevator.current_floor - target_floor)
        load_factor = elevator.load_factor

        # Base score is distance
        score = distance

        # Penalize loaded elevators
        score += load_factor * 10

        # Bonus if elevator is already going in right direction and will pass the floor
        elevator_direction = elevator.last_tick_direction
        if elevator_direction == direction:
            if direction == "up" and elevator.current_floor <= target_floor:
                score *= 0.5  # Strong preference
            elif direction == "down" and elevator.current_floor >= target_floor:
                score *= 0.5  # Strong preference

        # Penalty if elevator is going opposite direction
        if elevator_direction == "up" and direction == "down" and elevator.current_floor < target_floor:
            score += 20
        elif elevator_direction == "down" and direction == "up" and elevator.current_floor > target_floor:
            score += 20

        return score

    def _find_nearest_waiting_call(self, current_floor: int) -> int:
        """Find nearest floor with waiting passengers"""
        min_distance = float('inf')
        best_floor = None

        for floor_num in range(self.num_floors):
            if self.waiting_up[floor_num] or self.waiting_down[floor_num]:
                distance = abs(current_floor - floor_num)
                if distance < min_distance:
                    min_distance = distance
                    best_floor = floor_num

        return best_floor
