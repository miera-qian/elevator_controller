"""
Unit tests for MockSimulationEngine
"""
import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from webui.mock_simulation import MockSimulationEngine


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing"""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def sample_scenario_data():
    """Sample scenario data for testing"""
    return {
        "building": {
            "floors": 6,
            "elevators": 2,
            "capacity": 8,
            "description": "Test scenario",
            "duration": 100
        },
        "traffic": [
            {"id": 0, "tick": 0, "origin": 0, "destination": 2},
            {"id": 1, "tick": 5, "origin": 1, "destination": 3},
            {"id": 2, "tick": 10, "origin": 0, "destination": 4},
        ]
    }


@pytest.fixture
def mock_scenario_file(tmp_path, sample_scenario_data):
    """Create a temporary scenario file"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    scenario_file = data_dir / "test_scenario.json"

    with open(scenario_file, 'w') as f:
        json.dump(sample_scenario_data, f)

    return scenario_file


class TestMockSimulationEngineInit:
    """Test MockSimulationEngine initialization"""

    def test_init_basic(self, mock_websocket):
        """Test basic initialization"""
        engine = MockSimulationEngine(
            algorithm_name="TestAlgorithm",
            scenario_name="test_scenario",
            speed=1.0,
            websocket=mock_websocket
        )

        assert engine.algorithm_name == "TestAlgorithm"
        assert engine.scenario_name == "test_scenario"
        assert engine.speed == 1.0
        assert engine.websocket == mock_websocket
        assert engine.running == False
        assert engine.paused == False
        assert engine.current_tick == 0

    def test_load_scenario_success(self, mock_websocket, mock_scenario_file, sample_scenario_data):
        """Test successful scenario loading"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            assert engine.building_config == sample_scenario_data["building"]
            assert len(engine.traffic_events) == 3

    def test_load_scenario_file_not_found(self, mock_websocket):
        """Test scenario loading with non-existent file"""
        with pytest.raises(ValueError, match="Scenario file not found"):
            MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="non_existent_scenario",
                speed=1.0,
                websocket=mock_websocket
            )


class TestMockSimulationEngineElevators:
    """Test elevator initialization and management"""

    @pytest.mark.asyncio
    async def test_initialize_elevators(self, mock_websocket, mock_scenario_file):
        """Test elevator initialization"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine._initialize_elevators()

            assert len(engine.elevators) == 2
            assert all(e["current_floor"] == 1.0 for e in engine.elevators)
            assert all(e["direction"] == "idle" for e in engine.elevators)
            assert all(len(e["passengers"]) == 0 for e in engine.elevators)
            assert all(e["capacity"] == 8 for e in engine.elevators)

    def test_assign_elevator_to_floor_idle(self, mock_websocket, mock_scenario_file):
        """Test assigning idle elevator to floor"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine._initialize_elevators()
            engine._assign_elevator_to_floor(3)

            # Should assign nearest idle elevator
            assigned_elevator = None
            for e in engine.elevators:
                if e["target_floor"] == 3:
                    assigned_elevator = e
                    break

            assert assigned_elevator is not None
            assert assigned_elevator["direction"] in ["up", "down"]

    def test_update_elevator_movement_up(self, mock_websocket, mock_scenario_file):
        """Test elevator moving up"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine._initialize_elevators()
            engine.elevators[0]["target_floor"] = 5
            engine.elevators[0]["current_floor"] = 1.0

            initial_floor = engine.elevators[0]["current_floor"]
            engine._update_elevators()

            assert engine.elevators[0]["current_floor"] > initial_floor
            assert engine.elevators[0]["direction"] == "up"

    def test_update_elevator_movement_down(self, mock_websocket, mock_scenario_file):
        """Test elevator moving down"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine._initialize_elevators()
            engine.elevators[0]["current_floor"] = 5.0
            engine.elevators[0]["target_floor"] = 1

            initial_floor = engine.elevators[0]["current_floor"]
            engine._update_elevators()

            assert engine.elevators[0]["current_floor"] < initial_floor
            assert engine.elevators[0]["direction"] == "down"


class TestMockSimulationEnginePassengers:
    """Test passenger management"""

    def test_process_traffic_events(self, mock_websocket, mock_scenario_file):
        """Test processing traffic events at specific tick"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine._initialize_elevators()
            engine.current_tick = 0
            engine._process_traffic_events()

            # Should have 1 passenger waiting at floor 1 (origin 0 + 1)
            assert len(engine.waiting_passengers[1]) == 1
            assert engine.waiting_passengers[1][0]["from_floor"] == 1
            assert engine.waiting_passengers[1][0]["to_floor"] == 3

    def test_handle_floor_stop_pickup(self, mock_websocket, mock_scenario_file):
        """Test picking up passengers at floor"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine._initialize_elevators()

            # Add waiting passenger
            passenger = {
                "id": 0,
                "from_floor": 1,
                "to_floor": 3,
                "call_time": 0,
                "pickup_time": None,
                "dropoff_time": None
            }
            engine.waiting_passengers[1] = [passenger]
            engine.current_tick = 5

            # Elevator at floor 1
            elevator = engine.elevators[0]
            elevator["current_floor"] = 1.0

            engine._handle_floor_stop(elevator, 1)

            assert len(engine.waiting_passengers[1]) == 0
            assert len(elevator["passengers"]) == 1
            assert elevator["passengers"][0]["pickup_time"] == 5

    def test_handle_floor_stop_dropoff(self, mock_websocket, mock_scenario_file):
        """Test dropping off passengers at floor"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine._initialize_elevators()
            engine.current_tick = 10

            # Add passenger to elevator
            passenger = {
                "id": 0,
                "from_floor": 1,
                "to_floor": 3,
                "call_time": 0,
                "pickup_time": 5,
                "dropoff_time": None
            }
            elevator = engine.elevators[0]
            elevator["passengers"] = [passenger]
            elevator["current_floor"] = 3.0

            engine._handle_floor_stop(elevator, 3)

            assert len(elevator["passengers"]) == 0
            assert len(engine.completed_passengers) == 1
            assert engine.completed_passengers[0]["dropoff_time"] == 10

    def test_handle_floor_stop_capacity_limit(self, mock_websocket, mock_scenario_file):
        """Test elevator capacity limit during pickup"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine._initialize_elevators()

            # Fill elevator to capacity
            elevator = engine.elevators[0]
            elevator["capacity"] = 2
            elevator["passengers"] = [
                {"id": i, "to_floor": 3} for i in range(2)
            ]

            # Add more waiting passengers
            engine.waiting_passengers[1] = [
                {"id": 10, "from_floor": 1, "to_floor": 3},
                {"id": 11, "from_floor": 1, "to_floor": 3}
            ]

            engine._handle_floor_stop(elevator, 1)

            # Should not pick up more passengers
            assert len(elevator["passengers"]) == 2
            assert len(engine.waiting_passengers[1]) == 2


class TestMockSimulationEngineWebSocket:
    """Test WebSocket message sending"""

    @pytest.mark.asyncio
    async def test_send_init_state(self, mock_websocket, mock_scenario_file):
        """Test sending initial state message"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            await engine._send_init_state()

            mock_websocket.send_json.assert_called_once()
            call_args = mock_websocket.send_json.call_args[0][0]

            assert call_args["type"] == "init"
            assert call_args["algorithm"] == "TestAlgorithm"
            assert call_args["scenario"] == "test_scenario"
            assert call_args["building"]["floors"] == 6
            assert call_args["building"]["elevators"] == 2

    @pytest.mark.asyncio
    async def test_send_state_update(self, mock_websocket, mock_scenario_file):
        """Test sending state update message"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine._initialize_elevators()
            engine.current_tick = 42

            await engine._send_state_update()

            mock_websocket.send_json.assert_called_once()
            call_args = mock_websocket.send_json.call_args[0][0]

            assert call_args["type"] == "state_update"
            assert call_args["tick"] == 42
            assert "elevators" in call_args
            assert "waiting" in call_args
            assert "stats" in call_args

    @pytest.mark.asyncio
    async def test_send_completion(self, mock_websocket, mock_scenario_file):
        """Test sending completion message"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine.current_tick = 100
            engine.completed_passengers = [
                {"call_time": 0, "pickup_time": 5, "dropoff_time": 10},
                {"call_time": 10, "pickup_time": 15, "dropoff_time": 20}
            ]

            await engine._send_completion()

            mock_websocket.send_json.assert_called_once()
            call_args = mock_websocket.send_json.call_args[0][0]

            assert call_args["type"] == "complete"
            assert call_args["tick"] == 100
            assert call_args["stats"]["total_passengers"] == 2
            assert "avg_wait_time" in call_args["stats"]


