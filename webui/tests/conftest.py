"""
Pytest configuration and shared fixtures for WebUI tests
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture(scope="session")
def test_data_dir():
    """Fixture providing test data directory"""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def sample_scenario_path(test_data_dir, tmp_path_factory):
    """Create a sample scenario file for testing"""
    import json

    scenario_data = {
        "building": {
            "floors": 6,
            "elevators": 2,
            "capacity": 8,
            "description": "Test scenario for unit tests",
            "duration": 100
        },
        "traffic": [
            {"id": 0, "tick": 0, "origin": 0, "destination": 2},
            {"id": 1, "tick": 0, "origin": 1, "destination": 3},
            {"id": 2, "tick": 5, "origin": 0, "destination": 4},
            {"id": 3, "tick": 5, "origin": 2, "destination": 0},
            {"id": 4, "tick": 10, "origin": 3, "destination": 1},
        ]
    }

    # Create temporary directory
    temp_dir = tmp_path_factory.mktemp("scenarios")
    scenario_file = temp_dir / "test_scenario.json"

    with open(scenario_file, 'w') as f:
        json.dump(scenario_data, f)

    return scenario_file


@pytest.fixture
def mock_building_config():
    """Fixture providing mock building configuration"""
    return {
        "floors": 10,
        "elevators": 3,
        "capacity": 8,
        "description": "Mock building for testing"
    }


@pytest.fixture
def mock_traffic_data():
    """Fixture providing mock traffic data"""
    return [
        {"id": i, "tick": i * 5, "origin": i % 5, "destination": (i + 2) % 5}
        for i in range(20)
    ]


@pytest.fixture(autouse=True)
def reset_test_state():
    """Automatically reset state before each test"""
    # Setup
    yield
    # Teardown - could add cleanup here if needed


# Custom markers
def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "websocket: marks tests that use WebSocket connections"
    )
