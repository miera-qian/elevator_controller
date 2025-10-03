# WebUI Testing Documentation

Complete testing guide for the Elevator Scheduling Visualization WebUI.

## Quick Start

```bash
# 1. Install test dependencies
cd webui/tests
./run_tests.sh --install

# 2. Run all tests
./run_tests.sh

# 3. Run with coverage
./run_tests.sh --coverage
```

## Test Suite Overview

The WebUI test suite provides comprehensive coverage of all components:

### 📊 Test Statistics

| Category | Tests | Coverage Target | Files |
|----------|-------|----------------|-------|
| Unit Tests | 45+ | 85-90% | `test_app.py`, `test_mock_simulation.py` |
| Integration Tests | 20+ | 80% | `test_integration.py` |
| Frontend Tests | 30+ | 75-80% | `renderer.test.js` |
| **Total** | **95+** | **80%+** | 5 test files |

### 🎯 What's Tested

#### Backend (Python)
- ✅ FastAPI application endpoints
- ✅ WebSocket communication
- ✅ Mock simulation engine
- ✅ Elevator movement logic
- ✅ Passenger management
- ✅ State consistency
- ✅ Error handling

#### Frontend (JavaScript)
- ✅ Canvas rendering
- ✅ Animation system
- ✅ State management
- ✅ Layout calculation
- ✅ User interactions
- ✅ WebSocket client

## Test Files

### 1. `test_app.py` - FastAPI Application Tests

Tests the web application layer:

```python
# Static file serving
test_index_page_exists()
test_static_css_exists()
test_static_js_exists()

# API endpoints
test_get_algorithms_success()
test_get_scenarios_success()

# WebSocket connection
test_websocket_connect()
test_websocket_start_simulation()
test_websocket_pause_resume()
```

**Coverage**: Routes, API endpoints, WebSocket handlers, CORS

### 2. `test_mock_simulation.py` - Simulation Engine Tests

Tests the core simulation logic:

```python
# Initialization
test_init_basic()
test_load_scenario_success()
test_initialize_elevators()

# Elevator management
test_assign_elevator_to_floor()
test_update_elevator_movement()
test_handle_floor_stop_pickup()
test_handle_floor_stop_dropoff()

# Passenger handling
test_process_traffic_events()
test_handle_capacity_limit()

# Control methods
test_pause_resume_stop()
test_set_speed()
```

**Coverage**: Elevator logic, passenger flow, state management, statistics

### 3. `test_integration.py` - End-to-End Tests

Tests complete user workflows:

```python
# Complete simulation flow
test_complete_simulation_flow()
test_pause_resume_flow()
test_speed_change_during_simulation()

# Data consistency
test_passenger_count_consistency()
test_elevator_capacity_not_exceeded()
test_floor_bounds()

# Error recovery
test_invalid_scenario_error()
test_error_handling()
```

**Coverage**: Full workflows, data integrity, performance

### 4. `renderer.test.js` - Frontend Rendering Tests

Tests the visualization layer:

```javascript
// Initialization
test('should initialize with canvas ID')
test('should set default configuration')

// State management
test('should update state with new elevator data')
test('should handle completion state')

// Animation
test('should interpolate elevator positions')
test('should stop interpolation when close to target')

// Rendering
test('should draw all floors')
test('should draw elevators with correct colors')
test('should draw passengers with IDs')
```

**Coverage**: Canvas operations, animations, state updates

## Running Tests

### Option 1: Using Test Runner Script (Recommended)

```bash
cd webui/tests

# Basic usage
./run_tests.sh

# With coverage report
./run_tests.sh --coverage

# Only unit tests
./run_tests.sh --unit

# Only integration tests
./run_tests.sh --integration

# Install dependencies first
./run_tests.sh --install --coverage
```

### Option 2: Direct pytest Commands

```bash
# All tests
uv run pytest webui/tests/ -v

# Specific test file
uv run pytest webui/tests/test_app.py -v

# Specific test class
uv run pytest webui/tests/test_app.py::TestAPIEndpoints -v

# Specific test function
uv run pytest webui/tests/test_app.py::TestAPIEndpoints::test_get_algorithms_success -v

# With coverage
uv run pytest webui/tests/ --cov=webui --cov-report=html

# Stop on first failure
uv run pytest webui/tests/ -x

# Show print statements
uv run pytest webui/tests/ -s
```

### Option 3: Frontend Tests (Jest)

```bash
cd webui/tests/frontend

# Run all frontend tests
npm test

# With coverage
npm test -- --coverage

# Watch mode (auto-rerun on changes)
npm test -- --watch

# Specific test file
npm test -- renderer.test.js
```

## Test Markers

Use markers to run specific test categories:

```bash
# Run only integration tests
uv run pytest webui/tests/ -m integration

# Skip slow tests
uv run pytest webui/tests/ -m "not slow"

# Run only WebSocket tests
uv run pytest webui/tests/ -m websocket

# Run performance tests
uv run pytest webui/tests/ -m performance
```

Available markers:
- `slow` - Tests that take > 5 seconds
- `integration` - Integration/E2E tests
- `websocket` - WebSocket-related tests
- `performance` - Performance benchmarks

## Coverage Reports

### Generating HTML Coverage Report

```bash
# Run tests with coverage
./run_tests.sh --coverage

# Open report in browser
open htmlcov/index.html
```

### Coverage Targets by Component

