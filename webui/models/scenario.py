"""
场景数据模型
职责：封装场景数据和数据访问逻辑
"""
from typing import List, Optional
from pathlib import Path
import json
from pydantic import BaseModel


class ScenarioInfo(BaseModel):
    """场景信息数据模型"""
    name: str
    display_name: str
    floors: int
    elevators: int
    passengers: int
    duration: int
    capacity: int = 8
    scale: str = "unknown"
    type: str = "mixed"


class ScenarioRepository:
    """
    场景数据仓库
    职责：从文件系统加载场景数据
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        初始化场景仓库

        Args:
            data_dir: 数据目录路径，默认为 ./traffic (统一的traffic目录)
        """
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent.parent / "traffic"
        else:
            self.data_dir = data_dir

    def get_all(self) -> List[ScenarioInfo]:
        """
        获取所有可用场景

        Returns:
            List[ScenarioInfo]: 场景信息列表
        """
        scenarios = []

        for json_file in sorted(self.data_dir.glob("*.json")):
            if json_file.name == "README.json":
                continue

            try:
                scenario_info = self._load_scenario_file(json_file)
                if scenario_info:
                    scenarios.append(scenario_info)
            except Exception as e:
                print(f"Error loading scenario {json_file}: {e}")
                continue

        return scenarios

    def get_by_name(self, name: str) -> Optional[ScenarioInfo]:
        """
        根据名称获取场景信息

        Args:
            name: 场景名称（文件名不含扩展名）

        Returns:
            Optional[ScenarioInfo]: 场景信息，不存在则返回 None
        """
        scenario_file = self.data_dir / f"{name}.json"

        if not scenario_file.exists():
            return None

        return self._load_scenario_file(scenario_file)

    def _load_scenario_file(self, file_path: Path) -> Optional[ScenarioInfo]:
        """
        从文件加载场景信息

        Args:
            file_path: 场景文件路径

        Returns:
            Optional[ScenarioInfo]: 场景信息
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            building = data.get("building", {})
            traffic = data.get("traffic", [])

            return ScenarioInfo(
                name=file_path.stem,
                display_name=building.get("description", file_path.stem),
                floors=building.get("floors", 0),
                elevators=building.get("elevators", 0),
                passengers=building.get("expected_passengers", len(traffic)),
                duration=building.get("duration", 0),
                capacity=building.get("elevator_capacity", 8),
                scale=building.get("scale", "unknown"),
                type=building.get("scenario", "mixed")
            )
        except Exception as e:
            print(f"Error parsing scenario file {file_path}: {e}")
            return None

    def exists(self, name: str) -> bool:
        """
        检查场景是否存在

        Args:
            name: 场景名称

        Returns:
            bool: 是否存在
        """
        scenario_file = self.data_dir / f"{name}.json"
        return scenario_file.exists()
