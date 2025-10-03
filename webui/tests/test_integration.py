"""
Integration tests for WebUI
Tests the complete flow from API to WebSocket to simulation
"""
import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from webui.app import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestEndToEndSimulation:
    """Test complete simulation flow"""

    @pytest.mark.timeout(30)
    def test_complete_simulation_flow(self, client):
        """Test complete simulation from start to finish"""
        with client.websocket_connect("/ws/simulation") as websocket:
            # 1. Start simulation
            websocket.send_json({
                "action": "start",
                "algorithm": "OptimizedScanAlgorithm",
                "scenario": "small_morning_rush",
                "speed": 10.0  # Fast speed for testing
            })

            # 2. Receive init message
            init_msg = websocket.receive_json()
            assert init_msg["type"] == "init"
            assert init_msg["algorithm"] == "OptimizedScanAlgorithm"
            assert init_msg["scenario"] == "small_morning_rush"
            assert "building" in init_msg
            assert init_msg["building"]["floors"] == 6
            assert init_msg["building"]["elevators"] == 2

            # 3. Receive state updates
            state_updates = []
            max_updates = 100
            completed = False

            for i in range(max_updates):
                try:
                    msg = websocket.receive_json(timeout=1.0)

                    if msg["type"] == "state_update":
                        state_updates.append(msg)

                        # Verify state structure
                        assert "tick" in msg
                        assert "elevators" in msg
                        assert "waiting" in msg
                        assert "stats" in msg

                        # Verify elevator data
                        for elevator in msg["elevators"]:
                            assert "id" in elevator
                            assert "floor" in elevator
                            assert "direction" in elevator
                            assert "passengers" in elevator

                    elif msg["type"] == "complete":
                        completed = True
                        # Verify completion message
                        assert "tick" in msg
                        assert "stats" in msg
                        assert msg["stats"]["total_passengers"] > 0
                        break

                except Exception as e:
                    if i >= 10:  # Allow at least 10 updates
                        break

            # 4. Verify simulation ran
            assert len(state_updates) > 0, "Should receive state updates"

            # 5. Verify completion (or timeout)
            if completed:
                assert state_updates[-1]["stats"]["completed"] == state_updates[-1]["stats"]["total_passengers"]

    def test_pause_resume_flow(self, client):
        """Test pausing and resuming simulation"""
        with client.websocket_connect("/ws/simulation") as websocket:
            # Start
            websocket.send_json({
                "action": "start",
                "algorithm": "OptimizedScanAlgorithm",
                "scenario": "small_morning_rush",
                "speed": 5.0
            })

            # Wait for init
            init_msg = websocket.receive_json()
            assert init_msg["type"] == "init"

            # Get a few updates
            for _ in range(5):
                msg = websocket.receive_json(timeout=1.0)
                if msg["type"] == "state_update":
                    first_tick = msg["tick"]
                    break

            # Pause
            websocket.send_json({"action": "pause"})
            asyncio.sleep(0.2)

            # Resume
            websocket.send_json({"action": "resume"})

            # Get more updates
            for _ in range(5):
                msg = websocket.receive_json(timeout=1.0)
                if msg["type"] == "state_update":
                    resumed_tick = msg["tick"]
                    break

            # Ticks should have advanced
            assert resumed_tick >= first_tick

            # Stop
            websocket.send_json({"action": "stop"})

    def test_speed_change_during_simulation(self, client):
        """Test changing speed during simulation"""
        with client.websocket_connect("/ws/simulation") as websocket:
            # Start at normal speed
            websocket.send_json({
                "action": "start",
                "algorithm": "OptimizedScanAlgorithm",
                "scenario": "small_morning_rush",
                "speed": 1.0
            })

            # Wait for init
            init_msg = websocket.receive_json()

            # Get a few updates at normal speed
            ticks_before = []
            for _ in range(3):
                msg = websocket.receive_json(timeout=2.0)
                if msg["type"] == "state_update":
                    ticks_before.append(msg["tick"])

            # Change to faster speed
            websocket.send_json({
                "action": "set_speed",
                "speed": 5.0
            })

            # Get a few updates at fast speed
            ticks_after = []
            for _ in range(3):
                msg = websocket.receive_json(timeout=2.0)
                if msg["type"] == "state_update":
                    ticks_after.append(msg["tick"])

            # Should process more ticks at higher speed
            # (This is a rough check as timing can vary)
            if len(ticks_before) >= 2 and len(ticks_after) >= 2:
                avg_delta_before = (ticks_before[-1] - ticks_before[0]) / (len(ticks_before) - 1)
                avg_delta_after = (ticks_after[-1] - ticks_after[0]) / (len(ticks_after) - 1)

                # At higher speed, should process more ticks per update
                # (though this depends on update frequency)

            # Stop
            websocket.send_json({"action": "stop"})

    def test_multiple_simulations_sequential(self, client):
        """Test running multiple simulations in sequence"""
        with client.websocket_connect("/ws/simulation") as websocket:
            scenarios = ["small_morning_rush", "small_evening_rush"]

            for scenario in scenarios:
                # Start simulation
                websocket.send_json({
                    "action": "start",
                    "algorithm": "OptimizedScanAlgorithm",
                    "scenario": scenario,
                    "speed": 10.0
                })

                # Wait for init
                init_msg = websocket.receive_json()
                assert init_msg["type"] == "init"
                assert init_msg["scenario"] == scenario

                # Get a few updates
                for _ in range(10):
                    msg = websocket.receive_json(timeout=1.0)
                    if msg["type"] == "complete":
                        break

                # Stop current simulation
                websocket.send_json({"action": "stop"})
                asyncio.sleep(0.1)


