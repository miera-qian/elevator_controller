# Quick Start Guide - Adding Your Own Algorithm

> **Goal**: Add a custom elevator scheduling algorithm in 15 minutes

## 📋 Prerequisites

- Python 3.12+
- Project dependencies installed (`uv sync`)
- Basic understanding of Python classes

## 🚀 Step-by-Step Guide

### Step 1: Create Your Algorithm File

Create a new file in the `algo/` directory:

```bash
# Create your algorithm file
touch algo/my_algorithm.py
```

### Step 2: Implement the Algorithm

Copy this template into `algo/my_algorithm.py`:

```python
"""
My Custom Elevator Algorithm
"""
from algo.base_algorithm import BaseAlgorithm


class MyAlgorithm(BaseAlgorithm):
    """
    Your custom elevator scheduling algorithm

    This is a simple template. Implement your logic in the callback methods.
    """

    def __init__(self, enable_logging: bool = False):
        """Initialize your algorithm"""
        super().__init__(enable_logging=enable_logging)
        # Add your custom initialization here
        self.name = "MyAlgorithm"

    def on_passenger_call(self, passenger, elevators):
        """
        Called when a passenger calls an elevator

        Args:
            passenger: Passenger object with attributes:
                - id: Passenger ID
                - origin: Origin floor
                - destination: Destination floor
            elevators: List of Elevator objects

        Returns:
            Elevator object to assign, or None
        """
        # Simple strategy: Find the nearest idle elevator
        idle_elevators = [e for e in elevators if not e.passengers and not e.destination_floor]

        if idle_elevators:
            # Find closest idle elevator
            closest = min(idle_elevators, key=lambda e: abs(e.current_floor - passenger.origin))
            return closest

        return None

    def on_elevator_idle(self, elevator, waiting_passengers):
        """
        Called when an elevator becomes idle

        Args:
            elevator: The idle Elevator object
            waiting_passengers: List of waiting Passenger objects

        Returns:
            Floor number to send elevator to, or None
        """
        if not waiting_passengers:
            return None

        # Go to the nearest waiting passenger
        nearest = min(waiting_passengers, key=lambda p: abs(elevator.current_floor - p.origin))
        return nearest.origin

    def on_elevator_approaching(self, elevator, floor, passengers_waiting, passengers_in_elevator):
        """
        Called when elevator is approaching a floor

        Args:
            elevator: The Elevator object
            floor: Floor number being approached
            passengers_waiting: List of passengers waiting at this floor
            passengers_in_elevator: List of passengers in the elevator

        Returns:
            Boolean - True to stop, False to continue
        """
        # Stop if any passenger wants to get off or on at this floor
        for passenger in passengers_in_elevator:
            if passenger.destination == floor:
                return True

        for passenger in passengers_waiting:
            if passenger.origin == floor:
                return True

        return False

    def on_passenger_board(self, elevator, passenger):
        """
        Called when a passenger boards an elevator

        Args:
            elevator: The Elevator object
            passenger: The Passenger object

        Returns:
            Boolean - True to register destination, False otherwise
        """
        # Always register the passenger's destination
        return True
```

### Step 3: Register Your Algorithm

Edit `algo/__init__.py` to export your algorithm:

```python
# algo/__init__.py
from .base_algorithm import BaseAlgorithm
from .optimized_scan import OptimizedScanAlgorithm
from .rl_dqn import RLDQNAlgorithm
from .hybrid_scan_rl import HybridScanRLAlgorithm
from .my_algorithm import MyAlgorithm  # Add this line

__all__ = [
    'BaseAlgorithm',
    'OptimizedScanAlgorithm',
    'RLDQNAlgorithm',
    'HybridScanRLAlgorithm',
    'MyAlgorithm',  # Add this line
]
```

### Step 4: Test Your Algorithm

#### Option 1: Quick Test with CLI

```bash
# Test with a small scenario
uv run python main.py run --algorithm MyAlgorithm
```

#### Option 2: Automated Test

```bash
# Test on small scenarios (5-10 minutes)
uv run python tests/auto_test.py \
    --algorithms MyAlgorithm \
    --scenarios small_morning_rush,small_evening_rush,small_burst_traffic
```

#### Option 3: Full Test Suite

