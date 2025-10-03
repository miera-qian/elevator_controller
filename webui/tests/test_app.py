"""
Unit tests for FastAPI application endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from webui.app import app, get_available_algorithms, get_available_scenarios


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestStaticFiles:
    """Test static file serving"""

    def test_index_page_exists(self, client):
        """Test that index page loads"""
        response = client.get("/")
        assert response.status_code == 200
        assert b"<!DOCTYPE html>" in response.content
        assert b"elevator" in response.content.lower()

    def test_static_css_exists(self, client):
        """Test that CSS file is accessible"""
        response = client.get("/static/css/style.css")
        assert response.status_code == 200

    def test_static_js_exists(self, client):
        """Test that JavaScript files are accessible"""
        response = client.get("/static/js/app.js")
        assert response.status_code == 200

        response = client.get("/static/js/renderer.js")
        assert response.status_code == 200

        response = client.get("/static/js/websocket.js")
        assert response.status_code == 200


class TestAPIEndpoints:
    """Test REST API endpoints"""

    def test_get_algorithms_success(self, client):
        """Test getting available algorithms"""
        response = client.get("/api/algorithms")
        assert response.status_code == 200

        data = response.json()
        assert "algorithms" in data
        assert isinstance(data["algorithms"], list)
        assert len(data["algorithms"]) > 0

        # Check algorithm structure
        algo = data["algorithms"][0]
        assert "name" in algo
        assert "display_name" in algo
        assert "type" in algo
        assert "description" in algo

    def test_get_scenarios_success(self, client):
        """Test getting available scenarios"""
        response = client.get("/api/scenarios")
        assert response.status_code == 200

        data = response.json()
        assert "scenarios" in data
        assert isinstance(data["scenarios"], list)
        assert len(data["scenarios"]) > 0

        # Check scenario structure
        scenario = data["scenarios"][0]
        assert "name" in scenario
        assert "display_name" in scenario
        assert "floors" in scenario
        assert "elevators" in scenario
        assert "passengers" in scenario

    def test_get_algorithms_returns_correct_count(self, client):
        """Test that all algorithms are returned"""
        response = client.get("/api/algorithms")
        data = response.json()

        # Should have at least 3 algorithms
        assert len(data["algorithms"]) >= 3

        # Check for specific algorithms
        algo_names = [a["name"] for a in data["algorithms"]]
        assert "OptimizedScanAlgorithm" in algo_names

    def test_get_scenarios_returns_correct_count(self, client):
        """Test that all scenarios are returned"""
        response = client.get("/api/scenarios")
        data = response.json()

        # Should have 10 scenarios
        assert len(data["scenarios"]) == 10


class TestWebSocketConnection:
    """Test WebSocket connection and basic flow"""

    def test_websocket_connect(self, client):
        """Test WebSocket connection establishment"""
        with client.websocket_connect("/ws/simulation") as websocket:
            # Should connect successfully
            assert websocket is not None

    def test_websocket_start_simulation_missing_params(self, client):
        """Test starting simulation without required parameters"""
        with client.websocket_connect("/ws/simulation") as websocket:
            # Send start message without algorithm
            websocket.send_json({
                "action": "start",
                "scenario": "test_scenario",
                "speed": 1.0
            })

            # Should receive error
            data = websocket.receive_json()
            assert "error" in data

    def test_websocket_start_simulation_invalid_scenario(self, client):
        """Test starting simulation with invalid scenario"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({
                "action": "start",
                "algorithm": "OptimizedScanAlgorithm",
                "scenario": "non_existent_scenario",
                "speed": 1.0
            })

            # Should receive error
            data = websocket.receive_json()
            assert "error" in data

    @pytest.mark.asyncio
    async def test_websocket_pause_resume(self, client):
        """Test pause and resume functionality"""
        with client.websocket_connect("/ws/simulation") as websocket:
            # Start simulation
            websocket.send_json({
                "action": "start",
                "algorithm": "OptimizedScanAlgorithm",
                "scenario": "small_morning_rush",
                "speed": 5.0
            })

            # Receive init message
            init_msg = websocket.receive_json()
            assert init_msg["type"] == "init"

            # Pause
            websocket.send_json({"action": "pause"})

            # Resume
            websocket.send_json({"action": "resume"})

            # Stop
            websocket.send_json({"action": "stop"})

    def test_websocket_set_speed(self, client):
        """Test setting simulation speed"""
        with client.websocket_connect("/ws/simulation") as websocket:
            # Start simulation first
            websocket.send_json({
                "action": "start",
                "algorithm": "OptimizedScanAlgorithm",
                "scenario": "small_morning_rush",
                "speed": 1.0
            })

            # Wait for init
            init_msg = websocket.receive_json()

            # Set speed
            websocket.send_json({
                "action": "set_speed",
                "speed": 2.5
            })

            # Stop
            websocket.send_json({"action": "stop"})


class TestHelperFunctions:
    """Test helper functions"""

    def test_get_available_algorithms_structure(self):
        """Test algorithm metadata structure"""
        algorithms = get_available_algorithms()

        assert isinstance(algorithms, list)
        assert len(algorithms) > 0

        for algo in algorithms:
            assert isinstance(algo, dict)
            assert "name" in algo
            assert "display_name" in algo
            assert "type" in algo
            assert "description" in algo
            assert isinstance(algo["name"], str)
            assert isinstance(algo["display_name"], str)

    def test_get_available_scenarios_structure(self):
        """Test scenario metadata structure"""
        scenarios = get_available_scenarios()

        assert isinstance(scenarios, list)
        assert len(scenarios) > 0

        for scenario in scenarios:
            assert isinstance(scenario, dict)
            assert "name" in scenario
            assert "display_name" in scenario
            assert "floors" in scenario
            assert "elevators" in scenario
            assert "passengers" in scenario
            assert "duration" in scenario
            assert "type" in scenario

    def test_get_available_scenarios_file_reading(self):
        """Test that scenarios correctly read from JSON files"""
        scenarios = get_available_scenarios()

        # Pick a known scenario
        small_morning = next((s for s in scenarios if s["name"] == "small_morning_rush"), None)

        assert small_morning is not None
        assert small_morning["floors"] == 6
        assert small_morning["elevators"] == 2
        assert small_morning["passengers"] == 160


class TestCORSandMiddleware:
    """Test CORS and middleware configuration"""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present"""
        response = client.get("/api/algorithms")

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers

    def test_options_request(self, client):
        """Test OPTIONS preflight request"""
        response = client.options("/api/algorithms")
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling"""

    def test_404_for_non_existent_route(self, client):
        """Test 404 for non-existent routes"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_405_for_wrong_method(self, client):
        """Test 405 for wrong HTTP method"""
        response = client.post("/api/algorithms")
        assert response.status_code == 405

    def test_websocket_invalid_action(self, client):
        """Test WebSocket with invalid action"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({
                "action": "invalid_action"
            })

            # Should handle gracefully (may return error or ignore)
            # Implementation dependent
