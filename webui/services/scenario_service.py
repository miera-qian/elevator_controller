"""
场景业务逻辑服务
职责：处理场景相关的业务逻辑
"""
from typing import List
from webui.models import ScenarioInfo, ScenarioRepository


class ScenarioService:
    """场景业务逻辑服务"""

    def __init__(self):
        self.repository = ScenarioRepository()

    def list_scenarios(self) -> List[ScenarioInfo]:
        """
        获取场景列表

        Returns:
            List[ScenarioInfo]: 场景列表
        """
        return self.repository.get_all()

    def get_scenario(self, name: str) -> ScenarioInfo:
        """
        获取单个场景信息

        Args:
            name: 场景名称

        Returns:
            ScenarioInfo: 场景信息

        Raises:
            ValueError: 场景不存在
        """
        scenario = self.repository.get_by_name(name)
        if not scenario:
            raise ValueError(f"Scenario '{name}' not found")
        return scenario

    def validate_scenario(self, name: str) -> bool:
        """
        验证场景是否存在

        Args:
            name: 场景名称

        Returns:
            bool: 是否存在
        """
        return self.repository.exists(name)