```bash
# Test on all scenarios (20-40 minutes)
uv run python tests/auto_test.py --algorithms MyAlgorithm
```

### Step 5: View Results

After running tests, check the generated report:

```bash
# View the latest report
ls -lt docs/auto_test_report_*.md | head -1

# Open it (macOS)
open $(ls -t docs/auto_test_report_*.md | head -1)
```

## 📚 Available Methods

Your algorithm class can override these methods:

| Method | Called When | Return Value |
|--------|------------|--------------|
| `on_passenger_call()` | Passenger calls elevator | Elevator to assign (or None) |
| `on_elevator_idle()` | Elevator becomes idle | Floor to go to (or None) |
| `on_elevator_approaching()` | Elevator approaching floor | True to stop, False to continue |
| `on_passenger_board()` | Passenger boards elevator | True to register destination |

## 🎯 Algorithm Strategies

### Strategy 1: Nearest Elevator
```python
def on_passenger_call(self, passenger, elevators):
    """Assign nearest available elevator"""
    available = [e for e in elevators if len(e.passengers) < e.capacity]
    if available:
        return min(available, key=lambda e: abs(e.current_floor - passenger.origin))
    return None
```

### Strategy 2: Direction-Aware
```python
def on_passenger_call(self, passenger, elevators):
    """Prefer elevators moving in the same direction"""
    direction = 1 if passenger.destination > passenger.origin else -1

    for elevator in elevators:
        if elevator.direction == direction:
            # Check if elevator will pass by
            if self._will_pass_by(elevator, passenger.origin, direction):
                return elevator

    return None
```

### Strategy 3: Load Balancing
```python
def on_passenger_call(self, passenger, elevators):
    """Balance load across elevators"""
    # Score each elevator (lower is better)
    def score(e):
        distance = abs(e.current_floor - passenger.origin)
        load = len(e.passengers) / e.capacity
        return distance + load * 10  # Weight load heavily

    return min(elevators, key=score)
```

## 🔍 Debugging Tips

### 1. Enable Logging

```python
algorithm = MyAlgorithm(enable_logging=True)
```

### 2. Print Debug Info

```python
def on_passenger_call(self, passenger, elevators):
    print(f"Passenger {passenger.id}: {passenger.origin} → {passenger.destination}")
    print(f"Elevators: {[(e.id, e.current_floor) for e in elevators]}")
    # ... your logic
```

### 3. Use the WebUI for Visualization

```bash
# Start WebUI to see elevator movements (uses Mock engine, not your algorithm)
uv run python -m webui.app
```

**Note**: WebUI currently uses a simplified mock engine, not real algorithms. Use it for visual reference only.

## 📊 Performance Metrics

After testing, you'll see these metrics:

| Metric | Description | Goal |
|--------|-------------|------|
| **Average Wait Time** | Average time passengers wait for pickup | < 120 ticks |
| **P95 Wait Time** | 95% of passengers wait less than this | < 200 ticks |
| **Average System Time** | Time from call to destination | < 150 ticks |
| **Completion Rate** | Percentage of passengers served | 100% |

### Baseline Performance

| Building Size | Good | Acceptable | Needs Improvement |
|---------------|------|------------|-------------------|
| Small (6 floors) | < 80 | 80-120 | > 120 |
| Medium (10 floors) | < 100 | 100-150 | > 150 |
| Large (15-20 floors) | < 140 | 140-200 | > 200 |

*Values in ticks (average wait time)*

## 🎓 Example: FCFS Algorithm

Here's a complete example of a First-Come-First-Served algorithm:

