#!/usr/bin/env python3
"""
FastAPI application for elevator scheduling visualization
Supports both Mock simulation (for quick demos) and Real simulation (actual algorithms)
"""

import json
from pathlib import Path
from typing import List, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import algo

app = FastAPI(title="Elevator Scheduling Visualization")

# Configuration: Set to True to use real algorithms, False for mock simulation
USE_REAL_SIMULATION = True  # Change to True when you want to test with real algorithms

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Store active WebSocket connections
active_connections: List[WebSocket] = []


@app.get("/")
async def get_index():
    """Serve the main HTML page"""
    index_file = static_path / "index.html"
    return FileResponse(index_file)


@app.get("/api/algorithms")
async def get_algorithms():
    """Get list of available algorithms"""
    algorithms = []

    algorithms_info = {
        "OptimizedScanAlgorithm": {
            "name": "OptimizedScanAlgorithm",
            "display_name": "Optimized SCAN",
            "description": "优化SCAN算法 - 智能评分系统",
            "type": "Heuristic"
        },
        "RLDQNAlgorithm": {
            "name": "RLDQNAlgorithm",
            "display_name": "RL DQN",
            "description": "强化学习Q-learning算法",
            "type": "Machine Learning"
        },
        "HybridScanRLAlgorithm": {
            "name": "HybridScanRLAlgorithm",
            "display_name": "Hybrid SCAN-RL ⭐",
            "description": "混合SCAN-RL算法 (推荐)",
            "type": "Hybrid"

        },
        "ScanController": {
            "name": "ScanController",
            "display_name": "BASE SCAN",
            "description": "基础SCAN算法",
            "type": "Heuristic"
        }
    }

    for algo_name in algo.__all__:
        if algo_name in algorithms_info:
            algorithms.append(algorithms_info[algo_name])

    return {"algorithms": algorithms}


@app.get("/api/scenarios")
async def get_scenarios():
    """Get list of available test scenarios"""
    data_dir = Path(__file__).parent.parent / "data"
    scenarios = []

    for json_file in sorted(data_dir.glob("*.json")):
        if json_file.name == "README.json":
            continue

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                building = data.get("building", {})

                scenarios.append({
                    "name": json_file.stem,
                    "display_name": building.get("description", json_file.stem),
                    "floors": building.get("floors", 0),
                    "elevators": building.get("elevators", 0),
                    "passengers": building.get("expected_passengers", len(data.get("traffic", []))),
                    "duration": building.get("duration", 0),
                    "scale": building.get("scale", "unknown"),
                    "type": building.get("scenario", "mixed")
                })
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
            continue

    return {"scenarios": scenarios}


@app.websocket("/ws/simulation")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time simulation updates"""
    await websocket.accept()
    active_connections.append(websocket)

    engine = None  # Initialize engine before try block

    try:
        # Choose simulation engine based on configuration
        if USE_REAL_SIMULATION:
            from webui.real_simulation import RealSimulationEngine
            EngineClass = RealSimulationEngine
            print("[WebUI] Using REAL simulation engine")
        else:
            from webui.mock_simulation import MockSimulationEngine
            EngineClass = MockSimulationEngine
            print("[WebUI] Using MOCK simulation engine")

        while True:
            # Receive message from client
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "start":
                # Start new simulation
                algorithm_name = message.get("algorithm", "HybridScanRLAlgorithm")
                scenario_name = message.get("scenario", "small_morning_rush")
                speed = message.get("speed", 1.0)

                print(f"[WebUI] Received start request: algorithm={algorithm_name}, scenario={scenario_name}")

                # Stop existing simulation if any
                if engine:
                    engine.stop()
                    if USE_REAL_SIMULATION:
                        # Give time for cleanup
                        await asyncio.sleep(0.5)

                # Create and start new simulation
                try:
                    engine = EngineClass(
                        algorithm_name=algorithm_name,
                        scenario_name=scenario_name,
                        speed=speed,
                        websocket=websocket
                    )

                    # Start simulation in background task
                    import asyncio
                    asyncio.create_task(engine.start())

                except Exception as e:
                    print(f"[WebUI] Error creating simulation: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Failed to start simulation: {str(e)}"
                    })

            elif msg_type == "pause":
                if engine:
                    engine.pause()

            elif msg_type == "resume":
                if engine:
                    engine.resume()

            elif msg_type == "stop":
                if engine:
                    engine.stop()
                    if USE_REAL_SIMULATION:
                        await asyncio.sleep(0.5)
                    engine = None

            elif msg_type == "set_speed":
                speed = message.get("speed", 1.0)
                if engine:
                    engine.set_speed(speed)

    except WebSocketDisconnect:
        active_connections.remove(websocket)
        if engine:
            engine.stop()
            if USE_REAL_SIMULATION:
                import asyncio
                await asyncio.sleep(0.5)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)
        if engine:
            engine.stop()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
