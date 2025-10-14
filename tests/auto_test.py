#!/usr/bin/env python3
"""
Fully Automated Algorithm Testing Script

Automatically starts/stops simulator server for each test,
tests all algorithms on all datasets with complete isolation.

Usage:
    uv run python tests/auto_test.py
    uv run python tests/auto_test.py --algorithms OptimizedScanAlgorithm,RLDQNAlgorithm
    uv run python tests/auto_test.py --scenarios small_morning_rush,medium_inter_floor
"""

import json
import time
import subprocess
import sys
import signal
import argparse
import shutil
import re
import ast
import socket
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import requests
import os


class ServerManager:
    """Manages elevator simulator server lifecycle"""

    def __init__(self, port: int = 8000, startup_timeout: int = 60):
        self.port = port
        self.startup_timeout = startup_timeout
        self.process: Optional[subprocess.Popen] = None
        self.project_root = Path(__file__).parent.parent

    def is_port_free(self) -> bool:
        """Check if port is available"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('127.0.0.1', self.port))
            sock.close()
            return True
        except OSError:
            return False

    def wait_for_port_free(self, timeout: int = 10) -> bool:
        """Wait for port to be released"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_port_free():
                return True
            time.sleep(0.5)
        return False

    def wait_for_server(self) -> bool:
        """Wait for server to be ready"""
        start_time = time.time()
        url = f"http://127.0.0.1:{self.port}/"

        print("  Waiting for server to be ready...", end='', flush=True)

        # Need to wait longer as Flask debug mode restarts the server
        consecutive_successes = 0
        required_successes = 3  # Need 3 consecutive successful responses

        while time.time() - start_time < self.startup_timeout:
            try:
                response = requests.get(url, timeout=5)
                # Accept any HTTP response (even 404) as server is running
                if response.status_code in [200, 404]:
                    consecutive_successes += 1
                    if consecutive_successes >= required_successes:
                        print(" ✓")
                        return True
                    time.sleep(1)  # Wait between checks
                else:
                    consecutive_successes = 0
            except (requests.ConnectionError, requests.Timeout):
                consecutive_successes = 0
                pass

            # Show progress
            elapsed = int(time.time() - start_time)
            if elapsed > 0 and elapsed % 5 == 0:
                print(".", end='', flush=True)

            time.sleep(2)

        print(" ✗")
        return False

    def start(self) -> bool:
        """Start simulator server"""
        print(f"Starting simulator server on port {self.port}...")

        # Ensure port is free
        if not self.is_port_free():
            print(f"  ⚠ Port {self.port} is in use, waiting for it to be freed...")
            if not self.wait_for_port_free():
                print(f"  ✗ Port {self.port} is still in use after timeout")
                return False
        popen_kwargs = {
            'cwd': self.project_root,
            'stdout': subprocess.DEVNULL,
            'stderr': subprocess.PIPE,
            'text': True,
        }
        # On POSIX systems (Linux, macOS), use preexec_fn to ignore SIGINT in the child.
        if os.name == 'posix':
            popen_kwargs['preexec_fn'] = lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
        # On Windows, create a new process group to prevent Ctrl+C from affecting the child.
        elif os.name == 'nt':
            popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

        # Start server
        try:
            # Use the prepared arguments
            self.process = subprocess.Popen(
                ['uv', 'run', 'python', '-m', 'elevator_saga.server.simulator'],
                **popen_kwargs
            )

            # Wait for server to be ready
            if self.wait_for_server():
                return True
            else:
                print("  ✗ Server failed to start within timeout")
                # Check if process is still running
                if self.process.poll() is not None:
                    # Process died, show error
                    stderr_output = self.process.stderr.read() if self.process.stderr else ""
                    if stderr_output:
                        print(f"  Server error: {stderr_output[:200]}")
                self.stop()
                return False

        except Exception as e:
            print(f"  ✗ Failed to start server: {e}")
            return False

    def stop(self) -> bool:
        """Stop simulator server"""
        if self.process is None:
            return True

        print("  Stopping server...")

        try:
            if os.name == 'nt':  # Windows-specific termination
                # Sending CTRL_BREAK_EVENT to the process group is a more reliable
                # way to terminate a console application and its children on Windows.
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
                self.process.wait(timeout=10)  # Wait for the process to exit
            else:  # POSIX graceful termination
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if not responding
                    print("  Server not responding, forcing kill...")
                    self.process.kill()
                    self.process.wait(timeout=2)
        except (ProcessLookupError, PermissionError):
            # Process might have already terminated, which is fine.
            pass
        except subprocess.TimeoutExpired:
            print("  ⚠ Server did not stop within timeout, attempting final kill.")
            # Final kill attempt for any OS if wait times out
            try:
                self.process.kill()
            except ProcessLookupError:
                pass  # Already gone
        except Exception as e:
            print(f"  ⚠ Error stopping server: {e}")

        self.process = None

        # Wait for port to be released
        if not self.wait_for_port_free(timeout=10):
            print(f"  ⚠ Port {self.port} may still be in use")
            return False

        print("  ✓ Server stopped")
        return True

    def restart(self) -> bool:
        """Restart server"""
        self.stop()
        time.sleep(2)  # Extra cooldown
        return self.start()


