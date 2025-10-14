"""
算法控制器
职责：处理算法相关的 HTTP 请求
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List
from webui.services import AlgorithmService
from webui.models import AlgorithmInfo


# 创建路由器
router = APIRouter(prefix="/api", tags=["algorithms"])

# 依赖注入：创建服务实例
algorithm_service = AlgorithmService()


@router.get("/algorithms")
async def get_algorithms() -> Dict[str, List[AlgorithmInfo]]:
    """
    获取可用算法列表

    Returns:
        Dict: {"algorithms": [AlgorithmInfo, ...]}
    """
    try:
        algorithms = algorithm_service.list_algorithms()
        # 将 Pydantic 模型转换为字典
        return {"algorithms": [algo.dict() for algo in algorithms]}
    except Exception as e:
        print(f"Error getting algorithms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/algorithms/{algorithm_name}")
async def get_algorithm(algorithm_name: str) -> AlgorithmInfo:
    """
    获取单个算法详情

    Args:
        algorithm_name: 算法名称

    Returns:
        AlgorithmInfo: 算法信息
    """
    try:
        algorithm = algorithm_service.get_algorithm(algorithm_name)
        return algorithm.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
