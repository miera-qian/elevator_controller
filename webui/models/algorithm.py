"""
算法数据模型
职责：封装算法数据和数据访问逻辑
"""
from typing import List, Optional, Dict
from pydantic import BaseModel


class AlgorithmInfo(BaseModel):
    """算法信息数据模型"""
    name: str
    display_name: str
    description: str
    type: str  # "Heuristic", "Machine Learning", "Hybrid"


class AlgorithmRepository:
    """
    算法数据仓库
    职责：管理算法元数据，提供数据访问接口
    """

    # 算法元数据配置
    ALGORITHM_METADATA: Dict[str, AlgorithmInfo] = {
        "SimpleFCFSAlgorithm": AlgorithmInfo(
            name="SimpleFCFSAlgorithm",
            display_name="Simple FCFS (测试用)",
            description="简单的先来先服务算法 - 用于测试电梯基本功能",
            type="Heuristic"
        ),
        "OptimizedScanAlgorithm": AlgorithmInfo(
            name="OptimizedScanAlgorithm",
            display_name="Optimized SCAN",
            description="优化SCAN算法 - 智能评分系统",
            type="Heuristic"
        ),
        "RLDQNAlgorithm": AlgorithmInfo(
            name="RLDQNAlgorithm",
            display_name="RL DQN",
            description="强化学习Q-learning算法",
            type="Machine Learning"
        ),
        "HybridScanRLAlgorithm": AlgorithmInfo(
            name="HybridScanRLAlgorithm",
            display_name="Hybrid SCAN-RL ⭐",
            description="混合SCAN-RL算法 (推荐)",
            type="Hybrid"
        ),
        "ScanController": AlgorithmInfo(
            name="ScanController",
            display_name="BASE SCAN",
            description="基础SCAN算法",
            type="Heuristic"
        )
    }

    @classmethod
    def get_all(cls) -> List[AlgorithmInfo]:
        """
        获取所有可用算法

        Returns:
            List[AlgorithmInfo]: 可用算法列表
        """
        import algo
        available_algorithms = []

        for algo_name in algo.__all__:
            if algo_name in cls.ALGORITHM_METADATA:
                available_algorithms.append(cls.ALGORITHM_METADATA[algo_name])

        return available_algorithms

    @classmethod
    def get_by_name(cls, name: str) -> Optional[AlgorithmInfo]:
        """
        根据名称获取算法信息

        Args:
            name: 算法名称

        Returns:
            Optional[AlgorithmInfo]: 算法信息，不存在则返回 None
        """
        return cls.ALGORITHM_METADATA.get(name)

    @classmethod
    def exists(cls, name: str) -> bool:
        """
        检查算法是否存在

        Args:
            name: 算法名称

        Returns:
            bool: 是否存在
        """
        return name in cls.ALGORITHM_METADATA
