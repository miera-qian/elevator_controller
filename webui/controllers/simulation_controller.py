"""
模拟控制器
职责：处理 WebSocket 连接和模拟控制
"""
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
from webui.services import SimulationService, AlgorithmService, ScenarioService


# 全局状态：存储活跃的 WebSocket 连接
active_connections: List[WebSocket] = []

# 配置：使用真实模拟还是模拟数据
USE_REAL_SIMULATION = True


async def handle_websocket_simulation(websocket: WebSocket):
    """
    处理 WebSocket 模拟连接

    Args:
        websocket: WebSocket 连接实例
    """
    await websocket.accept()
    active_connections.append(websocket)

    # 创建服务实例
    simulation_service = SimulationService(use_real_simulation=USE_REAL_SIMULATION)
    algorithm_service = AlgorithmService()
    scenario_service = ScenarioService()

    engine = None

    try:
        print(f"[WebUI] Using {'REAL' if USE_REAL_SIMULATION else 'MOCK'} simulation engine")

        while True:
            # 接收客户端消息
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "start":
                # 处理开始模拟请求
                await _handle_start_simulation(
                    websocket,
                    message,
                    simulation_service,
                    algorithm_service,
                    scenario_service,
                    engine
                )
                engine = simulation_service.get_current_engine()

            elif msg_type == "pause":
                # 处理暂停请求
                if engine:
                    engine.pause()

            elif msg_type == "resume":
                # 处理恢复请求
                if engine:
                    engine.resume()

            elif msg_type == "stop":
                # 处理停止请求
                if engine:
                    engine.stop()
                    if USE_REAL_SIMULATION:
                        await asyncio.sleep(0.5)
                    simulation_service.clear_current_engine()
                    engine = None

            elif msg_type == "set_speed":
                # 处理速度设置请求
                speed = message.get("speed", 1.0)
                if engine:
                    engine.set_speed(speed)

    except WebSocketDisconnect:
        # 处理连接断开
        if websocket in active_connections:
            active_connections.remove(websocket)
        if engine:
            engine.stop()
            if USE_REAL_SIMULATION:
                await asyncio.sleep(0.5)

    except Exception as e:
        # 处理其他错误
        print(f"[WebUI] WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)
        if engine:
            engine.stop()


async def _handle_start_simulation(
    websocket: WebSocket,
    message: dict,
    simulation_service: SimulationService,
    algorithm_service: AlgorithmService,
    scenario_service: ScenarioService,
    current_engine
):
    """
    处理开始模拟请求

    Args:
        websocket: WebSocket 连接
        message: 客户端消息
        simulation_service: 模拟服务
        algorithm_service: 算法服务
        scenario_service: 场景服务
        current_engine: 当前运行的引擎
    """
    # 提取参数
    algorithm_name = message.get("algorithm", "HybridScanRLAlgorithm")
    scenario_name = message.get("scenario", "small_morning_rush")
    speed = message.get("speed", 1.0)
    max_ticks = message.get("max_ticks")  # 获取max_ticks参数

    print(f"[WebUI] ========================================")
    print(f"[WebUI] Received start request")
    print(f"[WebUI]   algorithm={algorithm_name}")
    print(f"[WebUI]   scenario={scenario_name}")
    print(f"[WebUI]   speed={speed}")
    print(f"[WebUI]   max_ticks={max_ticks}")
    print(f"[WebUI] ========================================")

    # 验证算法和场景是否存在
    if not algorithm_service.validate_algorithm(algorithm_name):
        print(f"[WebUI] ❌ Algorithm '{algorithm_name}' not found")
        await websocket.send_json({
            "type": "error",
            "message": f"Algorithm '{algorithm_name}' not found"
        })
        return

    if not scenario_service.validate_scenario(scenario_name):
        print(f"[WebUI] ❌ Scenario '{scenario_name}' not found")
        await websocket.send_json({
            "type": "error",
            "message": f"Scenario '{scenario_name}' not found"
        })
        return

    # 停止现有模拟
    if current_engine:
        current_engine.stop()
        if True:  # USE_REAL_SIMULATION
            await asyncio.sleep(0.5)

    # 创建并启动新模拟
    try:
        print(f"[WebUI] Creating engine...")
        engine = simulation_service.create_engine(
            algorithm_name=algorithm_name,
            scenario_name=scenario_name,
            speed=speed,
            max_ticks=max_ticks,
            websocket=websocket
        )
        print(f"[WebUI] Engine created: {engine}")

        # 在后台任务中启动模拟
        print(f"[WebUI] Creating background task to start engine...")
        asyncio.create_task(engine.start())
        print(f"[WebUI] Background task created")

    except Exception as e:
        print(f"[WebUI] ❌ Error creating simulation: {e}")
        import traceback
        traceback.print_exc()
        await websocket.send_json({
            "type": "error",
            "message": f"Failed to start simulation: {str(e)}"
        })