```python
"""
FCFS (First-Come-First-Served) Algorithm
"""
from algo.base_algorithm import BaseAlgorithm


class FCFSAlgorithm(BaseAlgorithm):
    """
    Simple FCFS: Assign the first available elevator to each passenger
    """

    def __init__(self, enable_logging: bool = False):
        super().__init__(enable_logging=enable_logging)
        self.name = "FCFS"
        self.passenger_queue = []  # Track call order

    def on_passenger_call(self, passenger, elevators):
        """Assign first available elevator"""
        # Add to queue
        self.passenger_queue.append(passenger.id)

        # Find any available elevator
        for elevator in elevators:
            if not elevator.destination_floor and len(elevator.passengers) == 0:
                return elevator

        return None

    def on_elevator_idle(self, elevator, waiting_passengers):
        """Go to the earliest waiting passenger"""
        if not waiting_passengers:
            return None

        # Sort by call order (earliest first)
        earliest = min(waiting_passengers,
                      key=lambda p: self.passenger_queue.index(p.id)
                      if p.id in self.passenger_queue else float('inf'))

        return earliest.origin

    def on_elevator_approaching(self, elevator, floor, passengers_waiting, passengers_in_elevator):
        """Stop for pickups and dropoffs"""
        # Stop if anyone wants off
        for p in passengers_in_elevator:
            if p.destination == floor:
                return True

        # Stop if going to pick someone up at this floor
        if elevator.destination_floor == floor:
            return True

        return False

    def on_passenger_board(self, elevator, passenger):
        """Register destination"""
        return True
```

## 🚀 Next Steps

1. **Study existing algorithms**:
   - `algo/optimized_scan.py` - Production-ready SCAN algorithm
   - `algo/rl_dqn.py` - Reinforcement learning approach
   - `algo/hybrid_scan_rl.py` - Best of both worlds

2. **Read detailed docs**:
   - [Simulator API Reference](simulator_api_reference.md) - **Complete list of available data and metrics** ⭐
   - [Algorithm Design Guide](algorithm.md) - In-depth explanation
   - [Algorithm Extension Guide](../algo/README.md) - Advanced topics
   - [Testing Guide](testing_guide.md) - Testing best practices

3. **Experiment**:
   - Try different strategies
   - Compare with existing algorithms
   - Test on different scenarios

## 💡 Common Patterns

### Pattern 1: Scoring System

```python
def _score_elevator(self, elevator, passenger):
    """Score elevator for assignment (lower is better)"""
    score = abs(elevator.current_floor - passenger.origin)  # Distance
    score += len(elevator.passengers) * 5  # Load penalty

    # Direction bonus
    if self._same_direction(elevator, passenger):
        score *= 0.5

    return score

def on_passenger_call(self, passenger, elevators):
    return min(elevators, key=lambda e: self._score_elevator(e, passenger))
```

### Pattern 2: State Tracking

```python
def __init__(self, enable_logging: bool = False):
    super().__init__(enable_logging=enable_logging)
    self.elevator_assignments = {}  # Track assignments
    self.pickup_promises = {}       # Track commitments

def on_passenger_call(self, passenger, elevators):
    # Check existing promises
    for elevator_id, promises in self.pickup_promises.items():
        if passenger.origin in promises:
            return next(e for e in elevators if e.id == elevator_id)
    # ... rest of logic
```

### Pattern 3: Look-Ahead

```python
def _estimate_arrival_time(self, elevator, floor):
    """Estimate when elevator will reach floor"""
    distance = abs(elevator.current_floor - floor)
    stops = len(elevator.passengers)  # Estimated stops
    return distance + stops * 2  # 2 ticks per stop

def on_passenger_call(self, passenger, elevators):
    # Choose elevator with earliest arrival
    return min(elevators,
               key=lambda e: self._estimate_arrival_time(e, passenger.origin))
```

## ❓ FAQ

**Q: Do I need to implement all methods?**
A: No, only implement the methods you need. The base class provides default implementations.

**Q: How do I access elevator state?**
A: Use elevator object attributes: `elevator.current_floor`, `elevator.passengers`, `elevator.capacity`, etc.

**Q: Can I use external libraries?**
A: Yes, but add them to `pyproject.toml` first with `uv add <package>`.

**Q: How do I debug my algorithm?**
A: Use `enable_logging=True` and print statements. Run on small scenarios first.

**Q: Why is my algorithm slow?**
A: Check the test output for specific metrics. Common issues:
- Not assigning elevators efficiently
- Not handling idle elevators
- Not stopping at correct floors

## 🎉 Congratulations!

You've successfully added a custom algorithm! Now experiment, test, and optimize to beat the existing algorithms.

**Happy Coding!** 🚀

---

*Last updated: 2025-10-03*
*See also: [Algorithm Design Guide](algorithm.md) | [Testing Guide](testing_guide.md)*