class AutoTester:
    """Automated testing orchestrator"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.server_manager = ServerManager()
        self.results: Dict = {}

    def get_algorithms(self, filter_list: Optional[List[str]] = None) -> List[str]:
        """Get list of algorithms to test"""
        # Import to get __all__
        import sys
        sys.path.insert(0, str(self.project_root))
        from algo import __all__ as all_algorithms

        algorithms = list(all_algorithms)

        if filter_list:
            algorithms = [a for a in algorithms if a in filter_list]

        return algorithms

    def get_scenarios(self, filter_list: Optional[List[str]] = None) -> List[Path]:
        """Get list of scenario files to test"""
        data_dir = self.project_root / "data"
        scenarios = sorted([f for f in data_dir.glob("*.json") if f.name != "README.json"])

        if filter_list:
            # Filter by stem (filename without extension)
            scenarios = [s for s in scenarios if s.stem in filter_list]

        return scenarios

    def load_scenario_info(self, scenario_file: Path) -> Dict:
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

    def prepare_scenario(self, scenario_file: Path) -> bool:
        """Copy scenario to traffic directory, replacing sample_traffic.json"""
        try:
            traffic_dir = self.project_root / "traffic"
            # Replace sample_traffic.json so server loads our scenario
            target_file = traffic_dir / "sample_traffic.json"

            # Backup original if it exists
            if target_file.exists():
                backup_file = traffic_dir / "sample_traffic.json.bak"
                if not backup_file.exists():
                    shutil.copy(target_file, backup_file)

            shutil.copy(scenario_file, target_file)
            time.sleep(0.5)  # Give filesystem time to sync
            return True
        except Exception as e:
            print(f"  ✗ Failed to prepare scenario: {e}")
            return False

    def run_algorithm(self, algorithm_name: str, scenario_name: str, timeout: int = 300) -> Dict:
        """Run single algorithm test"""
        print(f"    Running {algorithm_name}...", end='', flush=True)

        # Create test script
        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from algo import {algorithm_name}

algorithm = {algorithm_name}(enable_logging=False)
algorithm.start()
"""

        script_path = self.project_root / "tests" / f"_temp_{algorithm_name}_{scenario_name}.py"
        script_path.write_text(test_script)

        try:
            # Run algorithm
            result = subprocess.run(
                ['uv', 'run', 'python', str(script_path)],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Parse metrics
            metrics = self.parse_metrics(result.stdout)

            if 'error' in metrics:
                print(f" ✗ {metrics['error']}")
                # Show debugging info
                if result.stderr:
                    print(f"      Error:")
                    for line in result.stderr.split('\n')[:10]:
                        if line.strip():
                            print(f"        {line}")
            else:
                avg_wait = metrics.get('avg_wait', 0)
                p95_wait = metrics.get('p95_wait', 0)
                print(f" ✓ Avg={avg_wait:.1f}, P95={p95_wait:.1f}")

            return metrics

        except subprocess.TimeoutExpired:
            print(" ✗ Timeout")
            return {'error': 'Timeout'}
        except Exception as e:
            print(f" ✗ {str(e)}")
            return {'error': str(e)}
        finally:
            # Cleanup
            if script_path.exists():
                script_path.unlink()

    def parse_metrics(self, output: str) -> Dict:
        """Parse performance metrics from algorithm output"""
        # Look for dictionary pattern in output
        dict_pattern = r'\{[^}]*\'average_wait_time\'[^}]*\}'
        match = re.search(dict_pattern, output, re.DOTALL)

        if match:
            try:
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
            except Exception as e:
                return {'error': f'Parse error: {str(e)}'}

        return {'error': 'No metrics found in output'}

    def run_test(self, algorithm: str, scenario_file: Path) -> Tuple[bool, Dict]:
        """Run complete test: prepare scenario, start server, run algorithm, stop server"""
        scenario_info = self.load_scenario_info(scenario_file)
        scenario_name = scenario_info['name']

        print(f"\n  Scenario: {scenario_name}")
        print(f"    {scenario_info['description']}")
        print(f"    {scenario_info['floors']} floors, {scenario_info['elevators']} elevators, "
              f"{scenario_info['passengers']} passengers")

        # Prepare scenario BEFORE starting server
        if not self.prepare_scenario(scenario_file):
            return False, {'error': 'Failed to prepare scenario'}

        # Start server (will load the scenario we just copied)
        if not self.server_manager.start():
            return False, {'error': 'Failed to start server'}

        try:
            # Run algorithm
            metrics = self.run_algorithm(algorithm, scenario_name)

            return True, metrics

        finally:
            # Always stop server
            self.server_manager.stop()
            time.sleep(1)  # Cooldown between tests

    def run_all_tests(self, algorithms: List[str], scenarios: List[Path]):
        """Run all tests with full isolation"""
        total_tests = len(algorithms) * len(scenarios)
        current_test = 0

        print(f"\n{'='*70}")
        print(f"Automated Testing")
        print(f"{'='*70}")
        print(f"Algorithms: {', '.join(algorithms)}")
        print(f"Scenarios: {len(scenarios)}")
        print(f"Total tests: {total_tests}")
        print(f"{'='*70}\n")

        start_time = time.time()

        # Test each algorithm on each scenario
        for algorithm in algorithms:
            print(f"\n{'='*70}")
            print(f"Testing Algorithm: {algorithm}")
            print(f"{'='*70}")

            self.results[algorithm] = {}

            for scenario_file in scenarios:
                current_test += 1
                scenario_name = scenario_file.stem

                print(f"\n[{current_test}/{total_tests}] {algorithm} on {scenario_name}")

                success, metrics = self.run_test(algorithm, scenario_file)

                # Store results
                scenario_info = self.load_scenario_info(scenario_file)
                self.results[algorithm][scenario_name] = {
                    'info': scenario_info,
                    'metrics': metrics,
                    'success': success
                }

        elapsed_time = time.time() - start_time

        print(f"\n{'='*70}")
        print(f"Testing Complete!")
        print(f"Total time: {elapsed_time:.1f} seconds")
        print(f"{'='*70}\n")

    def save_results(self, output_dir: Path):
        """Save test results to files"""
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON
        json_file = output_dir / f"auto_test_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"Results saved to: {json_file}")

        # Generate report
        report_file = self.project_root / "docs" / f"auto_test_report_{timestamp}.md"
        self.generate_report(report_file)

        return json_file, report_file

    def generate_report(self, output_file: Path):
        """Generate markdown report"""
        report = []

        report.append("# 自动化测试报告\n")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append("---\n\n")

        # Summary
        algorithms = list(self.results.keys())
        total_scenarios = len(self.results[algorithms[0]]) if algorithms else 0

        report.append("## 测试概览\n\n")
        report.append(f"**测试算法**: {', '.join(algorithms)}\n\n")
        report.append(f"**测试场景数**: {total_scenarios}\n\n")
        report.append(f"**测试方法**: 每个测试都在独立的服务器实例中运行，确保完全隔离\n\n")

        # Detailed results table
        report.append("## 详细测试结果\n\n")
        report.append("| 算法 | 场景 | 规模 | 平均等待 | P95等待 | 平均系统时间 | 完成率 | 状态 |\n")
        report.append("|------|------|------|----------|---------|-------------|--------|----- |\n")

        for algorithm in algorithms:
            algo_results = self.results[algorithm]

            for scenario_name, data in sorted(algo_results.items()):
                info = data['info']
                metrics = data['metrics']
                success = data['success']

                scale = f"{info['floors']}层/{info['elevators']}梯/{info['passengers']}人"

                if 'error' in metrics:
                    avg_wait = p95_wait = avg_system = completion = "N/A"
                    status = f"❌ {metrics['error']}"
                else:
                    avg_wait = f"{metrics.get('avg_wait', 0):.1f}"
                    p95_wait = f"{metrics.get('p95_wait', 0):.1f}"
                    avg_system = f"{metrics.get('avg_system', 0):.1f}"
                    completion = f"{metrics.get('completion_rate', 0):.1f}%"
                    status = "✅" if success else "❌"

                report.append(f"| {algorithm} | {scenario_name} | {scale} | {avg_wait} | "
                            f"{p95_wait} | {avg_system} | {completion} | {status} |\n")

        report.append("\n")

        # Statistics per algorithm
        report.append("## 算法性能统计\n\n")
        report.append("| 算法 | 成功率 | 平均等待时间 (均值) | P95等待时间 (均值) | 完成率 (均值) |\n")
        report.append("|------|--------|---------------------|--------------------|--------------|\n")

        for algorithm in algorithms:
            algo_results = self.results[algorithm]

            successful = sum(1 for d in algo_results.values() if d['success'] and 'error' not in d['metrics'])
            total = len(algo_results)
            success_rate = (successful / total * 100) if total > 0 else 0

            avg_waits = [d['metrics']['avg_wait'] for d in algo_results.values()
                        if 'avg_wait' in d['metrics'] and 'error' not in d['metrics']]
            p95_waits = [d['metrics']['p95_wait'] for d in algo_results.values()
                        if 'p95_wait' in d['metrics'] and 'error' not in d['metrics']]
            completions = [d['metrics']['completion_rate'] for d in algo_results.values()
                          if 'completion_rate' in d['metrics'] and 'error' not in d['metrics']]

            avg_wait_mean = sum(avg_waits) / len(avg_waits) if avg_waits else 0
            p95_wait_mean = sum(p95_waits) / len(p95_waits) if p95_waits else 0
            completion_mean = sum(completions) / len(completions) if completions else 0

            report.append(f"| {algorithm} | {success_rate:.0f}% | {avg_wait_mean:.2f} | "
                        f"{p95_wait_mean:.2f} | {completion_mean:.1f}% |\n")

        report.append("\n---\n\n")
        report.append("*本报告由 auto_test.py 自动生成*\n")

        # Write report
        output_file.write_text(''.join(report), encoding='utf-8')
        print(f"Report saved to: {output_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Automated algorithm testing with server management')
    parser.add_argument('--algorithms', type=str, help='Comma-separated list of algorithms to test')
    parser.add_argument('--scenarios', type=str, help='Comma-separated list of scenarios to test')
    parser.add_argument('--output-dir', type=str, default='test_results', help='Output directory for results')

    args = parser.parse_args()

    # Setup
    project_root = Path(__file__).parent.parent
    tester = AutoTester(project_root)

    # Get algorithms and scenarios
    algorithm_filter = args.algorithms.split(',') if args.algorithms else None
    scenario_filter = args.scenarios.split(',') if args.scenarios else None

    algorithms = tester.get_algorithms(algorithm_filter)
    scenarios = tester.get_scenarios(scenario_filter)

    if not algorithms:
        print("Error: No algorithms found")
        sys.exit(1)

    if not scenarios:
        print("Error: No scenarios found")
        sys.exit(1)

    # Run tests
    try:
        tester.run_all_tests(algorithms, scenarios)

        # Save results
        output_dir = project_root / args.output_dir
        tester.save_results(output_dir)

    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user")
        tester.server_manager.stop()
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        tester.server_manager.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
