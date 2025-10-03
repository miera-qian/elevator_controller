#!/usr/bin/env python3
"""
Generate complex test data for elevator scheduling algorithm
Creates various traffic patterns to test different scenarios
"""

import json
import random
from typing import List, Dict
from pathlib import Path


def generate_morning_rush(floors: int, duration: int, start_tick: int = 0) -> List[Dict]:
    """
    Morning rush: Most passengers go from ground floor (0) to upper floors
    Simulates office building morning rush hour
    """
    passengers = []
    passenger_id = 1

    # Heavy traffic from floor 0 to upper floors
    num_passengers = int(duration * 0.8)  # High density

    for i in range(num_passengers):
        tick = start_tick + int(i * duration / num_passengers) + random.randint(-5, 5)
        tick = max(start_tick, tick)

        passengers.append({
            "id": passenger_id,
            "origin": 0,
            "destination": random.randint(1, floors - 1),
            "tick": tick
        })
        passenger_id += 1

    return passengers


def generate_evening_rush(floors: int, duration: int, start_tick: int = 0) -> List[Dict]:
    """
    Evening rush: Most passengers go from upper floors to ground floor (0)
    Simulates office building evening rush hour
    """
    passengers = []
    passenger_id = 1

    # Heavy traffic from upper floors to floor 0
    num_passengers = int(duration * 0.8)

    for i in range(num_passengers):
        tick = start_tick + int(i * duration / num_passengers) + random.randint(-5, 5)
        tick = max(start_tick, tick)

        passengers.append({
            "id": passenger_id,
            "origin": random.randint(1, floors - 1),
            "destination": 0,
            "tick": tick
        })
        passenger_id += 1

    return passengers


def generate_inter_floor(floors: int, duration: int, start_tick: int = 0) -> List[Dict]:
    """
    Inter-floor traffic: Random passengers between any floors
    Simulates normal office hours
    """
    passengers = []
    passenger_id = 1

    # Moderate, evenly distributed traffic
    num_passengers = int(duration * 0.4)

    for i in range(num_passengers):
        tick = start_tick + int(i * duration / num_passengers) + random.randint(-10, 10)
        tick = max(start_tick, tick)

        origin = random.randint(0, floors - 1)
        destination = random.randint(0, floors - 1)

        # Ensure origin != destination
        while destination == origin:
            destination = random.randint(0, floors - 1)

        passengers.append({
            "id": passenger_id,
            "origin": origin,
            "destination": destination,
            "tick": tick
        })
        passenger_id += 1

    return passengers


