#!/usr/bin/env python3
"""
FastAPI 应用入口 - MVC 架构
职责：应用初始化、路由注册、中间件配置

重构说明：
- 遵循 MVC 架构模式
- Model 层：webui/models/ - 数据模型和数据访问
- Service 层：webui/services/ - 业务逻辑
- Controller 层：webui/controllers/ - 请求处理
"""

from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# 导入 Controllers
from webui.controllers import (
    algorithm_router,
    scenario_router,
    handle_websocket_simulation
)


def create_app() -> FastAPI:
    """
    应用工厂函数
    职责：创建并配置 FastAPI 应用实例

    Returns:
        FastAPI: 配置好的应用实例
    """
    app = FastAPI(title="Elevator Scheduling Visualization - MVC Architecture")

    # 配置 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 挂载静态文件
    static_path = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    # 注册 API 路由（Controller 层）
    app.include_router(algorithm_router)
    app.include_router(scenario_router)

    # 首页路由
    @app.get("/")
    async def index():
        """返回首页 HTML"""
        return FileResponse(static_path / "index.html")

    # WebSocket 路由
    @app.websocket("/ws/simulation")
    async def websocket_simulation(websocket: WebSocket):
        """WebSocket 模拟端点"""
        await handle_websocket_simulation(websocket)

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5173, log_level="info")
