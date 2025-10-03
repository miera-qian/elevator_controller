#!/usr/bin/env python3
"""
Algorithm Comparison Test Script

Tests multiple algorithms on all scenarios and generates comparison report.
Requires simulator to be running on http://127.0.0.1:8000
"""

import json
import time
import subprocess
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime


def load_scenario_files() -> List[Path]:
    """Load all scenario files from data directory"""
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


def setup_scenario(scenario_file: Path) -> bool:
    """Setup scenario by copying to traffic directory and resetting"""
    try:
        # Copy scenario file to traffic directory
        traffic_dir = Path(__file__).parent.parent / "traffic"
        target_file = traffic_dir / "current_test.json"

        import shutil
        shutil.copy(scenario_file, target_file)

        # Reset simulator to load new traffic
        result = subprocess.run(
            ['curl', '-X', 'POST', 'http://127.0.0.1:8000/reset'],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error setting up scenario: {e}")
        return False


def run_algorithm_test(algorithm_name: str, scenario_file: Path) -> Dict:
    """Run single algorithm test on a scenario"""
    print(f"\n  Testing {algorithm_name}...")

    # Setup scenario
    if not setup_scenario(scenario_file):
        return {'error': 'Failed to setup scenario'}

    time.sleep(1)

    # Create temporary test script
    test_script = f"""
from algo import {algorithm_name}

algorithm = {algorithm_name}(enable_logging=False)
algorithm.start()
"""

    script_path = Path(__file__).parent / f"_temp_test_{algorithm_name}.py"
    script_path.write_text(test_script)

    try:
        # Run the algorithm
        result = subprocess.run(
            ['uv', 'run', 'python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=Path(__file__).parent.parent
        )

        output = result.stdout

        # Parse metrics from output (dict format from pprint)
        metrics = {}

        # Find the dict output
        import re
        import ast

        # Look for dictionary pattern in output
        dict_pattern = r'\{[^}]*\'average_wait_time\'[^}]*\}'
        match = re.search(dict_pattern, output, re.DOTALL)

        if match:
            try:
                # Extract and parse the dictionary
                dict_str = match.group(0)
                result_dict = ast.literal_eval(dict_str)

                metrics['avg_wait'] = result_dict.get('average_wait_time')
                metrics['p95_wait'] = result_dict.get('p95_wait_time')
                metrics['avg_system'] = result_dict.get('average_system_time')
                metrics['p95_system'] = result_dict.get('p95_system_time')
                metrics['served'] = result_dict.get('completed_passengers')
                metrics['total'] = result_dict.get('total_passengers')

                if metrics['total'] and metrics['total'] > 0:
                    metrics['completion_rate'] = (metrics['served'] / metrics['total']) * 100
            except Exception as e:
                print(f"      Error parsing metrics: {e}")

        return metrics

    except subprocess.TimeoutExpired:
        return {'error': 'Timeout'}
    except Exception as e:
        return {'error': str(e)}
    finally:
        # Cleanup
        if script_path.exists():
            script_path.unlink()
        time.sleep(2)


def test_all_algorithms(scenarios: List[Path], algorithms: List[str]) -> Dict:
    """Test all algorithms on all scenarios"""
    results = {}

    for scenario_file in scenarios:
        info = load_scenario_info(scenario_file)
        scenario_name = info['name']

        print(f"\n{'='*60}")
        print(f"Testing: {scenario_name}")
        print(f"  {info['description']}")
        print(f"  {info['floors']} floors, {info['elevators']} elevators, {info['passengers']} passengers")
        print(f"{'='*60}")

        results[scenario_name] = {
            'info': info,
            'algorithms': {}
        }

        for algorithm in algorithms:
            metrics = run_algorithm_test(algorithm, scenario_file)
            results[scenario_name]['algorithms'][algorithm] = metrics

            # Print quick summary
            if 'error' in metrics:
                print(f"    {algorithm}: ERROR - {metrics['error']}")
            else:
                avg_wait = metrics.get('avg_wait', 'N/A')
                p95_wait = metrics.get('p95_wait', 'N/A')
                print(f"    {algorithm}: Avg={avg_wait}, P95={p95_wait}")

    return results


def generate_report(results: Dict, output_file: Path):
    """Generate comparison report in Markdown"""

    report = []
    report.append("# 电梯调度算法性能对比报告\n")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append("---\n")

    # Overview
    report.append("## 测试概览\n")
    algorithms = set()
    for scenario_data in results.values():
        algorithms.update(scenario_data['algorithms'].keys())
    algorithms = sorted(algorithms)

    report.append(f"**测试算法**: {', '.join(algorithms)}\n")
    report.append(f"**测试场景数**: {len(results)}\n")
    report.append("")

    # Detailed results table
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

            avg_wait = f"{metrics.get('avg_wait', 0):.1f}" if 'avg_wait' in metrics else "N/A"
            p95_wait = f"{metrics.get('p95_wait', 0):.1f}" if 'p95_wait' in metrics else "N/A"
            avg_system = f"{metrics.get('avg_system', 0):.1f}" if 'avg_system' in metrics else "N/A"
            completion = f"{metrics.get('completion_rate', 0):.1f}%" if 'completion_rate' in metrics else "N/A"

            if 'error' in metrics:
                avg_wait = p95_wait = avg_system = completion = f"ERROR"

            report.append(f"| {scenario_col} | {scale_col} | {algorithm} | {avg_wait} | {p95_wait} | {avg_system} | {completion} |\n")

    report.append("\n")

    # Algorithm comparison summary
    report.append("## 算法对比分析\n")

    # Calculate average metrics per algorithm
    algo_stats = {algo: {'avg_waits': [], 'p95_waits': [], 'completion_rates': []}
                  for algo in algorithms}

    for scenario_data in results.values():
        for algorithm in algorithms:
            metrics = scenario_data['algorithms'].get(algorithm, {})
            if 'avg_wait' in metrics and 'error' not in metrics:
                algo_stats[algorithm]['avg_waits'].append(metrics['avg_wait'])
            if 'p95_wait' in metrics and 'error' not in metrics:
                algo_stats[algorithm]['p95_waits'].append(metrics['p95_wait'])
            if 'completion_rate' in metrics and 'error' not in metrics:
                algo_stats[algorithm]['completion_rates'].append(metrics['completion_rate'])

    report.append("### 整体性能统计\n")
    report.append("| 算法 | 平均等待时间 (均值) | P95等待时间 (均值) | 完成率 (均值) | 测试成功率 |\n")
    report.append("|------|---------------------|--------------------|--------------|-----------|\n")

    for algorithm in algorithms:
        stats = algo_stats[algorithm]

        avg_wait_mean = sum(stats['avg_waits']) / len(stats['avg_waits']) if stats['avg_waits'] else 0
        p95_wait_mean = sum(stats['p95_waits']) / len(stats['p95_waits']) if stats['p95_waits'] else 0
        completion_mean = sum(stats['completion_rates']) / len(stats['completion_rates']) if stats['completion_rates'] else 0
        success_rate = len(stats['avg_waits']) / len(results) * 100 if results else 0

        report.append(f"| {algorithm} | {avg_wait_mean:.2f} | {p95_wait_mean:.2f} | {completion_mean:.1f}% | {success_rate:.0f}% |\n")

    report.append("\n")

    # Head-to-head comparison
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
                if diff < 1.0:  # Consider <1 tick as tie
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

    # Find best algorithm by average wait time
    best_algo = min(algorithms,
                   key=lambda a: sum(algo_stats[a]['avg_waits']) / len(algo_stats[a]['avg_waits'])
                   if algo_stats[a]['avg_waits'] else float('inf'))

    report.append(f"### 最佳算法\n")
    report.append(f"根据平均等待时间指标，**{best_algo}** 表现最佳。\n")
    report.append("\n")

    report.append("### 使用建议\n")
    for algorithm in algorithms:
        report.append(f"- **{algorithm}**: ")

        if algorithm == "OptimizedScanAlgorithm":
            report.append("适用于中小型建筑、混合流量场景，性能稳定可靠，无需训练。\n")
        elif algorithm == "RLDQNAlgorithm":
            report.append("适用于需要自适应学习的场景，初期性能可能较差，需要大量训练数据。建议在流量模式固定但未知时使用。\n")
        else:
            report.append("详见算法文档。\n")

    report.append("\n---\n")
    report.append("*报告由 compare_algorithms.py 自动生成*\n")

    # Write to file
    output_file.write_text(''.join(report), encoding='utf-8')
    print(f"\n{'='*60}")
    print(f"Report saved to: {output_file}")
    print(f"{'='*60}")


def main():
    """Main test execution"""
    print("="*60)
    print("Algorithm Comparison Test")
    print("="*60)

    # Load scenarios
    scenarios = load_scenario_files()
    if not scenarios:
        print("No scenario files found in data/ directory")
        return

    print(f"\nFound {len(scenarios)} test scenarios")

    # Define algorithms to test
    algorithms = ['OptimizedScanAlgorithm', 'RLDQNAlgorithm']
    print(f"Testing algorithms: {', '.join(algorithms)}")

    # Run tests
    results = test_all_algorithms(scenarios, algorithms)

    # Save raw results
    results_dir = Path(__file__).parent.parent / "test_results"
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = results_dir / f"comparison_{timestamp}.json"

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nRaw results saved to: {json_file}")

    # Generate report
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    report_file = docs_dir / f"algorithm_comparison_{timestamp}.md"

    generate_report(results, report_file)


if __name__ == "__main__":
    main()