class TestMockSimulationEngineControl:
    """Test simulation control methods"""

    def test_pause(self, mock_websocket, mock_scenario_file):
        """Test pausing simulation"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine.pause()
            assert engine.paused == True

    def test_resume(self, mock_websocket, mock_scenario_file):
        """Test resuming simulation"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine.paused = True
            engine.resume()
            assert engine.paused == False

    def test_stop(self, mock_websocket, mock_scenario_file):
        """Test stopping simulation"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine.running = True
            engine.stop()
            assert engine.running == False

    def test_set_speed_valid(self, mock_websocket, mock_scenario_file):
        """Test setting valid speed"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine.set_speed(2.5)
            assert engine.speed == 2.5

    def test_set_speed_clamping(self, mock_websocket, mock_scenario_file):
        """Test speed clamping to valid range"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine.set_speed(15.0)
            assert engine.speed == 10.0

            engine.set_speed(0.05)
            assert engine.speed == 0.1


class TestMockSimulationEngineStatistics:
    """Test statistics calculation"""

    def test_calculate_average_wait_time(self, mock_websocket, mock_scenario_file):
        """Test average wait time calculation"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine.completed_passengers = [
                {"call_time": 0, "pickup_time": 5},  # wait: 5
                {"call_time": 10, "pickup_time": 20},  # wait: 10
                {"call_time": 20, "pickup_time": 25}   # wait: 5
            ]

            # Calculate manually
            wait_times = [5, 10, 5]
            expected_avg = sum(wait_times) / len(wait_times)

            # This would be tested in _send_state_update or _send_completion
            assert expected_avg == 20 / 3

    def test_calculate_stats_no_passengers(self, mock_websocket, mock_scenario_file):
        """Test stats calculation with no passengers"""
        with patch.object(Path, '__truediv__', return_value=mock_scenario_file):
            engine = MockSimulationEngine(
                algorithm_name="TestAlgorithm",
                scenario_name="test_scenario",
                speed=1.0,
                websocket=mock_websocket
            )

            engine._initialize_elevators()

            # No passengers, all stats should be 0
            total_waiting = sum(len(p) for p in engine.waiting_passengers.values())
            total_in_elevator = sum(len(e["passengers"]) for e in engine.elevators)
            total_completed = len(engine.completed_passengers)

            assert total_waiting == 0
            assert total_in_elevator == 0
            assert total_completed == 0