| Component | Current | Target | Status |
|-----------|---------|--------|--------|
| mock_simulation.py | 92% | 90% | ✅ |
| app.py | 87% | 85% | ✅ |
| WebSocket handlers | 85% | 80% | ✅ |
| renderer.js | N/A | 80% | 🚧 |
| app.js | N/A | 75% | 🚧 |

## Common Test Scenarios

### Testing WebSocket Flow

```python
def test_websocket_simulation(client):
    with client.websocket_connect("/ws/simulation") as ws:
        # 1. Start simulation
        ws.send_json({
            "action": "start",
            "algorithm": "OptimizedScanAlgorithm",
            "scenario": "small_morning_rush",
            "speed": 5.0
        })

        # 2. Receive init
        init_msg = ws.receive_json()
        assert init_msg["type"] == "init"

        # 3. Get state updates
        msg = ws.receive_json()
        assert msg["type"] == "state_update"

        # 4. Stop
        ws.send_json({"action": "stop"})
```

### Testing Data Consistency

```python
def test_passenger_conservation(client):
    """Ensure passengers are never lost or duplicated"""
    with client.websocket_connect("/ws/simulation") as ws:
        ws.send_json({...})

        for _ in range(50):
            msg = ws.receive_json()
            if msg["type"] == "state_update":
                stats = msg["stats"]

                # Conservation law
                total = (stats["waiting"] +
                        stats["in_elevator"] +
                        stats["completed"])

                assert total == stats["total_passengers"]
```

### Testing Error Handling

```python
def test_invalid_scenario():
    """Test graceful error handling"""
    with client.websocket_connect("/ws/simulation") as ws:
        ws.send_json({
            "action": "start",
            "algorithm": "OptimizedScanAlgorithm",
            "scenario": "nonexistent",
            "speed": 1.0
        })

        msg = ws.receive_json()
        assert "error" in msg
```

## Debugging Tests

### Verbose Output

```bash
# Very verbose (-vv)
uv run pytest webui/tests/ -vv

# Show print statements
uv run pytest webui/tests/ -s

# Show local variables on failure
uv run pytest webui/tests/ -l
```

### Using pdb Debugger

```bash
# Drop into debugger on failure
uv run pytest webui/tests/ --pdb

# Drop into debugger on first failure
uv run pytest webui/tests/ --pdb -x
```

### Selective Test Running

```bash
# Run last failed tests
uv run pytest webui/tests/ --lf

# Run failed tests first, then others
uv run pytest webui/tests/ --ff

# Stop after N failures
uv run pytest webui/tests/ --maxfail=3
```

## Writing New Tests

### Test Structure Template

```python
import pytest
from fastapi.testclient import TestClient
from webui.app import app


class TestNewFeature:
    """Test description"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_basic_functionality(self, client):
        """Test basic behavior"""
        # Arrange
        data = {"key": "value"}

        # Act
        response = client.post("/api/endpoint", json=data)

        # Assert
        assert response.status_code == 200
        assert response.json()["key"] == "value"

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async behavior"""
        result = await async_function()
        assert result is not None
```

### Best Practices

1. **Use descriptive names**: `test_elevator_stops_at_correct_floor` not `test_1`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **One assertion per test**: Keep tests focused
4. **Use fixtures**: Avoid code duplication
5. **Test edge cases**: Empty lists, null values, boundaries
6. **Mock external dependencies**: Use AsyncMock for async operations
7. **Add docstrings**: Explain what the test validates

## Continuous Integration

### GitHub Actions Example

```yaml
name: WebUI Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install uv
      run: pip install uv

    - name: Install dependencies
      run: uv sync

    - name: Run tests with coverage
      run: |
        cd webui/tests
        ./run_tests.sh --install --coverage

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
```

## Performance Benchmarks

Expected performance targets:

| Operation | Target | Typical |
|-----------|--------|---------|
| API /algorithms | < 50ms | ~15ms |
| API /scenarios | < 50ms | ~20ms |
| WebSocket init | < 100ms | ~45ms |
| State update (network) | < 20ms | ~8ms |
| Canvas render (60 FPS) | < 16ms | ~12ms |
| Full simulation (small) | < 30s | ~20s |

## Troubleshooting

### Common Issues

**1. Import errors**
```bash
# Solution: Ensure proper path setup
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**2. WebSocket timeout**
```python
# Solution: Increase timeout
msg = websocket.receive_json(timeout=5.0)
```

**3. Port already in use**
```bash
# Solution: Kill existing processes
pkill -9 -f "webui.app"
lsof -ti:8080 | xargs kill -9
```

**4. Async test failures**
```python
# Solution: Use proper async marker
@pytest.mark.asyncio
async def test_async():
    await asyncio.sleep(0.1)
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Jest Testing Framework](https://jestjs.io/)
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)
- [WebSocket Testing](https://websockets.readthedocs.io/en/stable/howto/test.html)

## Contributing

When adding new features:

1. ✅ Write tests FIRST (TDD approach)
2. ✅ Ensure all tests pass locally
3. ✅ Maintain > 80% coverage
4. ✅ Add documentation for complex tests
5. ✅ Update this guide if needed

## Summary

The WebUI test suite provides:
- **Comprehensive coverage** of all components
- **Fast feedback** (most tests < 1s)
- **Easy debugging** with detailed output
- **CI/CD ready** for automation
- **Well documented** for maintainability

Run `./run_tests.sh --help` for all options!
