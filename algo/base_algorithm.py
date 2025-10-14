#!/usr/bin/env python3
"""
Base Algorithm Class

Provides abstract base class for elevator scheduling algorithms.
All custom algorithms should inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Set
from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import SimulationEvent


class BaseAlgorithm(ElevatorController, ABC):
    """
    Abstract base class for elevator scheduling algorithms.

    Provides common infrastructure and defines required methods.
    Subclasses should implement the abstract methods to define their scheduling logic.
    """

    def __init__(self, server_url: str = "http://127.0.0.1:8000", enable_logging: bool = True):
        super().__init__(server_url, enable_logging)

        # Common tracking structures
        self.waiting_up: Dict[int, Set[int]] = {}  # floor -> set of passenger IDs going up
        self.waiting_down: Dict[int, Set[int]] = {}  # floor -> set of passenger IDs going down
        self.elevator_targets: Dict[int, List[int]] = {}  # elevator_id -> target floors

        # Store references
        self.elevators: List[ProxyElevator] = []
        self.floors: List[ProxyFloor] = []
        self.num_floors: int = 0
        self.num_elevators: int = 0

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """Initialize algorithm state - can be overridden"""
        self.elevators = elevators
        self.floors = floors
        self.num_floors = len(floors)
        self.num_elevators = len(elevators)
        # --- DEBUG PRINT ---
        print(f"--- ALGORITHM INITIALIZED ---")
        print(f"  > Managing {self.num_elevators} elevators and {self.num_floors} floors.")
        print(f"---------------------------------")
        # --- END DEBUG ---

        # Initialize tracking structures
        for floor in floors:
            self.waiting_up[floor.floor] = set()
            self.waiting_down[floor.floor] = set()

        for elevator in elevators:
            self.elevator_targets[elevator.id] = []

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

    def on_event_execute_end(
        self, tick: int, events: List[SimulationEvent],
        elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """Handle event execution end - override if needed"""
        pass

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """Handle elevator passing floor - override if needed"""
        pass

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        """Handle passenger alighting - override if needed"""
        pass

    # Abstract methods that must be implemented by subclasses

    @abstractmethod
    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """
        Handle new passenger call.

        This is where the main scheduling logic begins - assign an elevator to pick up the passenger.
        """
        pass

    @abstractmethod
    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """
        Handle idle elevator.

        Decide what an idle elevator should do (e.g., go to nearest waiting passenger).
        """
        pass

    @abstractmethod
    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """
        Decide whether to stop at approaching floor.

        Implement logic to determine if elevator should stop for waiting passengers or alighting.
        """
        pass

    @abstractmethod
    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """
        Handle elevator stopped at floor.

        Update internal state when elevator stops.
        """
        pass

    @abstractmethod
    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """
        Handle passenger boarding.

        Register passenger destination and update tracking.
        """
        pass