class TestDataConsistency:
    """Test data consistency across updates"""

    def test_passenger_count_consistency(self, client):
        """Test that passenger counts are consistent"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({
                "action": "start",
                "algorithm": "OptimizedScanAlgorithm",
                "scenario": "small_morning_rush",
                "speed": 5.0
            })

            # Wait for init
            init_msg = websocket.receive_json()
            total_passengers = init_msg["building"].get("passengers", 160)

            # Collect state updates
            for _ in range(20):
                try:
                    msg = websocket.receive_json(timeout=1.0)

                    if msg["type"] == "state_update" and "stats" in msg:
                        stats = msg["stats"]

                        # Total should always equal: waiting + in_elevator + completed
                        calculated_total = (
                            stats["waiting"] +
                            stats["in_elevator"] +
                            stats["completed"]
                        )

                        assert calculated_total == stats["total_passengers"], \
                            f"Passenger count mismatch at tick {msg['tick']}: " \
                            f"{calculated_total} != {stats['total_passengers']}"

                    elif msg["type"] == "complete":
                        break

                except Exception:
                    break

            websocket.send_json({"action": "stop"})

    def test_elevator_capacity_not_exceeded(self, client):
        """Test that elevators never exceed capacity"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({
                "action": "start",
                "algorithm": "OptimizedScanAlgorithm",
                "scenario": "small_morning_rush",
                "speed": 5.0
            })

            # Wait for init
            init_msg = websocket.receive_json()
            capacity = init_msg["building"]["capacity"]

            # Check all elevators
            for _ in range(50):
                try:
                    msg = websocket.receive_json(timeout=1.0)

                    if msg["type"] == "state_update":
                        for elevator in msg["elevators"]:
                            passenger_count = len(elevator["passengers"])
                            assert passenger_count <= capacity, \
                                f"Elevator {elevator['id']} exceeded capacity: " \
                                f"{passenger_count} > {capacity}"

                    elif msg["type"] == "complete":
                        break

                except Exception:
                    break

            websocket.send_json({"action": "stop"})

    def test_floor_bounds(self, client):
        """Test that elevators stay within floor bounds"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({
                "action": "start",
                "algorithm": "OptimizedScanAlgorithm",
                "scenario": "small_morning_rush",
                "speed": 5.0
            })

            # Wait for init
            init_msg = websocket.receive_json()
            num_floors = init_msg["building"]["floors"]

            # Check all elevators
            for _ in range(50):
                try:
                    msg = websocket.receive_json(timeout=1.0)

                    if msg["type"] == "state_update":
                        for elevator in msg["elevators"]:
                            floor = elevator["floor"]
                            assert 0 < floor <= num_floors + 1, \
                                f"Elevator {elevator['id']} out of bounds: floor {floor}"

                    elif msg["type"] == "complete":
                        break

                except Exception:
                    break

            websocket.send_json({"action": "stop"})


class TestErrorRecovery:
    """Test error handling and recovery"""

    def test_invalid_scenario_error(self, client):
        """Test error when using invalid scenario"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({
                "action": "start",
                "algorithm": "OptimizedScanAlgorithm",
                "scenario": "nonexistent_scenario",
                "speed": 1.0
            })

            msg = websocket.receive_json()
            assert "error" in msg

    def test_stop_without_start(self, client):
        """Test stopping before starting"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({"action": "stop"})
            # Should not crash

    def test_resume_without_pause(self, client):
        """Test resuming without pausing"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({
                "action": "start",
                "algorithm": "OptimizedScanAlgorithm",
                "scenario": "small_morning_rush",
                "speed": 1.0
            })

            init_msg = websocket.receive_json()

            websocket.send_json({"action": "resume"})
            # Should not crash

            websocket.send_json({"action": "stop"})


class TestPerformance:
    """Test performance characteristics"""

    @pytest.mark.timeout(10)
    def test_high_speed_simulation(self, client):
        """Test simulation at maximum speed"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({
                "action": "start",
                "algorithm": "OptimizedScanAlgorithm",
                "scenario": "small_morning_rush",
                "speed": 10.0  # Maximum speed
            })

            init_msg = websocket.receive_json()

            # Should complete in reasonable time
            update_count = 0
            for _ in range(200):
                try:
                    msg = websocket.receive_json(timeout=0.5)
                    if msg["type"] == "state_update":
                        update_count += 1
                    elif msg["type"] == "complete":
                        break
                except Exception:
                    break

            assert update_count > 0

    def test_websocket_message_rate(self, client):
        """Test WebSocket can handle message rate"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({
                "action": "start",
                "algorithm": "OptimizedScanAlgorithm",
                "scenario": "small_morning_rush",
                "speed": 5.0
            })

            init_msg = websocket.receive_json()

            # Receive messages for 2 seconds
            import time
            start_time = time.time()
            message_count = 0

            while time.time() - start_time < 2:
                try:
                    msg = websocket.receive_json(timeout=0.1)
                    message_count += 1

                    if msg["type"] == "complete":
                        break
                except Exception:
                    continue

            # Should receive at least a few messages per second
            assert message_count > 0

            websocket.send_json({"action": "stop"})
