#!/usr/bin/env python3
"""
Simulation engine for elevator scheduling visualization
"""

import json
import asyncio
import subprocess
import threading
import time
import signal
from pathlib import Path
from typing import Optional, Dict, List, Any
from fastapi import WebSocket

import algo
import requests


class SimulationEngine:
    """Engine to run elevator simulations and broadcast state updates via WebSocket"""

    def __init__(
        self,
        algorithm_name: str,
        scenario_name: str,
        speed: float,
        websocket: WebSocket
    ):
        """
        Initialize simulation engine

        Args:
            algorithm_name: Name of the algorithm to use
            scenario_name: Name of the scenario JSON file (without .json)
            speed: Simulation speed multiplier (1.0 = normal)
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

        # Server state cache
        self.last_state = None
        self.server_url = "http://127.0.0.1:8000"

        # Server process
        self.server_process = None

        # Load scenario
        self._load_scenario()

        # Algorithm instance
        self.algorithm = None
        self.algorithm_thread = None

    def _load_scenario(self):
        """Load scenario data from JSON file"""
        data_dir = Path(__file__).parent.parent / "data"
        scenario_file = data_dir / f"{self.scenario_name}.json"

        if not scenario_file.exists():
            raise ValueError(f"Scenario file not found: {scenario_file}")

        with open(scenario_file, 'r') as f:
            self.scenario_data = json.load(f)

        self.building_config = self.scenario_data.get("building", {})
        self.traffic_events = self.scenario_data.get("traffic", [])

    async def start(self):
        """Start the simulation"""
        print(f"[SimulationEngine] Starting simulation: {self.algorithm_name} on {self.scenario_name}")
        self.running = True
        self.paused = False
        self.current_tick = 0

        try:
            # Send initial state
            await self._send_init_state()

            # Start elevator server in background
            await self._start_server()

            # Wait for server to be ready
            await self._wait_for_server()

            # Load scenario into server
            await self._load_scenario_to_server()

            # Start algorithm in background thread
            self._start_algorithm()

            # Run state monitoring loop
            await self._run_simulation()
        except Exception as e:
            print(f"[SimulationEngine] Error during simulation: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def _start_server(self):
        """Start elevator server in background"""
        print(f"[SimulationEngine] Starting elevator server on {self.server_url}...")
        loop = asyncio.get_event_loop()

        def run_server():
            import os
            # 跨平台兼容的进程创建
            popen_kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
            }

            # POSIX 系统（Linux, macOS）使用 preexec_fn
            if os.name == 'posix':
                popen_kwargs['preexec_fn'] = lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
            # Windows 使用 CREATE_NEW_PROCESS_GROUP
            elif os.name == 'nt':
                popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

            self.server_process = subprocess.Popen(
                ["uv", "run", "python", "-m", "elevator_saga.server.simulator"],
                **popen_kwargs
            )
            print(f"[SimulationEngine] Server process started with PID: {self.server_process.pid}")

        await loop.run_in_executor(None, run_server)

    async def _wait_for_server(self, timeout=10):
        """Wait for server to be ready"""
        print(f"[SimulationEngine] Waiting for server to be ready (timeout: {timeout}s)...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.get(f"{self.server_url}/state", timeout=1)
                )
                if response.status_code == 200:
                    print(f"[SimulationEngine] Server is ready!")
                    return True
            except Exception as e:
                # Server not ready yet
                pass

            await asyncio.sleep(0.5)

        # Check if process is still running
        if self.server_process and self.server_process.poll() is not None:
            stderr = self.server_process.stderr.read().decode() if self.server_process.stderr else ""
            print(f"[SimulationEngine] Server process died! Error: {stderr}")

        raise RuntimeError("Server failed to start in time")

    async def _load_scenario_to_server(self):
        """Load scenario data to server"""
        print(f"[SimulationEngine] Loading scenario {self.scenario_name} to server...")

        # Convert scenario format to server format
        traffic_data = {
            "building": {
                "floors": self.building_config.get("floors", 10),
                "elevators": self.building_config.get("elevators", 3),
                "elevator_capacity": self.building_config.get("capacity", 8),
                "duration": self.building_config.get("duration", 300)
            },
            "traffic": [
                {
                    "id": event.get("id", i),
                    "origin": event.get("from_floor", 1),
                    "destination": event.get("to_floor", 1),
                    "tick": event.get("call_time", 0)
                }
                for i, event in enumerate(self.traffic_events)
            ]
        }

        print(f"[SimulationEngine] Scenario: {len(self.traffic_events)} passengers, {traffic_data['building']}")

        # POST to server
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                f"{self.server_url}/traffic",
                json=traffic_data,
                timeout=5
            )
        )

        if response.status_code != 200:
            print(f"[SimulationEngine] Failed to load traffic: {response.status_code} {response.text}")
            raise RuntimeError(f"Failed to load traffic: {response.text}")

        print(f"[SimulationEngine] Scenario loaded successfully!")

    def _start_algorithm(self):
        """Start the algorithm in a background thread"""
        print(f"[SimulationEngine] Starting algorithm {self.algorithm_name}...")

        def run_algorithm():
            try:
                # Get algorithm class
                algorithm_class = getattr(algo, self.algorithm_name)

                # Create algorithm instance
                kwargs = {
                    "server_url": self.server_url,
                    "enable_logging": False
                }

                self.algorithm = algorithm_class(**kwargs)
                print(f"[SimulationEngine] Algorithm instance created, starting...")

                # Start algorithm (this will block)
                self.algorithm.start()
                print(f"[SimulationEngine] Algorithm finished")
            except Exception as e:
                print(f"[SimulationEngine] Algorithm error: {e}")
                import traceback
                traceback.print_exc()

        self.algorithm_thread = threading.Thread(target=run_algorithm, daemon=True)
        self.algorithm_thread.start()
        print(f"[SimulationEngine] Algorithm thread started")

    def pause(self):
        """Pause the simulation"""
        self.paused = True

    def resume(self):
        """Resume the simulation"""
        self.paused = False

    def stop(self):
        """Stop the simulation"""
        self.running = False

        # Kill server process
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=2)
            except:
                self.server_process.kill()
            self.server_process = None

    def set_speed(self, speed: float):
        """Set simulation speed"""
        self.speed = max(0.1, min(10.0, speed))

    async def _send_init_state(self):
        """Send initial state to client"""
        num_floors = self.building_config.get("floors", 10)
        num_elevators = self.building_config.get("elevators", 3)

        # Send init message
        await self.websocket.send_json({
            "type": "init",
            "building": {
                "floors": num_floors,
                "elevators": num_elevators,
                "capacity": self.building_config.get("capacity", 8),
                "description": self.building_config.get("description", ""),
                "duration": self.building_config.get("duration", 0)
            },
            "algorithm": self.algorithm_name,
            "scenario": self.scenario_name
        })

    async def _run_simulation(self):
        """Main simulation loop - poll server state and broadcast updates"""
        max_duration = self.building_config.get("duration", 300)

        while self.running and self.current_tick < max_duration * 2:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            try:
                # Fetch current state from server
                state = await self._fetch_server_state()

                if state:
                    # Send state update
                    await self._send_state_update(state)
                    self.current_tick += 1

                # Sleep based on speed
                await asyncio.sleep(0.1 / self.speed)

            except Exception as e:
                print(f"Error in simulation loop: {e}")
                # Continue anyway
                await asyncio.sleep(0.1)

        # Send completion message
        await self._send_completion()

        # Stop the server
        self.stop()

    async def _fetch_server_state(self) -> Optional[Dict]:
        """Fetch current state from elevator server"""
        try:
            # Run blocking request in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(f"{self.server_url}/state", timeout=1)
            )

            if response.status_code == 200:
                return response.json()
        except Exception:
            # Server might not be ready yet
            pass

        return None

    async def _send_state_update(self, state: Dict):
        """Send current state to client"""
        # Extract elevator states
        elevators = state.get("elevators", [])
        elevators_state = []

        for i, elevator in enumerate(elevators):
            # Determine direction
            direction = "idle"
            current_floor = elevator.get("floor", 1)

            # Check if moving
            target_floors = elevator.get("target_floors", [])
            if target_floors:
                next_target = target_floors[0]
                if next_target > current_floor:
                    direction = "up"
                elif next_target < current_floor:
                    direction = "down"

            elevators_state.append({
                "id": i,
                "floor": current_floor,
                "direction": direction,
                "passengers": elevator.get("passengers", []),
                "capacity": elevator.get("capacity", 8)
            })

        # Extract waiting passengers by floor
        waiting_by_floor = {}
        for floor_num in range(1, state.get("num_floors", 10) + 1):
            floor_key = str(floor_num)
            floor_data = state.get("floors", {}).get(floor_key, {})
            waiting_passengers = floor_data.get("waiting_passengers", [])

            waiting_by_floor[floor_key] = [
                {
                    "id": p.get("id", 0),
                    "from_floor": floor_num,
                    "to_floor": p.get("destination_floor", 1),
                    "call_time": p.get("call_time", 0)
                }
                for p in waiting_passengers
            ]

        # Calculate statistics
        total_waiting = sum(len(passengers) for passengers in waiting_by_floor.values())
        total_in_elevator = sum(len(e["passengers"]) for e in elevators_state)

        update = {
            "type": "state_update",
            "tick": self.current_tick,
            "elevators": elevators_state,
            "waiting": waiting_by_floor,
            "stats": {
                "total_passengers": total_waiting + total_in_elevator,
                "waiting": total_waiting,
                "in_elevator": total_in_elevator,
                "completed": 0,  # Not available in real-time
                "avg_wait_time": 0.0  # Not available in real-time
            }
        }

        await self.websocket.send_json(update)

    async def _send_completion(self):
        """Send simulation completion message"""
        await self.websocket.send_json({
            "type": "complete",
            "tick": self.current_tick,
            "stats": {
                "total_passengers": 0,
                "avg_wait_time": 0
            }
        })
