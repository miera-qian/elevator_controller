# Simulator API Reference - Available Data and Metrics

> **Version**: 1.0.0
> **Last Updated**: 2025-10-04
> **Purpose**: Complete reference of all data structures and metrics available from the elevator simulator

---

## Table of Contents

1. [Overview](#overview)
2. [Simulation State](#simulation-state)
3. [Performance Metrics](#performance-metrics)
4. [Elevator State](#elevator-state)
5. [Floor State](#floor-state)
6. [Passenger Information](#passenger-information)
7. [Simulation Events](#simulation-events)
8. [How to Access Data](#how-to-access-data)
9. [Code Examples](#code-examples)

---

## Overview

The elevator simulator (`elevator-saga` server) calculates and maintains all system state and performance metrics. Algorithms access this data through the `ElevatorController` base class and API client.

**Key Principle**:
- **Single Source of Truth**: All metrics are calculated by the simulator
- **Read-Only Access**: Algorithms read state but don't calculate metrics themselves
- **Consistency**: All algorithms are evaluated using identical metrics

---

## Simulation State

The complete simulation state is available via `api_client.get_state()` which returns a `SimulationState` object.

### SimulationState

| Field | Type | Description |
|-------|------|-------------|
| `tick` | `int` | Current simulation tick (time step) |
| `elevators` | `List[ElevatorState]` | List of all elevator states |
| `floors` | `List[FloorState]` | List of all floor states |
| `passengers` | `Dict[int, PassengerInfo]` | Map of passenger ID to passenger info |
| `metrics` | `PerformanceMetrics` | Current performance metrics |
| `events` | `List[SimulationEvent]` | Events that occurred in this tick |

**Access Methods**:
```python
def on_event_execute_end(self, tick, events, elevators, floors):
    state = self.api_client.get_state()
    current_metrics = state.metrics
    print(f"Tick {state.tick}: {current_metrics.average_wait_time}")
```

---

## Performance Metrics

**Source**: `SimulationState.metrics` (type: `PerformanceMetrics`)

All performance metrics are calculated by the simulator based on passenger journey data.

### Available Metrics

| Metric | Type | Description | How Calculated |
|--------|------|-------------|----------------|
| `completed_passengers` | `int` | Number of passengers who reached destination | Count of passengers with `dropoff_tick > 0` |
| `total_passengers` | `int` | Total number of passengers in scenario | Count of all passengers that called elevator |
| `average_wait_time` | `float` | Average time passengers wait for pickup (ticks) | Mean of `(pickup_tick - arrive_tick)` for all passengers |
| `p95_wait_time` | `float` | 95th percentile wait time (ticks) | 95th percentile of `(pickup_tick - arrive_tick)` |
| `average_system_time` | `float` | Average total journey time (ticks) | Mean of `(dropoff_tick - arrive_tick)` for completed passengers |
| `p95_system_time` | `float` | 95th percentile system time (ticks) | 95th percentile of `(dropoff_tick - arrive_tick)` |

### Computed Properties

| Property | Type | Description | Formula |
|----------|------|-------------|---------|
| `completion_rate` | `float` | Percentage of passengers completed | `completed_passengers / total_passengers` |

**Note**: Energy consumption metrics (`total_energy_consumption`, `energy_per_passenger`) are currently disabled in the simulator.

### Metric Definitions

- **Wait Time**: Time from when passenger calls elevator (`arrive_tick`) to when they board (`pickup_tick`)
- **System Time**: Total time from call to arrival at destination (`dropoff_tick - arrive_tick`)
- **P95**: 95% of passengers experience time less than or equal to this value

### Access Example

```python
# In your algorithm's event handler
state = self.api_client.get_state()
metrics = state.metrics

print(f"Performance Summary:")
print(f"  Completed: {metrics.completed_passengers}/{metrics.total_passengers}")
print(f"  Completion Rate: {metrics.completion_rate * 100:.1f}%")
print(f"  Avg Wait: {metrics.average_wait_time:.2f} ticks")
print(f"  P95 Wait: {metrics.p95_wait_time:.2f} ticks")
print(f"  Avg System Time: {metrics.average_system_time:.2f} ticks")
print(f"  P95 System Time: {metrics.p95_system_time:.2f} ticks")
```

---

## Elevator State

**Source**: `SimulationState.elevators[i]` (type: `ElevatorState`)

Each elevator provides rich state information for decision-making.

### ElevatorState Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Unique elevator identifier |
| `position` | `Position` | Current position details |
| `next_target_floor` | `Optional[int]` | Next floor the elevator will go to |
| `passengers` | `List[int]` | List of passenger IDs currently in elevator |
| `max_capacity` | `int` | Maximum passenger capacity (default: 10) |
| `speed_pre_tick` | `float` | Speed per tick (default: 0.5 floors/tick) |
| `run_status` | `ElevatorStatus` | Current running status (see below) |
| `last_tick_direction` | `Direction` | Direction in last tick |
| `indicators` | `ElevatorIndicators` | Up/down indicator lights |
| `passenger_destinations` | `Dict[int, int]` | Map of passenger ID to destination floor |
| `energy_consumed` | `float` | Total energy consumed (currently disabled) |
| `last_update_tick` | `int` | Tick when last updated |

### Position Details

| Field | Type | Description |
|-------|------|-------------|
| `current_floor` | `int` | Current floor number (integer) |
| `target_floor` | `int` | Target floor number |
| `floor_up_position` | `int` | Sub-floor position (0-9), 10 = next floor |
| `current_floor_float` | `float` | Precise position: `current_floor + floor_up_position/10` |

### ElevatorStatus Enum

| Status | Description |
|--------|-------------|
| `STOPPED` | Elevator is stopped at a floor |
| `START_UP` | Acceleration phase (1 tick) |
| `CONSTANT_SPEED` | Constant speed movement |
| `START_DOWN` | Deceleration phase (1 tick) |

**Important**: `START_UP`/`START_DOWN` refer to acceleration/deceleration, NOT movement direction. Check `target_floor_direction` for actual direction.

### Direction Enum

| Value | Description |
|-------|-------------|
| `UP` | Moving upward |
| `DOWN` | Moving downward |
| `STOPPED` | Not moving |

### Computed Properties

| Property | Type | Description |
|----------|------|-------------|
| `current_floor` | `int` | Integer floor number |
| `current_floor_float` | `float` | Precise position with decimals |
| `target_floor` | `int` | Next target floor |
| `load_factor` | `float` | Current load (0.0-1.0): `len(passengers) / max_capacity` |
| `target_floor_direction` | `Direction` | Direction to target: UP/DOWN/STOPPED |
| `is_idle` | `bool` | True if `run_status == STOPPED` |
| `is_full` | `bool` | True if `len(passengers) >= max_capacity` |
| `is_running` | `bool` | True if elevator is moving |
| `pressed_floors` | `List[int]` | Sorted list of destination floors |

### Access Example

```python
state = self.api_client.get_state()

for elevator_state in state.elevators:
    print(f"Elevator {elevator_state.id}:")
    print(f"  Position: {elevator_state.current_floor_float:.1f}")
    print(f"  Target: {elevator_state.target_floor}")
    print(f"  Direction: {elevator_state.target_floor_direction.value}")
    print(f"  Status: {elevator_state.run_status.value}")
    print(f"  Passengers: {len(elevator_state.passengers)}/{elevator_state.max_capacity}")
    print(f"  Load Factor: {elevator_state.load_factor * 100:.1f}%")
    print(f"  Destinations: {elevator_state.pressed_floors}")
    print(f"  Is Idle: {elevator_state.is_idle}")
    print(f"  Is Full: {elevator_state.is_full}")
```

---

## Floor State

**Source**: `SimulationState.floors[i]` (type: `FloorState`)

Each floor tracks waiting passengers.

### FloorState Fields

| Field | Type | Description |
|-------|------|-------------|
| `floor` | `int` | Floor number |
| `up_queue` | `List[int]` | IDs of passengers waiting to go up |
| `down_queue` | `List[int]` | IDs of passengers waiting to go down |

### Computed Properties

| Property | Type | Description |
|----------|------|-------------|
| `has_waiting_passengers` | `bool` | True if any passengers waiting |
| `total_waiting` | `int` | Total count of waiting passengers |

### Access Example

```python
state = self.api_client.get_state()

for floor_state in state.floors:
    if floor_state.has_waiting_passengers:
        print(f"Floor {floor_state.floor}:")
        print(f"  Waiting Up: {len(floor_state.up_queue)} passengers")
        print(f"  Waiting Down: {len(floor_state.down_queue)} passengers")
        print(f"  Total: {floor_state.total_waiting}")

        # Get detailed passenger info
        for passenger_id in floor_state.up_queue:
            passenger = state.passengers[passenger_id]
            print(f"    Passenger {passenger_id}: {passenger.origin} → {passenger.destination}")
```

---

## Passenger Information

**Source**: `SimulationState.passengers[passenger_id]` (type: `PassengerInfo`)

Detailed information about each passenger.

### PassengerInfo Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Unique passenger identifier |
| `origin` | `int` | Origin floor (where they called from) |
| `destination` | `int` | Destination floor |
| `arrive_tick` | `int` | Tick when passenger called elevator |
| `pickup_tick` | `int` | Tick when passenger boarded (0 if waiting) |
| `dropoff_tick` | `int` | Tick when passenger arrived (0 if not completed) |
| `elevator_id` | `Optional[int]` | ID of elevator carrying passenger (None if waiting) |

### PassengerStatus Enum

| Status | Condition |
|--------|-----------|
| `WAITING` | `pickup_tick == 0` |
| `IN_ELEVATOR` | `pickup_tick > 0 and dropoff_tick == 0` |
| `COMPLETED` | `dropoff_tick > 0` |
| `CANCELLED` | Not currently used |

### Computed Properties

| Property | Type | Description | Formula |
|----------|------|-------------|---------|
| `status` | `PassengerStatus` | Current passenger status | Based on tick values |
| `wait_time` | `int` | Time waited for pickup | `pickup_tick - arrive_tick` |
| `system_time` | `int` | Total journey time | `dropoff_tick - arrive_tick` |
| `travel_direction` | `Direction` | Intended direction | UP if `destination > origin` |

### Access Example

```python
state = self.api_client.get_state()

# Get all waiting passengers
waiting_passengers = [
    p for p in state.passengers.values()
    if p.status == PassengerStatus.WAITING
]

for passenger in waiting_passengers:
    print(f"Passenger {passenger.id}:")
    print(f"  Journey: Floor {passenger.origin} → {passenger.destination}")
    print(f"  Direction: {passenger.travel_direction.value}")
    print(f"  Called at tick: {passenger.arrive_tick}")
    print(f"  Wait time so far: {state.tick - passenger.arrive_tick} ticks")

# Get passengers in elevators
in_transit = [
    p for p in state.passengers.values()
    if p.status == PassengerStatus.IN_ELEVATOR
]

for passenger in in_transit:
    print(f"Passenger {passenger.id} in elevator {passenger.elevator_id}")
    print(f"  Waited: {passenger.wait_time} ticks")
    print(f"  Going to floor: {passenger.destination}")
```

---

## Simulation Events

**Source**: `SimulationState.events` or callback parameters (type: `SimulationEvent`)

Events represent state changes in the simulation.

### EventType Enum

| Event Type | Description | Data Fields |
|------------|-------------|-------------|
| `UP_BUTTON_PRESSED` | Passenger called elevator (going up) | `floor`, `passenger` |
| `DOWN_BUTTON_PRESSED` | Passenger called elevator (going down) | `floor`, `passenger` |
| `PASSING_FLOOR` | Elevator passed a floor | `elevator`, `floor`, `direction` |
| `STOPPED_AT_FLOOR` | Elevator stopped at floor | `elevator`, `floor` |
| `ELEVATOR_APPROACHING` | Elevator approaching floor (deceleration) | `elevator`, `floor`, `direction` |
| `IDLE` | Elevator became idle | `elevator` |
| `PASSENGER_BOARD` | Passenger boarded elevator | `elevator`, `passenger` |
| `PASSENGER_ALIGHT` | Passenger exited elevator | `elevator`, `passenger`, `floor` |

### SimulationEvent Fields

| Field | Type | Description |
|-------|------|-------------|
| `tick` | `int` | Tick when event occurred |
| `type` | `EventType` | Type of event |
| `data` | `Dict[str, Any]` | Event-specific data |
| `timestamp` | `str` | ISO format timestamp |

### Event Data Fields

Different events include different data:

```python
# UP_BUTTON_PRESSED / DOWN_BUTTON_PRESSED
{"floor": int, "passenger": int}

# PASSING_FLOOR
{"elevator": int, "floor": int, "direction": str}

# STOPPED_AT_FLOOR
{"elevator": int, "floor": int}

# ELEVATOR_APPROACHING
{"elevator": int, "floor": int, "direction": str}

# IDLE
{"elevator": int}

# PASSENGER_BOARD
{"elevator": int, "passenger": int}

# PASSENGER_ALIGHT
{"elevator": int, "passenger": int, "floor": int}
```

---

## How to Access Data

### 1. During Simulation

Access state through the API client in any callback:

```python
def on_event_execute_end(self, tick, events, elevators, floors):
    # Get complete state
    state = self.api_client.get_state()

    # Access metrics
    metrics = state.metrics

    # Access elevator details
    for elevator_state in state.elevators:
        # Use elevator_state data
        pass

    # Access floor details
    for floor_state in state.floors:
        # Use floor_state data
        pass

    # Access passenger details
    for passenger_id, passenger in state.passengers.items():
        # Use passenger data
        pass
```

### 2. At Simulation End

The simulator automatically prints metrics when simulation completes:

```python
# base_controller.py line 277
if self.current_tick >= self.current_traffic_max_tick:
    pprint(state.metrics.to_dict())
```

Output example:
```python
{
    'average_system_time': 156.78,
    'average_wait_time': 98.45,
    'completed_passengers': 120,
    'p95_system_time': 245.0,
    'p95_wait_time': 180.0,
    'total_passengers': 120
}
```

### 3. Proxy Objects vs State Objects

**Important Distinction**:

| Object Type | Source | When to Use |
|-------------|--------|-------------|
| `ProxyElevator`, `ProxyFloor`, `ProxyPassenger` | Callback parameters | For **sending commands** to simulator |
| `ElevatorState`, `FloorState`, `PassengerInfo` | `api_client.get_state()` | For **reading detailed state** |

**Proxy objects** (in callbacks):
```python
def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str):
    # Use proxy to send commands
    elevator.go_to_floor(floor.floor)
    elevator.register_destination(passenger.destination)
```

**State objects** (from API):
```python
def on_event_execute_end(self, tick, events, elevators, floors):
    state = self.api_client.get_state()
    # Use state objects to read detailed information
    for elevator_state in state.elevators:
        load = elevator_state.load_factor
        destinations = elevator_state.pressed_floors
```

---

## Code Examples

### Example 1: Monitor Performance in Real-Time

```python
class MyAlgorithm(BaseAlgorithm):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.metrics_log = []

    def on_event_execute_end(self, tick, events, elevators, floors):
        # Log metrics every 100 ticks
        if tick % 100 == 0:
            state = self.api_client.get_state()
            metrics = state.metrics

            self.metrics_log.append({
                'tick': tick,
                'avg_wait': metrics.average_wait_time,
                'p95_wait': metrics.p95_wait_time,
                'completed': metrics.completed_passengers,
                'total': metrics.total_passengers
            })

            print(f"[Tick {tick}] Avg Wait: {metrics.average_wait_time:.1f}, "
                  f"P95: {metrics.p95_wait_time:.1f}, "
                  f"Completed: {metrics.completed_passengers}/{metrics.total_passengers}")
```

### Example 2: Detailed Elevator Analysis

```python
def analyze_elevator_state(self, elevator_id: int):
    """Get detailed information about an elevator"""
    state = self.api_client.get_state()
    elevator = state.get_elevator_by_id(elevator_id)

    if not elevator:
        return None

    analysis = {
        'id': elevator.id,
        'position': elevator.current_floor_float,
        'target': elevator.target_floor,
        'direction': elevator.target_floor_direction.value,
        'status': elevator.run_status.value,
        'passenger_count': len(elevator.passengers),
        'capacity': elevator.max_capacity,
        'load_factor': elevator.load_factor,
        'is_full': elevator.is_full,
        'is_idle': elevator.is_idle,
        'destinations': elevator.pressed_floors,
        'passengers': []
    }

    # Get passenger details
    for passenger_id in elevator.passengers:
        passenger = state.passengers.get(passenger_id)
        if passenger:
            analysis['passengers'].append({
                'id': passenger.id,
                'origin': passenger.origin,
                'destination': passenger.destination,
                'wait_time': passenger.wait_time
            })

    return analysis
```

### Example 3: Find Best Elevator for Passenger

```python
def find_best_elevator(self, passenger_id: int):
    """Score elevators for a waiting passenger"""
    state = self.api_client.get_state()
    passenger = state.passengers.get(passenger_id)

    if not passenger or passenger.status != PassengerStatus.WAITING:
        return None

    scores = []
    for elevator in state.elevators:
        # Calculate distance
        distance = abs(elevator.current_floor - passenger.origin)

        # Calculate load penalty
        load_penalty = elevator.load_factor * 10

        # Direction bonus
        direction_bonus = 0
        if elevator.target_floor_direction == passenger.travel_direction:
            direction_bonus = -5  # Negative = better score

        # Idle bonus
        idle_bonus = -3 if elevator.is_idle else 0

        # Full penalty
        full_penalty = 100 if elevator.is_full else 0

        total_score = distance + load_penalty + direction_bonus + idle_bonus + full_penalty

        scores.append({
            'elevator_id': elevator.id,
            'score': total_score,
            'distance': distance,
            'load_factor': elevator.load_factor,
            'is_idle': elevator.is_idle,
            'is_full': elevator.is_full
        })

    # Return elevator with lowest score
    best = min(scores, key=lambda x: x['score'])
    return best['elevator_id']
```

### Example 4: Custom Metrics Tracking

```python
class EnhancedMetricsAlgorithm(BaseAlgorithm):
    """Algorithm with custom metrics tracking"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.custom_metrics = {
            'elevator_trips': {},  # elevator_id -> trip count
            'floor_requests': {},  # floor -> request count
            'passenger_assignments': {},  # passenger_id -> elevator_id
        }

    def on_passenger_call(self, passenger, floor, direction):
        # Track floor request
        floor_num = floor.floor
        self.custom_metrics['floor_requests'][floor_num] = \
            self.custom_metrics['floor_requests'].get(floor_num, 0) + 1

        # Your assignment logic here
        assigned_elevator = self.assign_elevator(passenger, floor, direction)

        # Track assignment
        if assigned_elevator:
            self.custom_metrics['passenger_assignments'][passenger.id] = assigned_elevator.id

        return assigned_elevator

    def on_elevator_stopped(self, elevator, floor):
        # Track elevator trips
        self.custom_metrics['elevator_trips'][elevator.id] = \
            self.custom_metrics['elevator_trips'].get(elevator.id, 0) + 1

    def on_stop(self):
        """Print custom metrics at end"""
        super().on_stop()

        # Get final state
        state = self.api_client.get_state()

        print("\n=== Custom Metrics ===")
        print(f"Elevator Trips: {self.custom_metrics['elevator_trips']}")
        print(f"Most Requested Floor: {max(self.custom_metrics['floor_requests'].items(), key=lambda x: x[1])}")
        print(f"\n=== Simulator Metrics ===")
        print(f"Average Wait Time: {state.metrics.average_wait_time:.2f}")
        print(f"P95 Wait Time: {state.metrics.p95_wait_time:.2f}")
        print(f"Completion Rate: {state.metrics.completion_rate * 100:.1f}%")
```

---

## Best Practices

### 1. Use Simulator Metrics for Evaluation

**DO**:
```python
# Get metrics from simulator
state = self.api_client.get_state()
avg_wait = state.metrics.average_wait_time
```

**DON'T**:
```python
# Don't calculate metrics yourself
self.total_wait_time += passenger.wait_time  # Redundant!
avg_wait = self.total_wait_time / len(passengers)  # May be inconsistent!
```

### 2. Access State When Needed

**DO**:
```python
# Get fresh state when making decisions
def on_passenger_call(self, passenger, floor, direction):
    state = self.api_client.get_state()
    # Use state for decision making
```

**DON'T**:
```python
# Don't cache state across ticks
self.cached_state = self.api_client.get_state()  # Will be stale!
```

### 3. Use Appropriate Data Structures

**For Commands**: Use proxy objects from callbacks
```python
def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction):
    elevator.go_to_floor(floor.floor)  # ✓ Correct
```

**For Reading**: Use state objects from API
```python
state = self.api_client.get_state()
load_factor = state.elevators[0].load_factor  # ✓ Correct
```

### 4. Trust Simulator Calculations

The simulator handles:
- ✓ Passenger wait time calculation
- ✓ System time calculation
- ✓ P95 percentile calculation
- ✓ Completion rate calculation
- ✓ Energy consumption (when enabled)

You should focus on:
- ✓ Elevator assignment logic
- ✓ Routing decisions
- ✓ Stop decisions
- ✓ Custom optimization strategies

---

## Summary

| Data Type | Access Method | Use Case |
|-----------|---------------|----------|
| **Performance Metrics** | `state.metrics` | Evaluate algorithm performance |
| **Elevator State** | `state.elevators[i]` | Make assignment decisions |
| **Floor State** | `state.floors[i]` | Know where passengers are waiting |
| **Passenger Info** | `state.passengers[id]` | Detailed passenger journey data |
| **Events** | `state.events` or callbacks | React to state changes |

**Remember**: The simulator is the single source of truth for all metrics and state. Your algorithm focuses on making smart scheduling decisions, not calculating metrics.

---

## Additional Resources

- [Quick Start Guide](quick_start_guide.md) - How to create a custom algorithm
- [Algorithm Design Guide](algorithm.md) - In-depth algorithm design patterns
- [Testing Guide](testing_guide.md) - How to test and evaluate algorithms

---

*Last updated: 2025-10-04*
*For questions or issues, please check the main README or open an issue.*
