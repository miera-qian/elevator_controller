"""
算法业务逻辑服务
职责：处理算法相关的业务逻辑
"""
from typing import List
from webui.models import AlgorithmInfo, AlgorithmRepository


class AlgorithmService:
    """算法业务逻辑服务"""

    def __init__(self):
        self.repository = AlgorithmRepository()

    def list_algorithms(self) -> List[AlgorithmInfo]:
        """
        获取算法列表

        业务规则：
        1. 只返回已注册的算法
        2. 按类型排序（Heuristic > Hybrid > Machine Learning）

        Returns:
            List[AlgorithmInfo]: 算法列表
        """
        algorithms = self.repository.get_all()

        # 业务逻辑：按类型排序
        type_order = {"Heuristic": 1, "Hybrid": 2, "Machine Learning": 3}
        algorithms.sort(key=lambda a: (type_order.get(a.type, 99), a.name))

        return algorithms

    def get_algorithm(self, name: str) -> AlgorithmInfo:
        """
        获取单个算法信息

        Args:
            name: 算法名称

        Returns:
            AlgorithmInfo: 算法信息

        Raises:
            ValueError: 算法不存在
        """
        algorithm = self.repository.get_by_name(name)
        if not algorithm:
            raise ValueError(f"Algorithm '{name}' not found")
        return algorithm

    def validate_algorithm(self, name: str) -> bool:
        """
        验证算法是否存在

        Args:
            name: 算法名称

        Returns:
            bool: 是否存在
        """
        return self.repository.exists(name)
