#!/usr/bin/env python3
"""
Simple test runner that tests each scenario and collects results
Requires simulator to be running on http://127.0.0.1:8000
"""

import json
import time
from pathlib import Path
from typing import Dict, List
import statistics


def load_scenario_info(scenario_file: Path) -> Dict:
    """Load scenario metadata"""
    with open(scenario_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    building = data['building']
    return {
        'filename': scenario_file.name,
        'description': building.get('description', ''),
        'floors': building['floors'],
        'elevators': building['elevators'],
        'capacity': building['elevator_capacity'],
        'duration': building['duration'],
        'passengers': building['expected_passengers'],
        'scenario_type': building.get('scenario', 'unknown')
    }


def get_difficulty_stars(scenario_type: str, floors: int, passengers: int) -> str:
    """Determine difficulty level"""
    if floors <= 6 and passengers < 100:
        return "★☆☆☆☆"
    elif floors <= 10 and passengers < 150:
        return "★★☆☆☆"
    elif floors <= 10 and passengers < 200:
        return "★★★☆☆"
    elif floors <= 15 and passengers < 300:
        return "★★★★☆"
    else:
        return "★★★★★"


def format_metric(value: float, unit: str = "ticks") -> str:
    """Format metric with color coding"""
    if value is None:
        return "N/A"
    return f"{value:.2f} {unit}"


def print_scenario_header(info: Dict, index: int, total: int):
    """Print scenario header"""
    print("\n" + "="*80)
    print(f"测试 [{index}/{total}]: {info['filename']}")
    print("="*80)
    print(f"描述: {info['description']}")
    print(f"配置: {info['floors']}层 | {info['elevators']}部电梯 | 容量{info['capacity']}人")
    print(f"流量: {info['passengers']}位乘客 | {info['duration']} ticks")
    print(f"难度: {get_difficulty_stars(info['scenario_type'], info['floors'], info['passengers'])}")
    print("-"*80)


def collect_test_results() -> Dict:
    """Collect test results from user input"""
    print("\n请输入测试结果（从控制器输出中复制）:")
    print("示例格式:")
    print("{'average_wait_time': 122.47, 'p95_wait_time': 194.0, ...}")
    print("\n直接粘贴字典格式的输出，或输入 'skip' 跳过:")

    user_input = input("\n> ").strip()

    if user_input.lower() == 'skip':
        return None

    try:
        # Try to parse as dict
        if user_input.startswith('{'):
            results = eval(user_input)
            return {
                'average_wait_time': results.get('average_wait_time'),
                'p95_wait_time': results.get('p95_wait_time'),
                'average_system_time': results.get('average_system_time'),
                'p95_system_time': results.get('p95_system_time'),
                'completed_passengers': results.get('completed_passengers'),
                'total_passengers': results.get('total_passengers')
            }
    except:
        print("❌ 解析失败，跳过此场景")
        return None


def generate_summary_report(all_results: List[Dict], output_file: Path):
    """Generate comprehensive summary report"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 电梯调度算法测试报告\n\n")
        f.write(f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**测试场景**: {len(all_results)}个\n\n")

        # Summary statistics
        completed_tests = [r for r in all_results if r['results'] is not None]
        if completed_tests:
            f.write("## 总体统计\n\n")

            avg_waits = [r['results']['average_wait_time'] for r in completed_tests if r['results']['average_wait_time']]
            p95_waits = [r['results']['p95_wait_time'] for r in completed_tests if r['results']['p95_wait_time']]

            if avg_waits:
                f.write(f"- **平均等待时间均值**: {statistics.mean(avg_waits):.2f} ticks\n")
                f.write(f"- **平均等待时间中位数**: {statistics.median(avg_waits):.2f} ticks\n")
                f.write(f"- **P95等待时间均值**: {statistics.mean(p95_waits):.2f} ticks\n")
                f.write(f"- **P95等待时间中位数**: {statistics.median(p95_waits):.2f} ticks\n")
                f.write(f"- **完成测试数**: {len(completed_tests)}/{len(all_results)}\n\n")

        # Detailed results table
        f.write("## 详细结果\n\n")
        f.write("| 场景 | 描述 | 规模 | 平均等待 | P95等待 | 完成率 | 状态 |\n")
        f.write("|------|------|------|----------|---------|--------|------|\n")

        for result in all_results:
            info = result['info']
            results = result['results']

            scale = f"{info['floors']}F/{info['elevators']}E/{info['passengers']}P"

            if results:
                avg_wait = f"{results['average_wait_time']:.1f}" if results['average_wait_time'] else "N/A"
                p95_wait = f"{results['p95_wait_time']:.1f}" if results['p95_wait_time'] else "N/A"

                completion_rate = "100%"
                if results['completed_passengers'] and results['total_passengers']:
                    rate = results['completed_passengers'] / results['total_passengers']
                    completion_rate = f"{rate:.1%}"

                status = "✅ 完成"
            else:
                avg_wait = "-"
                p95_wait = "-"
                completion_rate = "-"
                status = "⏭️ 跳过"

            f.write(f"| {info['filename']} | {info['description'][:20]}... | {scale} | "
                   f"{avg_wait} | {p95_wait} | {completion_rate} | {status} |\n")

        # Performance by category
        f.write("\n## 按场景类型分类\n\n")

        scenario_types = {}
        for result in completed_tests:
            stype = result['info']['scenario_type']
            if stype not in scenario_types:
                scenario_types[stype] = []
            scenario_types[stype].append(result)

        for stype, results in scenario_types.items():
            f.write(f"### {stype}\n\n")
            avg_waits = [r['results']['average_wait_time'] for r in results if r['results']['average_wait_time']]
            if avg_waits:
                f.write(f"- 平均等待时间: {statistics.mean(avg_waits):.2f} ticks\n")
                f.write(f"- 测试数量: {len(results)}\n\n")

        # Recommendations
        f.write("\n## 性能分析与建议\n\n")
        f.write("### 优势场景\n\n")

        if completed_tests:
            # Find best performing scenarios
            sorted_by_wait = sorted(completed_tests,
                                   key=lambda x: x['results']['average_wait_time'] or float('inf'))
            if sorted_by_wait:
                best = sorted_by_wait[0]
                f.write(f"- **最佳表现**: {best['info']['filename']}\n")
                f.write(f"  - 平均等待: {best['results']['average_wait_time']:.2f} ticks\n")
                f.write(f"  - P95等待: {best['results']['p95_wait_time']:.2f} ticks\n\n")

            f.write("### 挑战场景\n\n")
            # Find challenging scenarios
            if len(sorted_by_wait) > 0:
                worst = sorted_by_wait[-1]
                f.write(f"- **最具挑战**: {worst['info']['filename']}\n")
                f.write(f"  - 平均等待: {worst['results']['average_wait_time']:.2f} ticks\n")
                f.write(f"  - P95等待: {worst['results']['p95_wait_time']:.2f} ticks\n\n")

        f.write("### 改进建议\n\n")
        f.write("1. 针对表现较差的场景，分析流量模式特点\n")
        f.write("2. 考虑针对特定场景优化调度策略\n")
        f.write("3. 关注P95指标，减少极端等待时间\n")
        f.write("4. 测试更多混合场景，提高算法鲁棒性\n\n")

    print(f"\n✅ 报告已生成: {output_file}")


def main():
    """Main test runner"""
    print("="*80)
    print("电梯调度算法 - 批量测试工具")
    print("="*80)

    # Check data directory
    data_dir = Path("data")
    if not data_dir.exists():
        print("❌ 错误: data/ 目录不存在")
        print("请先运行: uv run python generate_test_data.py")
        return

    # Get all test scenarios
    scenarios = sorted([f for f in data_dir.glob("*.json") if f.name != "README.json"])

    if not scenarios:
        print("❌ 错误: 未找到测试场景")
        return

    print(f"\n✅ 找到 {len(scenarios)} 个测试场景\n")

    # Instructions
    print("测试说明:")
    print("1. 确保模拟器正在运行: uv run python -m elevator_saga.server.simulator")
    print("2. 对每个场景，运行控制器并记录结果")
    print("3. 复制输出的性能指标字典（或输入 'skip' 跳过）")
    print("\n按 Enter 开始测试...")
    input()

    # Test each scenario
    all_results = []

    for i, scenario_file in enumerate(scenarios, 1):
        info = load_scenario_info(scenario_file)
        print_scenario_header(info, i, len(scenarios))

        print("\n📋 操作步骤:")
        print(f"   1. 确保模拟器已加载: {scenario_file.name}")
        print("   2. 运行: uv run python elevator_controller.py")
        print("   3. 等待测试完成，查看输出")

        # Collect results
        results = collect_test_results()

        all_results.append({
            'info': info,
            'results': results
        })

        if results:
            print(f"\n✅ 已记录: {info['filename']}")
            print(f"   平均等待: {format_metric(results['average_wait_time'])}")
            print(f"   P95等待: {format_metric(results['p95_wait_time'])}")
        else:
            print(f"\n⏭️  已跳过: {info['filename']}")

    # Generate reports
    print("\n" + "="*80)
    print("生成测试报告...")
    print("="*80)

    # Create output directory
    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)

    # Save JSON results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    json_file = output_dir / f"results_{timestamp}.json"

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_scenarios': len(scenarios),
            'completed_scenarios': len([r for r in all_results if r['results']]),
            'results': all_results
        }, f, indent=2, ensure_ascii=False)

    print(f"✅ JSON结果: {json_file}")

    # Generate markdown report
    md_file = output_dir / f"report_{timestamp}.md"
    generate_summary_report(all_results, md_file)

    # Summary
    completed = len([r for r in all_results if r['results']])
    print("\n" + "="*80)
    print("测试完成!")
    print("="*80)
    print(f"✅ 完成测试: {completed}/{len(scenarios)}")
    print(f"📊 JSON结果: {json_file}")
    print(f"📝 详细报告: {md_file}")
    print("="*80)


if __name__ == "__main__":
    main()