def generate_lunch_rush(floors: int, duration: int, start_tick: int = 0) -> List[Dict]:
    """
    Lunch rush: Two-way traffic between floors and ground floor
    Simulates lunch time with people going down and coming back up
    """
    passengers = []
    passenger_id = 1

    num_passengers = int(duration * 0.6)
    half_duration = duration // 2

    # First half: going down to ground floor
    for i in range(num_passengers // 2):
        tick = start_tick + int(i * half_duration / (num_passengers // 2))

        passengers.append({
            "id": passenger_id,
            "origin": random.randint(1, floors - 1),
            "destination": 0,
            "tick": tick
        })
        passenger_id += 1

    # Second half: coming back up
    for i in range(num_passengers // 2):
        tick = start_tick + half_duration + int(i * half_duration / (num_passengers // 2))

        passengers.append({
            "id": passenger_id,
            "origin": 0,
            "destination": random.randint(1, floors - 1),
            "tick": tick
        })
        passenger_id += 1

    return passengers


def generate_burst_traffic(floors: int, duration: int, start_tick: int = 0, num_bursts: int = 5) -> List[Dict]:
    """
    Burst traffic: Sudden spikes of passengers at random times
    Tests algorithm's ability to handle sudden load
    """
    passengers = []
    passenger_id = 1

    burst_interval = duration // num_bursts

    for burst in range(num_bursts):
        burst_start = start_tick + burst * burst_interval
        # 10-20 passengers per burst
        burst_size = random.randint(10, 20)

        for i in range(burst_size):
            tick = burst_start + random.randint(0, 10)
            origin = random.randint(0, floors - 1)
            destination = random.randint(0, floors - 1)

            while destination == origin:
                destination = random.randint(0, floors - 1)

            passengers.append({
                "id": passenger_id,
                "origin": origin,
                "destination": destination,
                "tick": tick
            })
            passenger_id += 1

    return passengers


def generate_mixed_scenario(floors: int, duration: int) -> List[Dict]:
    """
    Mixed scenario: Combines multiple traffic patterns
    Most realistic and challenging test case
    """
    passengers = []

    # Morning rush (first 25%)
    morning = generate_morning_rush(floors, duration // 4, 0)
    passengers.extend(morning)

    # Normal inter-floor (next 25%)
    inter1 = generate_inter_floor(floors, duration // 4, duration // 4)
    passengers.extend(inter1)

    # Lunch rush (middle 25%)
    lunch = generate_lunch_rush(floors, duration // 4, duration // 2)
    passengers.extend(lunch)

    # Afternoon inter-floor (next 12.5%)
    inter2 = generate_inter_floor(floors, duration // 8, 3 * duration // 4)
    passengers.extend(inter2)

    # Evening rush (last 12.5%)
    evening = generate_evening_rush(floors, duration // 8, 7 * duration // 8)
    passengers.extend(evening)

    # Re-assign IDs sequentially
    for i, p in enumerate(passengers, 1):
        p["id"] = i

    # Sort by tick
    passengers.sort(key=lambda x: x["tick"])

    return passengers


def create_test_scenario(
    name: str,
    description: str,
    floors: int,
    elevators: int,
    elevator_capacity: int,
    duration: int,
    scenario_type: str,
    scale: str,
    passengers: List[Dict]
) -> Dict:
    """Create a complete test scenario JSON structure"""
    return {
        "building": {
            "floors": floors,
            "elevators": elevators,
            "elevator_capacity": elevator_capacity,
            "scenario": scenario_type,
            "scale": scale,
            "description": description,
            "expected_passengers": len(passengers),
            "duration": duration
        },
        "traffic": passengers
    }


def main():
    """Generate all test scenarios"""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    scenarios = []

    # 1. Small building - Morning rush
    scenarios.append({
        "filename": "small_morning_rush.json",
        "data": create_test_scenario(
            name="Small Morning Rush",
            description="小型建筑上班高峰 - 6层楼，2部电梯",
            floors=6,
            elevators=2,
            elevator_capacity=8,
            duration=200,
            scenario_type="morning_rush",
            scale="small",
            passengers=generate_morning_rush(6, 200)
        )
    })

    # 2. Small building - Evening rush
    scenarios.append({
        "filename": "small_evening_rush.json",
        "data": create_test_scenario(
            name="Small Evening Rush",
            description="小型建筑下班高峰 - 6层楼，2部电梯",
            floors=6,
            elevators=2,
            elevator_capacity=8,
            duration=200,
            scenario_type="evening_rush",
            scale="small",
            passengers=generate_evening_rush(6, 200)
        )
    })

    # 3. Medium building - Inter-floor
    scenarios.append({
        "filename": "medium_inter_floor.json",
        "data": create_test_scenario(
            name="Medium Inter-floor",
            description="中型建筑楼层间流量 - 10层楼，3部电梯",
            floors=10,
            elevators=3,
            elevator_capacity=10,
            duration=300,
            scenario_type="inter_floor",
            scale="medium",
            passengers=generate_inter_floor(10, 300)
        )
    })

    # 4. Medium building - Lunch rush
    scenarios.append({
        "filename": "medium_lunch_rush.json",
        "data": create_test_scenario(
            name="Medium Lunch Rush",
            description="中型建筑午餐高峰 - 10层楼，3部电梯",
            floors=10,
            elevators=3,
            elevator_capacity=10,
            duration=300,
            scenario_type="lunch_rush",
            scale="medium",
            passengers=generate_lunch_rush(10, 300)
        )
    })

    # 5. Large building - Mixed scenario
    scenarios.append({
        "filename": "large_mixed.json",
        "data": create_test_scenario(
            name="Large Mixed",
            description="大型建筑混合场景 - 15层楼，4部电梯，包含多种流量模式",
            floors=15,
            elevators=4,
            elevator_capacity=12,
            duration=500,
            scenario_type="mixed",
            scale="large",
            passengers=generate_mixed_scenario(15, 500)
        )
    })

    # 6. Small building - Burst traffic
    scenarios.append({
        "filename": "small_burst_traffic.json",
        "data": create_test_scenario(
            name="Small Burst Traffic",
            description="小型建筑突发流量 - 6层楼，2部电梯，测试突发负载",
            floors=6,
            elevators=2,
            elevator_capacity=8,
            duration=200,
            scenario_type="burst_traffic",
            scale="small",
            passengers=generate_burst_traffic(6, 200)
        )
    })

    # 7. Large building - Morning rush (high capacity test)
    scenarios.append({
        "filename": "large_morning_rush.json",
        "data": create_test_scenario(
            name="Large Morning Rush",
            description="大型建筑上班高峰 - 20层楼，5部电梯，高容量测试",
            floors=20,
            elevators=5,
            elevator_capacity=15,
            duration=400,
            scenario_type="morning_rush",
            scale="large",
            passengers=generate_morning_rush(20, 400)
        )
    })

    # 8. Extra-large building - Mixed (stress test)
    scenarios.append({
        "filename": "xlarge_stress_test.json",
        "data": create_test_scenario(
            name="Extra-Large Stress Test",
            description="超大型建筑压力测试 - 25层楼，6部电梯，极限场景",
            floors=25,
            elevators=6,
            elevator_capacity=20,
            duration=600,
            scenario_type="mixed",
            scale="xlarge",
            passengers=generate_mixed_scenario(25, 600)
        )
    })

    # 9. Medium building - High frequency burst
    scenarios.append({
        "filename": "medium_high_freq_burst.json",
        "data": create_test_scenario(
            name="Medium High Frequency Burst",
            description="中型建筑高频突发 - 10层楼，3部电梯，频繁突发流量",
            floors=10,
            elevators=3,
            elevator_capacity=10,
            duration=300,
            scenario_type="burst_traffic",
            scale="medium",
            passengers=generate_burst_traffic(10, 300, num_bursts=10)
        )
    })

    # 10. Asymmetric building - Bottom heavy
    bottom_heavy_passengers = []
    pid = 1
    for i in range(200):
        tick = i * 2
        # 80% from floors 0-2, 20% from other floors
        if random.random() < 0.8:
            origin = random.randint(0, 2)
        else:
            origin = random.randint(3, 9)
        destination = random.randint(0, 9)
        while destination == origin:
            destination = random.randint(0, 9)

        bottom_heavy_passengers.append({
            "id": pid,
            "origin": origin,
            "destination": destination,
            "tick": tick
        })
        pid += 1

    scenarios.append({
        "filename": "medium_bottom_heavy.json",
        "data": create_test_scenario(
            name="Medium Bottom Heavy",
            description="中型建筑底层密集 - 10层楼，3部电梯，底层流量占80%",
            floors=10,
            elevators=3,
            elevator_capacity=10,
            duration=400,
            scenario_type="asymmetric",
            scale="medium",
            passengers=bottom_heavy_passengers
        )
    })

    # Save all scenarios
    for scenario in scenarios:
        filepath = data_dir / scenario["filename"]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(scenario["data"], f, indent=2, ensure_ascii=False)

        num_passengers = len(scenario["data"]["traffic"])
        print(f"✓ Generated: {scenario['filename']} ({num_passengers} passengers)")

    # Create a summary file
    summary = {
        "test_scenarios": [
            {
                "filename": s["filename"],
                "description": s["data"]["building"]["description"],
                "floors": s["data"]["building"]["floors"],
                "elevators": s["data"]["building"]["elevators"],
                "capacity": s["data"]["building"]["elevator_capacity"],
                "duration": s["data"]["building"]["duration"],
                "passengers": s["data"]["building"]["expected_passengers"],
                "scenario_type": s["data"]["building"]["scenario"]
            }
            for s in scenarios
        ]
    }

    with open(data_dir / "README.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Generated {len(scenarios)} test scenarios in 'data/' directory")
    print("✓ Created README.json with scenario summary")


if __name__ == "__main__":
    main()
