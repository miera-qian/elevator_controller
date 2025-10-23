#!/usr/bin/env python3
"""
Real Simulation Engine - Runs actual scheduling algorithms
Uses subprocess to run simulator server and algorithm together
"""

import json
import asyncio
import subprocess
import time
import requests
from pathlib import Path
from typing import Optional, Dict, List, Any
from fastapi import WebSocket

# Import algorithm classes
import algo


class RealSimulationEngine:
    """
    Real simulation engine that runs actual scheduling algorithms
    by starting a simulator server subprocess and running the algorithm.
    """

    def __init__(
        self,
        algorithm_name: str,
        scenario_name: str,
        speed: float,
        websocket: WebSocket
    ):
        """
        Initialize real simulation engine

        Args:
            algorithm_name: Name of the algorithm class
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

        # Server configuration
        self.server_host = "127.0.0.1"
        self.server_port = 18000  # Use different port to avoid conflicts
        self.server_url = f"http://{self.server_host}:{self.server_port}"

        # Subprocess handles
        self.server_process = None
        self.algorithm_task = None
        self.algorithm_instance = None  # Store algorithm instance for speed control

        # Load scenario
        self._load_scenario()

    def _load_scenario(self):
        """Load scenario data from JSON file"""
        print(f"[RealSimulation] Loading scenario: {self.scenario_name}")

        # 从 elevator-py 包的 traffic 目录加载场景
        try:
            import elevator_saga
            traffic_dir = Path(elevator_saga.__file__).parent / "traffic"
            scenario_file = traffic_dir / f"{self.scenario_name}.json"

            if not scenario_file.exists():
                # 回退到本地 data 目录
                data_dir = Path(__file__).parent.parent / "data"
                scenario_file = data_dir / f"{self.scenario_name}.json"

                if not scenario_file.exists():
                    raise ValueError(f"Scenario file not found: {self.scenario_name}.json")
        except ImportError:
            # 如果包不存在，使用本地目录
            data_dir = Path(__file__).parent.parent / "data"
            scenario_file = data_dir / f"{self.scenario_name}.json"

            if not scenario_file.exists():
                raise ValueError(f"Scenario file not found: {self.scenario_name}.json")

        print(f"[RealSimulation] Using scenario file: {scenario_file}")
        with open(scenario_file, 'r', encoding='utf-8') as f:
            self.scenario_data = json.load(f)

        self.building_config = self.scenario_data.get("building", {})
        self.traffic_events = self.scenario_data.get("traffic", [])

        print(f"[RealSimulation] Loaded {len(self.traffic_events)} passengers")

    def _find_scenario_index(self) -> int:
        """Find the index of the selected scenario in traffic files list"""
        try:
            # 获取traffic目录中的所有JSON文件（按名称排序）
            import elevator_saga
            traffic_dir = Path(elevator_saga.__file__).parent / "traffic"
            traffic_files = sorted([f.stem for f in traffic_dir.glob("*.json")])

            print(f"[RealSimulation] Available scenarios: {traffic_files}")
            print(f"[RealSimulation] Looking for scenario: {self.scenario_name}")

            if self.scenario_name in traffic_files:
                index = traffic_files.index(self.scenario_name)
                print(f"[RealSimulation] Found scenario at index {index}")
                return index
            else:
                print(f"[RealSimulation] Scenario '{self.scenario_name}' not found, using index 0")
                return 0
        except Exception as e:
            print(f"[RealSimulation] Error finding scenario index: {e}")
            return 0

    async def start(self):
        """Start the real simulation"""
        print(f"[RealSimulation] Starting: {self.algorithm_name} on {self.scenario_name}")
        self.running = True
        self.paused = False
        self.current_tick = 0

        # Send initial state
        await self._send_init_state()

        try:
            # Start simulator server
            await self._start_server()

            # Give server time to initialize
            await asyncio.sleep(1)

            # Verify server is running
            if not await self._check_server():
                raise RuntimeError("Failed to start simulator server")

            # Run simulation loop
            await self._run_simulation()

        except Exception as e:
            print(f"[RealSimulation] Error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        finally:
            # Clean up
            await self._cleanup()

    async def _start_server(self):
        """Start the simulator server in a subprocess"""
        # 使用虚拟环境的 Python 解释器
        import sys
        python_executable = sys.executable

        # Create log file for simulator output
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"simulator_{self.server_port}.log"

        # 启动 simulator 模块（来自 elevator-py 包）
        # simulator 会自动从 elevator_saga/traffic 目录加载场景文件
        self.server_process = subprocess.Popen(
            [python_executable, "-m", "elevator_saga.server.simulator",
             "--host", self.server_host,
             "--port", str(self.server_port),
             "--debug"],
            stdout=open(log_file, 'w', encoding='utf-8'),
            stderr=subprocess.STDOUT,
            text=True
        )

        print(f"[RealSimulation] Started server on {self.server_url}")
        print(f"[RealSimulation] Server logs: {log_file}")

    async def _check_server(self) -> bool:
        """Check if server is responding"""
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.server_url}/api/state", timeout=5)
                if response.status_code == 200:
                    print(f"[RealSimulation] Server is ready")
                    return True
            except Exception as e:
                if i == max_retries - 1:
                    print(f"[RealSimulation] Server check failed: {e}")

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
        """Main simulation loop"""
        # 【场景选择修复】设置正确的场景文件
        scenario_index = self._find_scenario_index()
        current_index = 0

        # 获取当前服务器加载的场景索引
        try:
            response = requests.get(f"{self.server_url}/api/traffic/info", timeout=5)
            if response.status_code == 200:
                current_index = response.json().get("current_index", 0)
                print(f"[RealSimulation] Server current scenario index: {current_index}")
        except Exception as e:
            print(f"[RealSimulation] Failed to get traffic info: {e}")

        # 如果当前索引不是目标场景，循环调用next直到到达目标
        attempts = 0
        max_attempts = 20  # 防止无限循环
        while current_index != scenario_index and attempts < max_attempts:
            attempts += 1
            try:
                print(f"[RealSimulation] Switching from index {current_index} to {scenario_index}...")
                response = requests.post(
                    f"{self.server_url}/api/traffic/next",
                    json={"full_reset": False},
                    timeout=5
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        current_index += 1
                        print(f"[RealSimulation] Switched to index {current_index}")
                    else:
                        print(f"[RealSimulation] Switch failed, resetting...")
                        # 尝试完全重置
                        response = requests.post(
                            f"{self.server_url}/api/traffic/next",
                            json={"full_reset": True},
                            timeout=5
                        )
                        current_index = 0
                else:
                    print(f"[RealSimulation] Server returned {response.status_code}")
                    break
            except Exception as e:
                print(f"[RealSimulation] Error switching scenario: {e}")
                break

        if current_index == scenario_index:
            print(f"[RealSimulation] ✅ Successfully loaded scenario: {self.scenario_name} (index {scenario_index})")
        else:
            print(f"[RealSimulation] ⚠️  Could not load exact scenario, using index {current_index}")

        # 【修复】验证场景加载成功，确保 max_tick > 0
        try:
            response = requests.get(f"{self.server_url}/api/traffic/info", timeout=5)
            if response.status_code == 200:
                info = response.json()
                max_tick = info.get("max_tick", 0)
                print(f"[RealSimulation] After switching: max_tick={max_tick}")

                if max_tick == 0:
                    print(f"[RealSimulation] ⚠️ WARNING: max_tick is 0 after switching! Attempting reset...")
                    # 尝试重置并重新加载
                    requests.post(f"{self.server_url}/api/reset", timeout=5)
                    await asyncio.sleep(0.5)

                    # 重新验证
                    response = requests.get(f"{self.server_url}/api/traffic/info", timeout=5)
                    if response.status_code == 200:
                        info = response.json()
                        max_tick = info.get("max_tick", 0)
                        print(f"[RealSimulation] After reset: max_tick={max_tick}")

                        if max_tick == 0:
                            raise RuntimeError("Failed to load scenario: max_tick is still 0 after reset")
            else:
                print(f"[RealSimulation] Failed to verify scenario: HTTP {response.status_code}")
        except Exception as e:
            print(f"[RealSimulation] Error verifying scenario: {e}")
            # 继续执行，但可能会失败

        # 给服务器一些时间完全加载场景
        await asyncio.sleep(0.5)

        # Start algorithm in background task
        self.algorithm_task = asyncio.create_task(self._run_algorithm())

        max_duration = self.building_config.get("duration", 300)
        safety_limit = max_duration * 3

        last_tick = 0

        # Poll server for state updates with controlled speed
        # Increase base polling interval to slow down the visualization
        base_poll_interval = 0.5  # Increased from 0.1 to slow down animation

        while self.running and self.current_tick < safety_limit:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            try:
                # Get current state from server with longer timeout
                response = requests.get(f"{self.server_url}/api/state", timeout=10)
                if response.status_code == 200:
                    state_data = response.json()
                    self.current_tick = state_data.get("tick", 0)

                    # Only send update if tick changed
                    if self.current_tick != last_tick:
                        await self._send_state_update(state_data)
                        last_tick = self.current_tick

                    # Check if simulation completed
                    metrics = state_data.get("metrics", {})
                    if metrics.get("completed_passengers", 0) >= len(self.traffic_events):
                        print(f"[RealSimulation] All passengers completed")
                        break
                else:
                    print(f"[RealSimulation] Server returned status {response.status_code}")

            except requests.exceptions.Timeout:
                print(f"[RealSimulation] Request timeout at tick {self.current_tick}, retrying...")
                continue
            except requests.exceptions.ConnectionError as e:
                print(f"[RealSimulation] Connection error: {e}")
                break
            except Exception as e:
                print(f"[RealSimulation] Error polling state: {e}")
                break

            # Control polling rate based on speed (slower base interval)
            await asyncio.sleep(base_poll_interval / self.speed)

        # Send completion
        await self._send_completion()

    async def _run_algorithm(self):
        """Run the algorithm in background with controlled speed"""
        try:
            import time

            # 【修复】等待场景完全加载，确保 max_tick > 0
            max_retries = 10
            max_tick = 0
            for i in range(max_retries):
                try:
                    response = requests.get(f"{self.server_url}/api/traffic/info", timeout=5)
                    if response.status_code == 200:
                        info = response.json()
                        max_tick = info.get("max_tick", 0)
                        if max_tick > 0:
                            print(f"[RealSimulation] Traffic loaded successfully, max_tick={max_tick}")
                            break
                        else:
                            print(f"[RealSimulation] Waiting for traffic to load... (attempt {i+1}/{max_retries}, max_tick={max_tick})")
                            await asyncio.sleep(0.5)
                    else:
                        print(f"[RealSimulation] Traffic info request failed: HTTP {response.status_code}")
                        await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"[RealSimulation] Error checking traffic info: {e}")
                    await asyncio.sleep(0.5)

            # 如果最终 max_tick 仍然是 0，抛出错误
            if max_tick == 0:
                raise RuntimeError("Cannot start algorithm: max_tick is 0 (no passengers in scenario)")

            # Get algorithm class
            algorithm_class = getattr(algo, self.algorithm_name)

            # Create algorithm instance
            self.algorithm_instance = algorithm_class(
                server_url=self.server_url,
                enable_logging=False
            )

            print(f"[RealSimulation] Starting algorithm: {self.algorithm_name}")

            # Patch BOTH step and the internal _run_event_driven_simulation loop
            original_step = self.algorithm_instance.api_client.step

            def delayed_step(*args, **kwargs):
                """Step wrapper that adds delay based on simulation speed"""
                result = original_step(*args, **kwargs)
                # Add delay: slower speed = longer delay
                delay = 0.5 / self.speed
                print(f"[DEBUG] Step completed, sleeping {delay:.2f}s")
                time.sleep(delay)
                return result

            self.algorithm_instance.api_client.step = delayed_step

            # Run algorithm (this is blocking, but now with delays)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.algorithm_instance.start)

        except Exception as e:
            print(f"[RealSimulation] Algorithm error: {e}")
            import traceback
            traceback.print_exc()

    async def _send_state_update(self, state_data: Dict):
        """Convert server state to WebUI format and send"""
        # Extract elevator states
        elevators_state = []
        for elev in state_data.get("elevators", []):
            elev_id = elev.get("id")

            # Get current floor first
            position = elev.get("position", {})
            if position:
                current_floor = position.get("current_floor", 0)
                # ✅ FIX: target_floor 也在 position 对象里！
                target_floor = position.get("target_floor", current_floor)
            else:
                current_floor = elev.get("current_floor", 0)
                target_floor = elev.get("target_floor", current_floor)

            # 🔍 DEBUG: 打印原始数据（每5个tick）
            if self.current_tick % 5 == 0:
                print(f"\n[🔍 RAW DATA] E{elev_id} at tick {self.current_tick}:")
                print(f"  position对象: {position}")
                print(f"  current_floor (直接): {elev.get('current_floor')}")
                print(f"  target_floor: {target_floor}")
                print(f"  使用的值: current={current_floor}, target={target_floor}")

            # Determine direction based on current vs target floor
            if target_floor > current_floor:
                direction = "up"
                print(f"  ✅ 判断: {target_floor} > {current_floor} → direction='up' (应该是绿色)")
            elif target_floor < current_floor:
                direction = "down"
                print(f"  ✅ 判断: {target_floor} < {current_floor} → direction='down' (应该是橙色)")
            else:
                # If at target, check if there are passengers (means moving)
                # or check run_status
                run_status = elev.get("run_status", {})
                if isinstance(run_status, dict):
                    run_status_value = run_status.get("value", "stopped")
                else:
                    run_status_value = run_status

                if run_status_value in ["constant_speed", "start_up", "start_down"]:
                    # Moving but at target, check last direction
                    # For now, use idle
                    direction = "idle"
                else:
                    direction = "idle"

                if self.current_tick % 5 == 0:
                    print(f"  ⚠️  判断: {target_floor} == {current_floor} → direction='idle' (灰色)")
                    print(f"      run_status: {run_status}")

            # Debug: print elevator state
            if self.current_tick % 10 == 0:
                print(f"[DEBUG] E{elev.get('id')} - floor: {current_floor}, target: {target_floor}, direction: {direction}, status: {elev.get('run_status')}, passengers: {len(elev.get('passengers', []))}")

            # Convert passengers
            passengers_info = []
            for p_id in elev.get("passengers", []):
                # Find passenger in state
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
        """Send completion message with full final state"""
        try:
            # Get final stats from server with longer timeout
            response = requests.get(f"{self.server_url}/api/state", timeout=10)
            if response.status_code == 200:
                state_data = response.json()
                metrics = state_data.get("metrics", {})

                # 提取最终电梯状态（保持位置和乘客）
                elevators_state = []
                for elev in state_data.get("elevators", []):
                    position = elev.get("position", {})
                    current_floor = position.get("current_floor", 0) if position else elev.get("current_floor", 0)

                    # 转换乘客信息
                    passengers_info = []
                    passengers_dict = state_data.get("passengers", {})
                    for p_id in elev.get("passengers", []):
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
                        "direction": "idle",  # 模拟完成时都是idle
                        "passengers": passengers_info,
                        "capacity": elev.get("max_capacity", 8)
                    })

                print(f"[RealSimulation] Sending completion with {len(elevators_state)} elevators, "
                      f"{sum(len(e['passengers']) for e in elevators_state)} passengers still in elevators")

                # 发送完整的最终状态
                await self.websocket.send_json({
                    "type": "complete",
                    "tick": self.current_tick,
                    "elevators": elevators_state,  # 包含电梯位置和乘客
                    "waiting": {},  # 清空等待区
                    "stats": {
                        "total_passengers": len(self.traffic_events),
                        "waiting": 0,
                        "in_elevator": sum(len(e["passengers"]) for e in elevators_state),
                        "completed": metrics.get("completed_passengers", 0),
                        "avg_wait_time": round(metrics.get("average_floor_wait_time", 0), 2)
                    }
                })
                return
        except requests.exceptions.Timeout:
            print(f"[RealSimulation] Timeout getting final stats, using fallback")
        except Exception as e:
            print(f"[RealSimulation] Error getting final stats: {e}")

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

    async def _cleanup(self):
        """Clean up resources"""
        # Stop algorithm task
        if self.algorithm_task:
            self.algorithm_task.cancel()
            try:
                await self.algorithm_task
            except asyncio.CancelledError:
                pass

        # Stop server process
        if self.server_process:
            print(f"[RealSimulation] Stopping server")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()

    def pause(self):
        """Pause the simulation"""
        self.paused = True

    def resume(self):
        """Resume the simulation"""
        self.paused = False

    def stop(self):
        """Stop the simulation"""
        self.running = False

    def set_speed(self, speed: float):
        """Set simulation speed"""
        self.speed = max(0.1, min(10.0, speed))
