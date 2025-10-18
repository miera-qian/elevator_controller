#!/usr/bin/env python3
"""
Direct Simulation Engine - Connects to an already-running simulator server

Used when simulator.py is already running on the system.
Starts the scheduling algorithm in a background thread, polls the server,
and broadcasts state updates via WebSocket.
"""

import json
import asyncio
import requests
import threading
import time
import logging
import sys
from pathlib import Path
from typing import Optional, Dict
from fastapi import WebSocket

# Import algo module to get available algorithms
import algo

# 配置日志
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "direct_simulation.log"

logger = logging.getLogger("DirectSimulation")
logger.setLevel(logging.DEBUG)

# 文件处理器
fh = logging.FileHandler(log_file, encoding='utf-8')
fh.setLevel(logging.DEBUG)

# 日志格式
formatter = logging.Formatter('[%(asctime)s] %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh.setFormatter(formatter)
logger.addHandler(fh)

# 创建一个日志处理器来捕获 print() 输出
class PrintToLogger(object):
    """将 print() 的输出重定向到日志"""
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().split('\n'):
            if line:
                self.logger.log(self.level, line)

    def flush(self):
        pass

# 将 stdout 和 stderr 重定向到日志
sys.stdout = PrintToLogger(logger, logging.INFO)
sys.stderr = PrintToLogger(logger, logging.ERROR)


class DirectSimulationEngine:
    """
    Direct simulation engine that connects to an already-running simulator server.
    Does NOT start its own server subprocess.
    Starts the scheduling algorithm in a background thread,
    polls the server for state updates, and broadcasts them via WebSocket.
    """

    def __init__(
        self,
        algorithm_name: str,
        scenario_name: str,
        speed: float,
        max_ticks: Optional[int],
        websocket: WebSocket,
        server_url: str = "http://127.0.0.1:8000"
    ):
        """
        Initialize direct simulation engine

        Args:
            algorithm_name: Name of the algorithm class
            scenario_name: Name of the scenario JSON file
            speed: Simulation speed multiplier
            max_ticks: Maximum simulation duration in ticks (None = use scenario default)
            websocket: WebSocket connection for broadcasting updates
            server_url: URL of already-running simulator server
        """
        self.algorithm_name = algorithm_name
        self.scenario_name = scenario_name
        self.speed = speed
        self.max_ticks = max_ticks
        self.websocket = websocket
        self.server_url = server_url

        # State tracking
        self.running = False
        self.paused = False
        self.current_tick = 0

        # Scenario data
        self.scenario_data = None
        self.building_config = None
        self.traffic_events = []

        # Algorithm instance
        self.algorithm_instance = None
        self.algorithm_thread = None

        # Load scenario metadata
        self._load_scenario_metadata()

    def _load_scenario_metadata(self):
        """Load scenario metadata from JSON file"""
        logger.info(f"Loading scenario metadata: {self.scenario_name}")
        data_dir = Path(__file__).parent.parent / "traffic"
        scenario_file = data_dir / f"{self.scenario_name}.json"

        if not scenario_file.exists():
            raise ValueError(f"Scenario file not found: {scenario_file}")

        with open(scenario_file, 'r', encoding='utf-8') as f:
            self.scenario_data = json.load(f)

        self.building_config = self.scenario_data.get("building", {})
        self.traffic_events = self.scenario_data.get("traffic", [])

        logger.info(f"Loaded {len(self.traffic_events)} passengers")

    def _start_algorithm_thread(self):
        """Start the scheduling algorithm in a background thread"""
        import time as time_module
        start_time = time_module.time()
        
        logger.info(f"START_ALGORITHM_THREAD called")
        logger.debug(f"  Algorithm: {self.algorithm_name}")
        logger.debug(f"  Server URL: {self.server_url}")

        def run_algorithm():
            try:
                logger.info(f"[THREAD] Algorithm thread started")
                
                logger.debug(f"[THREAD] Step 1: Import algo module")
                logger.debug(f"[THREAD]   Available: {[x for x in dir(algo) if not x.startswith('_')]}")
                
                logger.debug(f"[THREAD] Step 2: Get algorithm class '{self.algorithm_name}'")
                algorithm_class = getattr(algo, self.algorithm_name)
                logger.info(f"[THREAD] Algorithm class found: {algorithm_class.__name__}")

                logger.debug(f"[THREAD] Step 3: Create algorithm instance")
                logger.debug(f"[THREAD]   server_url={self.server_url}")
                self.algorithm_instance = algorithm_class(
                    server_url=self.server_url,
                    enable_logging=False
                )
                logger.info(f"[THREAD] Algorithm instance created successfully")

                logger.info(f"[THREAD] Step 4: Calling algorithm.start() - THIS WILL BLOCK")
                self.algorithm_instance.start()
                logger.info(f"[THREAD] Algorithm.start() returned")
                
            except Exception as e:
                logger.error(f"[THREAD] Exception in algorithm thread: {e}", exc_info=True)
            finally:
                logger.info(f"[THREAD] Algorithm thread ending")

        logger.debug(f"Creating daemon thread...")
        self.algorithm_thread = threading.Thread(target=run_algorithm, daemon=True)
        self.algorithm_thread.start()
        
        elapsed = time_module.time() - start_time
        logger.info(f"Algorithm thread started (id: {self.algorithm_thread.ident}, elapsed: {elapsed:.3f}s)")

    async def start(self):
        """Start the direct simulation by starting algorithm and polling server"""
        logger.info(f"======== START_SIMULATION ========")
        logger.info(f"Algorithm: {self.algorithm_name}")
        logger.info(f"Scenario: {self.scenario_name}")
        logger.info(f"Max Ticks: {self.max_ticks}")
        logger.info(f"Server: {self.server_url}")
        logger.info(f"==================================")

        self.running = True
        self.paused = False
        self.current_tick = 0

        # Send initial state
        logger.info(f"Sending init state to WebSocket")
        await self._send_init_state()

        try:
            # Verify server is running
            logger.info(f"Checking if server is running")
            if not await self._check_server():
                raise RuntimeError("Simulator server is not responding")

            # Load the selected scenario on simulator
            logger.info(f"Loading scenario '{self.scenario_name}' on simulator")
            try:
                response = requests.post(
                    f"{self.server_url}/api/load_scenario",
                    json={"scenario_name": self.scenario_name},
                    timeout=5
                )
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Scenario loaded successfully: {result['elevators']} elevators, "
                               f"{result['floors']} floors, {result['passengers']} passengers")
                else:
                    error_msg = f"Failed to load scenario: {response.text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
            except Exception as e:
                logger.error(f"Error loading scenario on simulator: {e}")
                raise

            # Set max_ticks on simulator if provided by user
            if self.max_ticks is not None:
                logger.info(f"Setting max_ticks={self.max_ticks} on simulator")
                try:
                    response = requests.post(
                        f"{self.server_url}/api/config/max_ticks",
                        json={"max_ticks": self.max_ticks},
                        timeout=5
                    )
                    if response.status_code == 200:
                        logger.info(f"Successfully set simulator max_ticks to {self.max_ticks}")
                    else:
                        logger.warning(f"Failed to set max_ticks: {response.text}")
                except Exception as e:
                    logger.error(f"Error setting max_ticks on simulator: {e}")
                    # Continue anyway - frontend polling will still respect max_ticks

            # Start algorithm in background
            logger.info(f"Starting algorithm thread")
            self._start_algorithm_thread()

            # Give algorithm time to initialize
            logger.debug(f"Waiting 2 seconds for algorithm to initialize")
            await asyncio.sleep(2)

            # Run simulation loop
            logger.info(f"Starting simulation polling loop")
            await self._run_simulation()

        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            await self.websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        finally:
            # Stop the algorithm
            logger.info(f"Cleaning up")
            if self.algorithm_instance:
                logger.debug(f"Stopping algorithm instance")
                self.algorithm_instance.stop()

    async def _check_server(self) -> bool:
        """Check if server is responding"""
        logger.info(f"Checking server at {self.server_url}")
        max_retries = 5
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.server_url}/api/state", timeout=2)
                if response.status_code == 200:
                    logger.info(f"Server is ready!")
                    return True
            except Exception as e:
                if i == max_retries - 1:
                    logger.error(f"Server check failed: {e}")

            if i < max_retries - 1:
                await asyncio.sleep(0.5)

        return False

    async def _send_init_state(self):
        """Send initial state to client"""
        await self.websocket.send_json({
            "type": "init",
            "building": {
                "floors": self.building_config.get("floors"),
                "elevators": self.building_config.get("elevators"),
                "capacity": self.building_config.get("elevator_capacity", 8),
                "description": self.building_config.get("description", ""),
                "duration": self.building_config.get("duration")
            },
            "algorithm": self.algorithm_name,
            "scenario": self.scenario_name
        })

    async def _run_simulation(self):
        """Main simulation loop - poll server for state updates"""
        # 使用max_ticks（如果提供），否则使用场景的duration
        max_duration = self.max_ticks if self.max_ticks is not None else self.building_config.get("duration", 300)
        safety_limit = max_duration * 3

        last_tick = 0
        base_poll_interval = 0.2

        logger.info(f"Starting simulation loop (max_duration={max_duration}, max_ticks={self.max_ticks})")

        while self.running and self.current_tick < safety_limit:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            try:
                # Get current state from server
                response = requests.get(f"{self.server_url}/api/state", timeout=5)
                if response.status_code == 200:
                    state_data = response.json()
                    self.current_tick = state_data.get("tick", 0)

                    # Only send update if tick changed
                    if self.current_tick != last_tick:
                        await self._send_state_update(state_data)
                        last_tick = self.current_tick

                        # Check if all passengers completed (prioritize this check)
                        metrics = state_data.get("metrics", {})
                        if metrics.get("completed_passengers", 0) >= len(self.traffic_events):
                            logger.info(f"All passengers completed at tick {self.current_tick}")
                            break

                        # Check if simulation reached max_duration
                        if self.current_tick >= max_duration:
                            logger.info(f"Reached max_duration at tick {self.current_tick}")
                            break
                else:
                    logger.warning(f"Server returned status {response.status_code}")

            except requests.exceptions.Timeout:
                logger.debug(f"Request timeout at tick {self.current_tick}")
                continue
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error: {e}")
                break
            except Exception as e:
                logger.error(f"Error polling state: {e}")
                break

            # Control polling rate based on speed (use short sleep to allow quick stop)
            if self.running:
                await asyncio.sleep(base_poll_interval / self.speed)

        # Send completion only if not stopped
        if self.running:
            await self._send_completion()

        logger.info(f"Simulation loop ended (running={self.running}, tick={self.current_tick})")

    async def _send_state_update(self, state_data: Dict):
        """Convert server state to WebUI format and send"""
        # Extract elevator states
        elevators_state = []
        for elev in state_data.get("elevators", []):
            elev_id = elev.get("id")

            # Get current floor from position object
            position = elev.get("position", {})
            if position:
                current_floor = position.get("current_floor", 0)
                target_floor = position.get("target_floor", current_floor)
            else:
                current_floor = elev.get("current_floor", 0)
                target_floor = elev.get("target_floor", current_floor)

            # Determine direction based on current vs target floor
            if target_floor > current_floor:
                direction = "up"
            elif target_floor < current_floor:
                direction = "down"
            else:
                direction = "idle"

            # Convert passengers
            passengers_info = []
            for p_id in elev.get("passengers", []):
                passengers_dict = state_data.get("passengers", {})
                if str(p_id) in passengers_dict:
                    p = passengers_dict[str(p_id)]
                    passengers_info.append({
                        "id": p.get("id"),
                        "from_floor": p.get("origin", 0) + 1,
                        "to_floor": p.get("destination", 0) + 1,
                        "call_time": p.get("arrive_tick", 0)
                    })

            elevators_state.append({
                "id": elev.get("id"),
                "floor": current_floor + 1,  # Convert to 1-indexed
                "direction": direction,
                "passengers": passengers_info,
                "capacity": elev.get("max_capacity", 8)
            })

        # Extract waiting passengers by floor
        waiting_by_floor = {}
        passengers_dict = state_data.get("passengers", {})

        for floor in state_data.get("floors", []):
            floor_num = floor.get("floor", 0) + 1  # Convert to 1-indexed
            waiting_passengers = []

            # Process up and down queues
            for p_id in floor.get("up_queue", []) + floor.get("down_queue", []):
                if str(p_id) in passengers_dict:
                    p = passengers_dict[str(p_id)]
                    waiting_passengers.append({
                        "id": p.get("id"),
                        "from_floor": p.get("origin", 0) + 1,
                        "to_floor": p.get("destination", 0) + 1,
                        "call_time": p.get("arrive_tick", 0)
                    })

            if waiting_passengers:
                waiting_by_floor[str(floor_num)] = waiting_passengers

        # Calculate stats
        metrics = state_data.get("metrics", {})
        total_waiting = sum(len(p) for p in waiting_by_floor.values())
        total_in_elevator = sum(len(e.get("passengers", [])) for e in state_data.get("elevators", []))

        # Send state update
        await self.websocket.send_json({
            "type": "state_update",
            "tick": self.current_tick,
            "elevators": elevators_state,
            "waiting": waiting_by_floor,
            "stats": {
                "total_passengers": len(self.traffic_events),
                "waiting": total_waiting,
                "in_elevator": total_in_elevator,
                "completed": metrics.get("completed_passengers", 0),
                "avg_wait_time": round(metrics.get("average_floor_wait_time", 0), 2)
            }
        })

    async def _send_completion(self):
        """Send completion message"""
        try:
            # Get final stats from server
            response = requests.get(f"{self.server_url}/api/state", timeout=5)
            if response.status_code == 200:
                state_data = response.json()
                metrics = state_data.get("metrics", {})

                await self.websocket.send_json({
                    "type": "complete",
                    "tick": self.current_tick,
                    "stats": {
                        "total_passengers": metrics.get("completed_passengers", 0),
                        "avg_wait_time": round(metrics.get("average_floor_wait_time", 0), 2),
                        "p95_wait_time": round(metrics.get("p95_floor_wait_time", 0), 2)
                    }
                })
                return
        except Exception as e:
            logger.error(f"Error getting final stats: {e}")

        # Fallback completion message
        await self.websocket.send_json({
            "type": "complete",
            "tick": self.current_tick,
            "stats": {
                "total_passengers": len(self.traffic_events),
                "avg_wait_time": 0.0,
                "p95_wait_time": 0.0
            }
        })

    def pause(self):
        """Pause the simulation"""
        self.paused = True

    def resume(self):
        """Resume the simulation"""
        self.paused = False

    def stop(self):
        """Stop the simulation"""
        self.running = False
        if self.algorithm_instance:
            self.algorithm_instance.stop()

    def set_speed(self, speed: float):
        """Set simulation speed"""
        self.speed = max(0.1, min(10.0, speed))

