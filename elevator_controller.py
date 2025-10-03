#!/usr/bin/env python3
"""
Optimized Elevator Scheduling Algorithm
Goal: Minimize average and P95 passenger wait times
"""

from typing import List, Dict, Set
from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import SimulationEvent


class OptimizedElevatorController(ElevatorController):
    """
    Advanced elevator scheduling algorithm using:
    1. SCAN algorithm (elevator continues in direction until no more requests)
    2. Nearest-neighbor assignment for idle elevators
    3. Load balancing across multiple elevators
    4. Predictive destination registration
    """

    def __init__(self):
        super().__init__("http://127.0.0.1:8000", True)

        # Track waiting passengers per floor
        self.waiting_up: Dict[int, Set[int]] = {}  # floor -> set of passenger IDs
        self.waiting_down: Dict[int, Set[int]] = {}  # floor -> set of passenger IDs

        # Track elevator assignments
        self.elevator_targets: Dict[int, List[int]] = {}  # elevator_id -> list of target floors

        # Store references to elevators and floors
        self.elevators: List[ProxyElevator] = []
        self.floors: List[ProxyFloor] = []

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """Initialize controller state"""
        self.elevators = elevators
        self.floors = floors
        self.num_floors = len(floors)
        self.num_elevators = len(elevators)

        # Initialize tracking structures
        for floor in floors:
            self.waiting_up[floor.floor] = set()
            self.waiting_down[floor.floor] = set()

        for elevator in elevators:
            self.elevator_targets[elevator.id] = []

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """Handle new passenger call"""
        floor_num = floor.floor
        passenger_id = passenger.id

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
            elevator.go_to_floor(best_floor)
            if best_floor not in self.elevator_targets[elevator.id]:
                self.elevator_targets[elevator.id].append(best_floor)

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """
        Decide whether to stop at approaching floor
        Stop if: passengers need to alight OR passengers waiting in same direction
        """
        floor_num = floor.floor

        # Check if any passenger wants to get off at this floor
        # If so, the elevator will automatically stop (handled by simulator)

        # Check if passengers waiting in same direction and add floor as target
        if direction == "up" and self.waiting_up[floor_num]:
            elevator.go_to_floor(floor_num)
        elif direction == "down" and self.waiting_down[floor_num]:
            elevator.go_to_floor(floor_num)

        # If at end of range, also pick up passengers waiting in opposite direction
        if floor_num == self.num_floors - 1 and self.waiting_down[floor_num]:
            elevator.go_to_floor(floor_num)
        elif floor_num == 0 and self.waiting_up[floor_num]:
            elevator.go_to_floor(floor_num)

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """Handle elevator stopped at floor"""
        floor_num = floor.floor

        # Remove from targets
        if floor_num in self.elevator_targets[elevator.id]:
            self.elevator_targets[elevator.id].remove(floor_num)

        # Passengers will be handled automatically by on_passenger_board
        # No need to manually iterate waiting passengers

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """Handle passenger boarding - register destination and update tracking"""
        floor_num = passenger.origin_floor
        passenger_id = passenger.id
        destination = passenger.destination_floor

        # Remove from waiting lists
        self.waiting_up[floor_num].discard(passenger_id)
        self.waiting_down[floor_num].discard(passenger_id)

        # Register destination floor
        elevator.go_to_floor(destination)
        if destination not in self.elevator_targets[elevator.id]:
            self.elevator_targets[elevator.id].append(destination)

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        """Handle passenger alighting"""
        # Passenger successfully delivered, no action needed
        pass

    def on_event_execute_start(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """Handle event execution start"""
        pass

    def on_event_execute_end(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """Handle event execution end"""
        pass

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """Handle elevator passing floor"""
        pass

    def _assign_elevator_to_call(self, floor_num: int, direction: str) -> None:
        """Assign best elevator to handle a call"""
        best_elevator = self._find_best_elevator(floor_num, direction)

        if best_elevator:
            best_elevator.go_to_floor(floor_num)
            if floor_num not in self.elevator_targets[best_elevator.id]:
                self.elevator_targets[best_elevator.id].append(floor_num)

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
        Score elevator for assignment (lower is better)
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


if __name__ == "__main__":
    algorithm = OptimizedElevatorController()
    algorithm.start()
