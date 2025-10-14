"""
场景控制器
职责：处理场景相关的 HTTP 请求
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List
from webui.services import ScenarioService
from webui.models import ScenarioInfo


# 创建路由器
router = APIRouter(prefix="/api", tags=["scenarios"])

# 依赖注入：创建服务实例
scenario_service = ScenarioService()


@router.get("/scenarios")
async def get_scenarios() -> Dict[str, List[ScenarioInfo]]:
    """
    获取可用场景列表

    Returns:
        Dict: {"scenarios": [ScenarioInfo, ...]}
    """
    try:
        scenarios = scenario_service.list_scenarios()
        # 将 Pydantic 模型转换为字典
        return {"scenarios": [scenario.dict() for scenario in scenarios]}
    except Exception as e:
        print(f"Error getting scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scenarios/{scenario_name}")
async def get_scenario(scenario_name: str) -> ScenarioInfo:
    """
    获取单个场景详情

    Args:
        scenario_name: 场景名称

    Returns:
        ScenarioInfo: 场景信息
    """
    try:
        scenario = scenario_service.get_scenario(scenario_name)
        return scenario.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
