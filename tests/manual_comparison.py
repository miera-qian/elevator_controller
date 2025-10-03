#!/usr/bin/env python3
"""
Manual Algorithm Comparison Script

This script helps you manually test and compare algorithms.
You need to manually load each scenario in the simulator web interface.

Usage:
1. Start simulator: uv run python -m elevator_saga.server.simulator
2. Run this script: uv run python tests/manual_comparison.py
3. Follow the prompts to load scenarios and run tests
"""

import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List


def load_scenario_files() -> List[Path]:
    """Load all scenario files"""
    data_dir = Path(__file__).parent.parent / "data"
    scenarios = sorted([f for f in data_dir.glob("*.json") if f.name != "README.json"])
    return scenarios


def load_scenario_info(scenario_file: Path) -> Dict:
    """Load scenario metadata"""
    with open(scenario_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    building = data['building']
    return {
        'filename': scenario_file.name,
        'name': scenario_file.stem,
        'description': building.get('description', ''),
        'floors': building['floors'],
        'elevators': building['elevators'],
        'capacity': building['elevator_capacity'],
        'duration': building['duration'],
        'passengers': building['expected_passengers'],
        'scenario_type': building.get('scenario', 'unknown')
    }


def run_algorithm_test(algorithm_name: str) -> Dict:
    """Run algorithm test"""
    print(f"\n  Running {algorithm_name}...")

    test_script = f"""
from algo import {algorithm_name}

algorithm = {algorithm_name}(enable_logging=False)
algorithm.start()
"""

    script_path = Path(__file__).parent / "_temp_test.py"
    script_path.write_text(test_script)

    try:
        result = subprocess.run(
            ['uv', 'run', 'python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=Path(__file__).parent.parent
        )

        # Parse results
        import re
        import ast

        dict_pattern = r'\{[^}]*\'average_wait_time\'[^}]*\}'
        match = re.search(dict_pattern, result.stdout, re.DOTALL)

        if match:
            dict_str = match.group(0)
            result_dict = ast.literal_eval(dict_str)

            metrics = {
                'avg_wait': result_dict.get('average_wait_time'),
                'p95_wait': result_dict.get('p95_wait_time'),
                'avg_system': result_dict.get('average_system_time'),
                'p95_system': result_dict.get('p95_system_time'),
                'served': result_dict.get('completed_passengers'),
                'total': result_dict.get('total_passengers')
            }

            if metrics['total'] and metrics['total'] > 0:
                metrics['completion_rate'] = (metrics['served'] / metrics['total']) * 100

            return metrics
        else:
            return {'error': 'No metrics found in output'}

    except subprocess.TimeoutExpired:
        return {'error': 'Timeout'}
    except Exception as e:
        return {'error': str(e)}
    finally:
        if script_path.exists():
            script_path.unlink()


def generate_report(results: Dict, output_file: Path):
    """Generate comparison report"""
    report = []
    report.append("# 电梯调度算法性能对比报告\n")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append("---\n")

    # Get algorithms
    algorithms = set()
    for scenario_data in results.values():
        algorithms.update(scenario_data['algorithms'].keys())
    algorithms = sorted(algorithms)

    report.append("## 测试概览\n")
    report.append(f"**测试算法**: {', '.join(algorithms)}\n")
    report.append(f"**测试场景数**: {len(results)}\n")
    report.append("\n")

    # Detailed results
    report.append("## 详细测试结果\n")
    report.append("| 场景 | 规模 | 算法 | 平均等待 | P95等待 | 平均系统时间 | 完成率 |\n")
    report.append("|------|------|------|----------|---------|-------------|--------|\n")

    for scenario_name, scenario_data in results.items():
        info = scenario_data['info']
        scale = f"{info['floors']}层/{info['elevators']}梯/{info['passengers']}人"

        for i, algorithm in enumerate(algorithms):
            metrics = scenario_data['algorithms'].get(algorithm, {})

            scenario_col = scenario_name if i == 0 else ""
            scale_col = scale if i == 0 else ""

            if 'error' in metrics:
                avg_wait = p95_wait = avg_system = completion = "ERROR"
            else:
                avg_wait = f"{metrics.get('avg_wait', 0):.1f}" if 'avg_wait' in metrics else "N/A"
                p95_wait = f"{metrics.get('p95_wait', 0):.1f}" if 'p95_wait' in metrics else "N/A"
                avg_system = f"{metrics.get('avg_system', 0):.1f}" if 'avg_system' in metrics else "N/A"
                completion = f"{metrics.get('completion_rate', 0):.1f}%" if 'completion_rate' in metrics else "N/A"

            report.append(f"| {scenario_col} | {scale_col} | {algorithm} | {avg_wait} | {p95_wait} | {avg_system} | {completion} |\n")

    report.append("\n")

    # Statistics
    algo_stats = {algo: {'avg_waits': [], 'p95_waits': []} for algo in algorithms}

    for scenario_data in results.values():
        for algorithm in algorithms:
            metrics = scenario_data['algorithms'].get(algorithm, {})
            if 'avg_wait' in metrics and 'error' not in metrics:
                algo_stats[algorithm]['avg_waits'].append(metrics['avg_wait'])
            if 'p95_wait' in metrics and 'error' not in metrics:
                algo_stats[algorithm]['p95_waits'].append(metrics['p95_wait'])

    report.append("## 整体性能统计\n")
    report.append("| 算法 | 平均等待时间 (均值) | P95等待时间 (均值) | 测试成功率 |\n")
    report.append("|------|---------------------|--------------------|-----------|\n")

    for algorithm in algorithms:
        stats = algo_stats[algorithm]
        avg_wait_mean = sum(stats['avg_waits']) / len(stats['avg_waits']) if stats['avg_waits'] else 0
        p95_wait_mean = sum(stats['p95_waits']) / len(stats['p95_waits']) if stats['p95_waits'] else 0
        success_rate = len(stats['avg_waits']) / len(results) * 100 if results else 0

        report.append(f"| {algorithm} | {avg_wait_mean:.2f} | {p95_wait_mean:.2f} | {success_rate:.0f}% |\n")

    report.append("\n")

    # Head-to-head if 2 algorithms
    if len(algorithms) == 2:
        report.append("### 直接对比 (胜/平/负)\n")
        algo1, algo2 = sorted(algorithms)

        wins = {'avg_wait': {algo1: 0, algo2: 0, 'tie': 0},
                'p95_wait': {algo1: 0, algo2: 0, 'tie': 0}}

        for scenario_data in results.values():
            metrics1 = scenario_data['algorithms'].get(algo1, {})
            metrics2 = scenario_data['algorithms'].get(algo2, {})

            if 'avg_wait' in metrics1 and 'avg_wait' in metrics2:
                diff = abs(metrics1['avg_wait'] - metrics2['avg_wait'])
                if diff < 1.0:
                    wins['avg_wait']['tie'] += 1
                elif metrics1['avg_wait'] < metrics2['avg_wait']:
                    wins['avg_wait'][algo1] += 1
                else:
                    wins['avg_wait'][algo2] += 1

            if 'p95_wait' in metrics1 and 'p95_wait' in metrics2:
                diff = abs(metrics1['p95_wait'] - metrics2['p95_wait'])
                if diff < 1.0:
                    wins['p95_wait']['tie'] += 1
                elif metrics1['p95_wait'] < metrics2['p95_wait']:
                    wins['p95_wait'][algo1] += 1
                else:
                    wins['p95_wait'][algo2] += 1

        report.append(f"**平均等待时间**: {algo1} {wins['avg_wait'][algo1]}胜 / "
                     f"{wins['avg_wait']['tie']}平 / {wins['avg_wait'][algo2]}负 {algo2}\n")
        report.append(f"**P95等待时间**: {algo1} {wins['p95_wait'][algo1]}胜 / "
                     f"{wins['p95_wait']['tie']}平 / {wins['p95_wait'][algo2]}负 {algo2}\n")
        report.append("\n")

    # Recommendations
    report.append("## 结论与建议\n")
    best_algo = min(algorithms,
                   key=lambda a: sum(algo_stats[a]['avg_waits']) / len(algo_stats[a]['avg_waits'])
                   if algo_stats[a]['avg_waits'] else float('inf'))

    report.append(f"根据平均等待时间指标，**{best_algo}** 表现最佳。\n")
    report.append("\n---\n")
    report.append("*报告由 manual_comparison.py 生成*\n")

    output_file.write_text(''.join(report), encoding='utf-8')
    print(f"\nReport saved to: {output_file}")


def main():
    """Main function"""
    print("="*60)
    print("Manual Algorithm Comparison Tool")
    print("="*60)

    scenarios = load_scenario_files()
    if not scenarios:
        print("No scenarios found!")
        return

    print(f"\nFound {len(scenarios)} scenarios")

    algorithms = ['OptimizedScanAlgorithm', 'RLDQNAlgorithm']
    print(f"Will test: {', '.join(algorithms)}\n")

    results = {}

    for scenario_file in scenarios:
        info = load_scenario_info(scenario_file)
        scenario_name = info['name']

        print(f"\n{'='*60}")
        print(f"Scenario: {scenario_name}")
        print(f"  {info['description']}")
        print(f"  {info['floors']} floors, {info['elevators']} elevators, {info['passengers']} passengers")
        print(f"{'='*60}")

        # Copy to traffic directory
        traffic_dir = Path(__file__).parent.parent / "traffic"
        import shutil
        shutil.copy(scenario_file, traffic_dir / "current_test.json")

        print(f"\n⚠️  Please reload the scenario in simulator web interface:")
        print(f"   1. Open http://127.0.0.1:8000")
        print(f"   2. Select 'current_test' from traffic dropdown")
        print(f"   3. Click reload/reset")

        input("\nPress ENTER when ready to start testing...")

        results[scenario_name] = {
            'info': info,
            'algorithms': {}
        }

        for algorithm in algorithms:
            metrics = run_algorithm_test(algorithm)
            results[scenario_name]['algorithms'][algorithm] = metrics

            if 'error' in metrics:
                print(f"  ✗ {algorithm}: ERROR - {metrics['error']}")
            else:
                avg_wait = metrics.get('avg_wait', 'N/A')
                p95_wait = metrics.get('p95_wait', 'N/A')
                print(f"  ✓ {algorithm}: Avg={avg_wait:.1f}, P95={p95_wait:.1f}")

    # Save results
    results_dir = Path(__file__).parent.parent / "test_results"
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON
    json_file = results_dir / f"comparison_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nRaw results saved to: {json_file}")

    # Report
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    report_file = docs_dir / f"algorithm_comparison_{timestamp}.md"

    generate_report(results, report_file)

    print(f"\n{'='*60}")
    print("Testing complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
