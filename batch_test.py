#!/usr/bin/env python3
"""
Batch testing script for elevator scheduling algorithm
Tests all scenarios in the data/ directory and generates performance reports
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List
import sys


class BatchTester:
    """Batch testing framework for elevator algorithms"""

    def __init__(self, data_dir: str = "data", output_dir: str = "test_results"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = []

    def get_test_scenarios(self) -> List[Path]:
        """Get all JSON test scenario files from data directory"""
        json_files = list(self.data_dir.glob("*.json"))
        # Exclude README.json
        json_files = [f for f in json_files if f.name != "README.json"]
        return sorted(json_files)

    def load_scenario_metadata(self, scenario_file: Path) -> Dict:
        """Load scenario metadata from JSON file"""
        with open(scenario_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "filename": scenario_file.name,
            "description": data["building"].get("description", ""),
            "floors": data["building"]["floors"],
            "elevators": data["building"]["elevators"],
            "capacity": data["building"]["elevator_capacity"],
            "duration": data["building"]["duration"],
            "passengers": data["building"]["expected_passengers"],
            "scenario_type": data["building"].get("scenario", "unknown")
        }

    def run_single_test(self, scenario_file: Path) -> Dict:
        """
        Run a single test scenario
        Note: This requires the simulator to support traffic file specification
        For now, we'll provide instructions for manual testing
        """
        print(f"\n{'='*80}")
        print(f"Testing: {scenario_file.name}")
        print(f"{'='*80}")

        metadata = self.load_scenario_metadata(scenario_file)

        print(f"Description: {metadata['description']}")
        print(f"Building: {metadata['floors']} floors, {metadata['elevators']} elevators")
        print(f"Passengers: {metadata['passengers']}, Duration: {metadata['duration']} ticks")
        print(f"\nNote: Please manually load {scenario_file.name} in the simulator")
        print("Then run the elevator controller and paste the results below.")
        print(f"\nWaiting for manual test completion...")

        # In a real implementation, you would:
        # 1. Start the simulator with the specific traffic file
        # 2. Start the controller
        # 3. Capture the output
        # 4. Parse the results
        #
        # For now, we'll create a placeholder result structure

        result = {
            "scenario": metadata["filename"],
            "description": metadata["description"],
            "config": {
                "floors": metadata["floors"],
                "elevators": metadata["elevators"],
                "capacity": metadata["capacity"],
                "duration": metadata["duration"],
                "passengers": metadata["passengers"]
            },
            "metrics": {
                "average_wait_time": None,
                "p95_wait_time": None,
                "average_system_time": None,
                "p95_system_time": None,
                "completed_passengers": None,
                "completion_rate": None
            },
            "status": "manual_test_required"
        }

        return result

    def generate_report(self):
        """Generate comprehensive test report"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"test_report_{timestamp}.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 电梯调度算法批量测试报告\n\n")
            f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"测试场景数量: {len(self.results)}\n\n")

            f.write("---\n\n")
            f.write("## 测试场景概览\n\n")

            for i, result in enumerate(self.results, 1):
                f.write(f"### {i}. {result['scenario']}\n\n")
                f.write(f"**描述**: {result['description']}\n\n")

                config = result['config']
                f.write(f"**配置**:\n")
                f.write(f"- 楼层数: {config['floors']}\n")
                f.write(f"- 电梯数: {config['elevators']}\n")
                f.write(f"- 电梯容量: {config['capacity']}人\n")
                f.write(f"- 测试时长: {config['duration']} ticks\n")
                f.write(f"- 乘客数: {config['passengers']}人\n\n")

                metrics = result['metrics']
                f.write(f"**性能指标**:\n")
                if metrics['average_wait_time'] is not None:
                    f.write(f"- 平均等待时间: {metrics['average_wait_time']:.2f} ticks\n")
                    f.write(f"- P95等待时间: {metrics['p95_wait_time']:.2f} ticks\n")
                    f.write(f"- 平均系统时间: {metrics['average_system_time']:.2f} ticks\n")
                    f.write(f"- P95系统时间: {metrics['p95_system_time']:.2f} ticks\n")
                    f.write(f"- 完成乘客数: {metrics['completed_passengers']}/{config['passengers']}\n")
                    f.write(f"- 完成率: {metrics['completion_rate']:.1%}\n")
                else:
                    f.write(f"- 状态: {result['status']}\n")

                f.write("\n")

            f.write("---\n\n")
            f.write("## 使用说明\n\n")
            f.write("本报告为模板，需要手动运行测试并填充结果。\n\n")
            f.write("### 测试步骤\n\n")
            f.write("1. 启动模拟器服务\n")
            f.write("```bash\n")
            f.write("uv run python -m elevator_saga.server.simulator\n")
            f.write("```\n\n")
            f.write("2. 在新终端运行控制器测试\n")
            f.write("```bash\n")
            f.write("uv run python elevator_controller.py\n")
            f.write("```\n\n")
            f.write("3. 记录每个场景的性能指标\n\n")

        print(f"\n✓ Report generated: {report_file}")
        return report_file

    def run_all_tests(self):
        """Run all test scenarios"""
        scenarios = self.get_test_scenarios()

        if not scenarios:
            print("No test scenarios found in data/ directory")
            return

        print(f"\nFound {len(scenarios)} test scenarios")
        print("="*80)

        for scenario in scenarios:
            result = self.run_single_test(scenario)
            self.results.append(result)

        print("\n" + "="*80)
        print("All scenarios listed. Manual testing required.")
        print("="*80)

        # Generate report
        self.generate_report()

        # Generate JSON summary
        self.save_results_json()

    def save_results_json(self):
        """Save results to JSON file"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_file = self.output_dir / f"test_results_{timestamp}.json"

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "total_scenarios": len(self.results),
                "results": self.results
            }, f, indent=2, ensure_ascii=False)

        print(f"✓ Results saved: {json_file}")


def print_manual_test_guide():
    """Print manual testing guide"""
    print("\n" + "="*80)
    print("手动测试指南")
    print("="*80)
    print()
    print("由于elevator-py框架的限制，当前需要手动测试每个场景。")
    print()
    print("自动化测试步骤：")
    print()
    print("1. 确保模拟器服务正在运行:")
    print("   uv run python -m elevator_saga.server.simulator")
    print()
    print("2. 模拟器会自动加载流量数据")
    print()
    print("3. 在新终端运行控制器:")
    print("   uv run python elevator_controller.py")
    print()
    print("4. 观察输出的性能指标")
    print()
    print("5. 记录以下数据:")
    print("   - average_wait_time (平均等待时间)")
    print("   - p95_wait_time (P95等待时间)")
    print("   - average_system_time (平均系统时间)")
    print("   - p95_system_time (P95系统时间)")
    print("   - completed_passengers (完成乘客数)")
    print()
    print("6. 重复上述步骤测试所有场景")
    print()
    print("="*80)


def create_automated_test_script():
    """Create an automated test script that can be customized"""
    script_content = '''#!/usr/bin/env python3
"""
Automated testing script (requires custom integration)
"""

import json
import time
from pathlib import Path
from elevator_controller import OptimizedElevatorController


def test_scenario(scenario_file: Path):
    """
    Test a single scenario

    Note: This is a template. You need to integrate with the simulator
    to actually run automated tests with different traffic files.
    """
    print(f"\\nTesting: {scenario_file.name}")

    # Load scenario
    with open(scenario_file, 'r', encoding='utf-8') as f:
        scenario_data = json.load(f)

    # TODO: Configure simulator to use this traffic data
    # This would require simulator API support

    # Run controller
    controller = OptimizedElevatorController()

    # TODO: Start test and capture results
    # controller.start()

    print("Manual test required - simulator needs traffic file configuration")

    return None


def main():
    data_dir = Path("data")
    scenarios = sorted([f for f in data_dir.glob("*.json") if f.name != "README.json"])

    results = []
    for scenario in scenarios:
        result = test_scenario(scenario)
        if result:
            results.append(result)

    # Save results
    with open("test_results/automated_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
'''

    with open("automated_test_template.py", "w", encoding="utf-8") as f:
        f.write(script_content)

    print("✓ Created automated_test_template.py")


def main():
    """Main entry point"""
    print("="*80)
    print("电梯调度算法 - 批量测试工具")
    print("="*80)

    # Create batch tester
    tester = BatchTester()

    # Check if data directory exists
    if not tester.data_dir.exists():
        print(f"Error: {tester.data_dir} directory not found")
        print("Please run generate_test_data.py first")
        sys.exit(1)

    # Print manual test guide
    print_manual_test_guide()

    print("\nPress Enter to continue and generate test report template...")
    input()

    # Run all tests (will create placeholders)
    tester.run_all_tests()

    # Create automated test template
    create_automated_test_script()

    print("\n" + "="*80)
    print("批量测试准备完成")
    print("="*80)
    print()
    print("生成的文件:")
    print(f"1. test_results/ - 测试报告目录")
    print(f"2. automated_test_template.py - 自动化测试模板")
    print()
    print("下一步:")
    print("1. 查看 test_results/ 目录中的测试报告模板")
    print("2. 手动运行每个场景并记录结果")
    print("3. 或者修改 automated_test_template.py 实现自动化测试")
    print()


if __name__ == "__main__":
    main()
