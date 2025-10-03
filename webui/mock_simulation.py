#!/usr/bin/env python3
"""
Mock Simulation Engine - Provides pre-recorded/generated data for WebUI visualization

This is a simplified simulation that generates realistic-looking elevator movements
without actually running the scheduling algorithms. Useful for:
- Quick demonstrations
- UI development and testing
- Visual effect validation
"""

import json
import asyncio
import random
from pathlib import Path
from typing import Optional, Dict, List, Any
from fastapi import WebSocket


class MockSimulationEngine:
    """
    Mock simulation engine that generates realistic elevator movements
    and passenger flows for visualization purposes.
    """

    def __init__(
        self,
        algorithm_name: str,
        scenario_name: str,
        speed: float,
        websocket: WebSocket
    ):
        """
        Initialize mock simulation engine

        Args:
            algorithm_name: Name of the algorithm (for display only)
            scenario_name: Name of the scenario JSON file
            speed: Simulation speed multiplier
            websocket: WebSocket connection for broadcasting updates
        """
        self.algorithm_name = algorithm_name
        self.scenario_name = scenario_name
        self.speed = speed
        self.websocket = websocket

        # State tracking
        self.running = False
        self.paused = False
        self.current_tick = 0

        # Scenario data
        self.scenario_data = None
        self.building_config = None
        self.traffic_events = []

        # Simulation state
        self.elevators = []
        self.waiting_passengers = {}
        self.completed_passengers = []

        # Load scenario
        self._load_scenario()

    def _load_scenario(self):
        """Load scenario data from JSON file"""
        print(f"[MockSimulation] Loading scenario: {self.scenario_name}")
        data_dir = Path(__file__).parent.parent / "data"
        scenario_file = data_dir / f"{self.scenario_name}.json"

        if not scenario_file.exists():
            raise ValueError(f"Scenario file not found: {scenario_file}")

        with open(scenario_file, 'r') as f:
            self.scenario_data = json.load(f)

        self.building_config = self.scenario_data.get("building", {})
        self.traffic_events = self.scenario_data.get("traffic", [])

        print(f"[MockSimulation] Loaded {len(self.traffic_events)} passengers, "
              f"{self.building_config.get('floors')} floors, "
              f"{self.building_config.get('elevators')} elevators")

    async def start(self):
        """Start the mock simulation"""
        print(f"[MockSimulation] Starting: {self.algorithm_name} on {self.scenario_name}")
        self.running = True
        self.paused = False
        self.current_tick = 0

        # Send initial state
        await self._send_init_state()

        # Initialize elevators
        self._initialize_elevators()

        # Run simulation loop
        await self._run_simulation()

    def _initialize_elevators(self):
        """Initialize elevator states"""
        num_elevators = self.building_config.get("elevators", 3)
        capacity = self.building_config.get("capacity", 8)

        self.elevators = []
        for i in range(num_elevators):
            self.elevators.append({
                "id": i,
                "current_floor": 1.0,
                "target_floor": 1,
                "direction": "idle",
                "passengers": [],
                "capacity": capacity,
                "speed": 0.5  # floors per tick
            })

        # Initialize waiting passengers by floor
        num_floors = self.building_config.get("floors", 10)
        self.waiting_passengers = {floor: [] for floor in range(1, num_floors + 1)}

    async def _send_init_state(self):
        """Send initial state to client"""
        num_floors = self.building_config.get("floors", 10)
        num_elevators = self.building_config.get("elevators", 3)

        await self.websocket.send_json({
            "type": "init",
            "building": {
                "floors": num_floors,
                "elevators": num_elevators,
                "capacity": self.building_config.get("capacity", 8),
                "description": self.building_config.get("description", ""),
                "duration": self.building_config.get("duration", 300)
            },
            "algorithm": self.algorithm_name,
            "scenario": self.scenario_name
        })
        print(f"[MockSimulation] Sent init state")

    async def _run_simulation(self):
        """Main simulation loop"""
        max_duration = self.building_config.get("duration", 300)
        # Add safety limit: 3x the configured duration to prevent infinite loops
        safety_limit = max_duration * 3

        while self.running:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            # Process traffic events for current tick
            self._process_traffic_events()

            # Update elevator positions and assignments
            self._update_elevators()

            # Send state update
            await self._send_state_update()

            # Check if all passengers have been delivered
            total_waiting = sum(len(p) for p in self.waiting_passengers.values())
            total_in_elevator = sum(len(e["passengers"]) for e in self.elevators)
            all_delivered = (total_waiting == 0 and total_in_elevator == 0
                           and len(self.completed_passengers) == len(self.traffic_events))

            # Stop if all passengers delivered
            if all_delivered:
                print(f"[MockSimulation] ✅ All {len(self.traffic_events)} passengers delivered at tick {self.current_tick}")
                break

            # Safety check: prevent infinite loops
            if self.current_tick >= safety_limit:
                print(f"[MockSimulation] ⚠️ Safety limit ({safety_limit} ticks) reached!")
                print(f"[MockSimulation] Undelivered: {total_waiting} waiting + {total_in_elevator} in elevator = {total_waiting + total_in_elevator} passengers")
                break

            # Increment tick
            self.current_tick += 1

            # Sleep based on speed
            await asyncio.sleep(0.1 / self.speed)

        # Send completion message
        await self._send_completion()
        print(f"[MockSimulation] Simulation complete at tick {self.current_tick}")

    def _process_traffic_events(self):
        """Process traffic events for current tick"""
        for event in self.traffic_events:
            if event.get("tick") == self.current_tick:
                from_floor = event.get("origin") + 1  # Convert 0-indexed to 1-indexed
                to_floor = event.get("destination") + 1  # Convert 0-indexed to 1-indexed

                passenger = {
                    "id": event.get("id", len(self.completed_passengers) +
                         sum(len(p) for p in self.waiting_passengers.values())),
                    "from_floor": from_floor,
                    "to_floor": to_floor,
                    "call_time": self.current_tick,
                    "pickup_time": None,
                    "dropoff_time": None
                }

                if from_floor in self.waiting_passengers:
                    self.waiting_passengers[from_floor].append(passenger)
                    # Assign elevator to pick up
                    self._assign_elevator_to_floor(from_floor)

    def _assign_elevator_to_floor(self, floor: int):
        """Assign the nearest idle elevator to a floor"""
        idle_elevators = [e for e in self.elevators if e["direction"] == "idle"]

        if idle_elevators:
            # Find nearest idle elevator
            nearest = min(idle_elevators,
                         key=lambda e: abs(e["current_floor"] - floor))
            nearest["target_floor"] = floor
            nearest["direction"] = "up" if floor > nearest["current_floor"] else "down"

    def _update_elevators(self):
        """Update elevator positions and handle passengers"""
        for elevator in self.elevators:
            current = elevator["current_floor"]
            target = elevator["target_floor"]

            # Move elevator towards target
            if abs(current - target) > 0.01:
                direction = 1 if target > current else -1
                step = min(elevator["speed"], abs(target - current))
                elevator["current_floor"] = current + direction * step

                # Update direction indicator
                if direction > 0:
                    elevator["direction"] = "up"
                else:
                    elevator["direction"] = "down"
            else:
                # Reached target floor
                elevator["current_floor"] = float(target)
                elevator["direction"] = "idle"

                # Handle passenger pickup/dropoff
                floor_num = int(round(current))
                self._handle_floor_stop(elevator, floor_num)

                # Assign next target
                self._find_next_target(elevator)

    def _handle_floor_stop(self, elevator: Dict, floor: int):
        """Handle passenger pickup and dropoff at a floor"""
        # Dropoff passengers
        passengers_to_remove = []
        for passenger in elevator["passengers"]:
            if passenger["to_floor"] == floor:
                passenger["dropoff_time"] = self.current_tick
                self.completed_passengers.append(passenger)
                passengers_to_remove.append(passenger)

        for p in passengers_to_remove:
            elevator["passengers"].remove(p)

        # Pickup passengers
        if floor in self.waiting_passengers:
            waiting = self.waiting_passengers[floor]
            while waiting and len(elevator["passengers"]) < elevator["capacity"]:
                passenger = waiting.pop(0)
                passenger["pickup_time"] = self.current_tick
                elevator["passengers"].append(passenger)

    def _find_next_target(self, elevator: Dict):
        """Find next target floor for elevator"""
        # Priority 1: Deliver current passengers
        if elevator["passengers"]:
            destinations = [p["to_floor"] for p in elevator["passengers"]]
            elevator["target_floor"] = min(destinations,
                                          key=lambda d: abs(d - elevator["current_floor"]))
            return

        # Priority 2: Pick up waiting passengers
        waiting_floors = [floor for floor, passengers in self.waiting_passengers.items()
                         if passengers]

        if waiting_floors:
            elevator["target_floor"] = min(waiting_floors,
                                          key=lambda f: abs(f - elevator["current_floor"]))
        else:
            # No work to do, stay at current floor
            elevator["target_floor"] = int(round(elevator["current_floor"]))

    async def _send_state_update(self):
        """Send current state to client"""
        # Prepare elevator states
        elevators_state = []
        for elevator in self.elevators:
            elevators_state.append({
                "id": elevator["id"],
                "floor": elevator["current_floor"],
                "direction": elevator["direction"],
                "passengers": elevator["passengers"],
                "capacity": elevator["capacity"]
            })

        # Prepare waiting passengers
        waiting_state = {}
        for floor, passengers in self.waiting_passengers.items():
            if passengers:  # Only include floors with waiting passengers
                waiting_state[str(floor)] = passengers

        # Calculate statistics
        total_waiting = sum(len(p) for p in self.waiting_passengers.values())
        total_in_elevator = sum(len(e["passengers"]) for e in self.elevators)
        total_completed = len(self.completed_passengers)

        # Calculate average wait time
        avg_wait_time = 0.0
        if self.completed_passengers:
            wait_times = [
                (p["pickup_time"] - p["call_time"])
                for p in self.completed_passengers
                if p.get("pickup_time") is not None
            ]
            if wait_times:
                avg_wait_time = sum(wait_times) / len(wait_times)

        state = {
            "type": "state_update",
            "tick": self.current_tick,
            "elevators": elevators_state,
            "waiting": waiting_state,
            "stats": {
                "total_passengers": len(self.traffic_events),
                "waiting": total_waiting,
                "in_elevator": total_in_elevator,
                "completed": total_completed,
                "avg_wait_time": round(avg_wait_time, 2)
            }
        }

        await self.websocket.send_json(state)

    async def _send_completion(self):
        """Send simulation completion message"""
        # Final statistics
        avg_wait_time = 0.0
        if self.completed_passengers:
            wait_times = [
                (p["pickup_time"] - p["call_time"])
                for p in self.completed_passengers
                if p.get("pickup_time") is not None
            ]
            if wait_times:
                avg_wait_time = sum(wait_times) / len(wait_times)

        await self.websocket.send_json({
            "type": "complete",
            "tick": self.current_tick,
            "stats": {
                "total_passengers": len(self.completed_passengers),
                "avg_wait_time": round(avg_wait_time, 2)
            }
        })

    def pause(self):
        """Pause the simulation"""
        self.paused = True
        print(f"[MockSimulation] Paused at tick {self.current_tick}")

    def resume(self):
        """Resume the simulation"""
        self.paused = False
        print(f"[MockSimulation] Resumed at tick {self.current_tick}")

    def stop(self):
        """Stop the simulation"""
        self.running = False
        print(f"[MockSimulation] Stopped at tick {self.current_tick}")

    def set_speed(self, speed: float):
        """Set simulation speed"""
        self.speed = max(0.1, min(10.0, speed))
        print(f"[MockSimulation] Speed set to {self.speed}x")
