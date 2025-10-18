"""
模拟业务逻辑服务
职责：管理模拟引擎的生命周期
"""
from typing import Optional
from fastapi import WebSocket


class SimulationService:
    """模拟业务逻辑服务"""

    def __init__(self, use_real_simulation: bool = True):
        """
        初始化模拟服务

        Args:
            use_real_simulation: 是否使用真实模拟（True）或模拟数据（False）
        """
        self.use_real_simulation = use_real_simulation
        self.current_engine: Optional[object] = None

    def create_engine(
        self,
        algorithm_name: str,
        scenario_name: str,
        speed: float,
        max_ticks: Optional[int],
        websocket: WebSocket
    ):
        """
        创建模拟引擎实例

        Args:
            algorithm_name: 算法名称
            scenario_name: 场景名称
            speed: 模拟速度
            max_ticks: 最大时长（ticks），None表示使用场景默认值
            websocket: WebSocket 连接

        Returns:
            模拟引擎实例
        """
        if self.use_real_simulation:
            from webui.direct_simulation import DirectSimulationEngine
            EngineClass = DirectSimulationEngine
        else:
            from webui.mock_simulation import MockSimulationEngine
            EngineClass = MockSimulationEngine

        engine = EngineClass(
            algorithm_name=algorithm_name,
            scenario_name=scenario_name,
            speed=speed,
            max_ticks=max_ticks,
            websocket=websocket
        )

        self.current_engine = engine
        return engine

    def get_current_engine(self):
        """获取当前运行的引擎"""
        return self.current_engine

    def clear_current_engine(self):
        """清除当前引擎引用"""
        self.current_engine = None
