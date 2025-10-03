# 电梯调度算法自动化测试完整指南

## 目录

1. [概述](#概述)
2. [系统架构](#系统架构)
3. [核心组件](#核心组件)
4. [使用指南](#使用指南)
5. [测试流程详解](#测试流程详解)
6. [配置与定制](#配置与定制)
7. [故障排查](#故障排查)
8. [性能优化](#性能优化)
9. [最佳实践](#最佳实践)
10. [技术细节](#技术细节)

---

## 概述

### 什么是自动化测试脚本？

`tests/auto_test.py` 是一个完全自动化的测试框架，用于评估电梯调度算法在各种场景下的性能表现。它能够：

- **完全自动化**：无需任何手动操作，从服务器启动到结果生成全程自动
- **完全隔离**：每个测试在独立的服务器实例中运行，确保结果可靠
- **全面测试**：支持测试所有算法在所有场景下的表现
- **详细报告**：生成包含多种性能指标的详细测试报告

### 为什么需要自动化测试？

**传统手动测试的问题**：
- ❌ 需要手动启动服务器
- ❌ 需要手动切换数据集
- ❌ 测试之间可能相互影响
- ❌ 容易遗漏测试场景
- ❌ 结果难以对比和分析

**自动化测试的优势**：
- ✅ 一键运行所有测试
- ✅ 完全隔离，结果可靠
- ✅ 覆盖所有场景组合
- ✅ 自动生成对比报告
- ✅ 适合集成到 CI/CD 流程

### 适用场景

| 场景 | 是否适用 | 说明 |
|------|---------|------|
| 算法开发验证 | ✅ 强烈推荐 | 快速验证算法改进效果 |
| 回归测试 | ✅ 强烈推荐 | 确保新代码不影响现有功能 |
| 性能基准测试 | ✅ 强烈推荐 | 建立性能基准线 |
| 算法对比分析 | ✅ 强烈推荐 | 多算法横向对比 |
| 快速原型验证 | ⚠️ 可用 | 启动开销较大，可用快速模式 |
| 实时调试 | ❌ 不适用 | 使用手动测试工具更合适 |

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      AutoTester (主控制器)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  测试编排器 (Orchestrator)                            │   │
│  │  - 算法遍历                                           │   │
│  │  - 场景遍历                                           │   │
│  │  - 结果收集                                           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐              │
│  │ ServerManager    │    │ ScenarioManager  │              │
│  │ - 启动/停止      │    │ - 场景准备       │              │
│  │ - 健康检查       │    │ - 数据复制       │              │
│  │ - 端口管理       │    │ - 备份恢复       │              │
│  └──────────────────┘    └──────────────────┘              │
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐              │
│  │ MetricsParser    │    │ ReportGenerator  │              │
│  │ - 输出解析       │    │ - JSON 报告      │              │
│  │ - 指标提取       │    │ - Markdown 报告  │              │
│  └──────────────────┘    └──────────────────┘              │
└─────────────────────────────────────────────────────────────┘
         │                          │                    │
         ▼                          ▼                    ▼
┌─────────────────┐    ┌──────────────────┐    ┌──────────────┐
│ Elevator Server │    │ Test Scenarios   │    │ Test Results │
│ (elevator-py)   │    │ (data/*.json)    │    │ (JSON/MD)    │
└─────────────────┘    └──────────────────┘    └──────────────┘
```

### 组件交互流程

```
1. 用户执行命令
   ↓
2. AutoTester 初始化
   ├─> 加载算法列表
   ├─> 扫描测试场景
   └─> 创建 ServerManager
   ↓
3. 开始测试循环
   FOR 每个算法:
     FOR 每个场景:
       ├─> ScenarioManager 准备场景数据
       ├─> ServerManager 启动服务器
       ├─> 运行算法实例
       ├─> MetricsParser 解析结果
       ├─> ServerManager 停止服务器
       └─> 记录测试结果
   ↓
4. ReportGenerator 生成报告
   ├─> 保存 JSON 原始数据
   └─> 生成 Markdown 可读报告
   ↓
5. 显示测试摘要
```

---

## 核心组件

### 1. ServerManager 类

**职责**：管理 elevator simulator 服务器的完整生命周期

#### 核心方法

```python
class ServerManager:
    def __init__(self, port: int = 8000, startup_timeout: int = 60):
        """
        初始化服务器管理器

        Args:
            port: 服务器端口（默认8000）
            startup_timeout: 启动超时时间（秒，默认60）
        """

    def is_port_available(self) -> bool:
        """检查端口是否可用"""

    def wait_for_port_free(self, timeout: int = 30) -> bool:
        """等待端口释放（最长30秒）"""

    def start(self) -> bool:
        """
        启动服务器

        Returns:
            bool: 成功返回 True，失败返回 False

        流程:
            1. 检查端口可用性
            2. 启动服务器进程（非阻塞）
            3. 执行健康检查
            4. 返回启动结果
        """

    def wait_for_server(self) -> bool:
        """
        等待服务器就绪

        实现细节:
            - 连续发送 HTTP GET 请求
            - 需要 3 次连续成功响应（处理 Flask debug 模式重启）
            - 接受 200 或 404 状态码（服务器根路径返回404但仍正常）
            - 超时时间: startup_timeout 秒
        """

    def stop(self):
        """
        优雅停止服务器

        流程:
            1. 发送 SIGTERM 信号（优雅终止）
            2. 等待最多 10 秒
            3. 如果仍未停止，发送 SIGKILL（强制终止）
            4. 等待端口释放
            5. 冷却期 2 秒
        """
```

#### 关键设计决策

**为什么需要 3 次连续健康检查？**

Flask 在 debug 模式下会在检测到代码变化时自动重启。如果只检查一次，可能：
```
时刻 T0: 健康检查成功 ✓
时刻 T1: Flask 检测到变化，重启
时刻 T2: 算法开始运行 ✗ 连接失败！
```

连续 3 次成功确保服务器已稳定运行。

**为什么接受 404 状态码？**

Elevator simulator 的根路径 `/` 没有定义路由，返回 404，但这不代表服务器未启动：
```python
# 可接受的响应
if response.status_code in [200, 404]:  # 都表示服务器在运行
    consecutive_successes += 1
```

**为什么需要冷却期？**

进程终止后，操作系统需要时间释放资源（文件句柄、网络端口）：
```python
self.process.wait(timeout=10)  # 等待进程退出
self.wait_for_port_free()      # 等待端口释放
time.sleep(2)                  # 冷却期，确保资源完全释放
```

### 2. AutoTester 类

**职责**：测试编排和执行

#### 核心方法

```python
class AutoTester:
    def __init__(self, port: int = 8000):
        """初始化测试器"""

    def discover_algorithms(self) -> List[str]:
        """
        发现可用算法

        通过导入 algo 模块并读取 __all__ 变量获取算法列表
        """

    def discover_scenarios(self) -> List[Path]:
        """
        发现测试场景

        扫描 data/ 目录中的所有 .json 文件
        """

    def prepare_scenario(self, scenario_file: Path) -> bool:
        """
        准备测试场景

        流程:
            1. 备份原始 sample_traffic.json（如果存在）
            2. 复制场景文件到 traffic/sample_traffic.json
            3. 等待文件系统同步

        为什么这样做:
            - 服务器在启动时读取 traffic/sample_traffic.json
            - 必须在服务器启动前准备好场景数据
        """

    def run_algorithm(self, algorithm_name: str, scenario_name: str,
                     timeout: int = 300) -> Dict:
        """
        运行单个算法测试

        Args:
            algorithm_name: 算法类名（如 "OptimizedScanAlgorithm"）
            scenario_name: 场景名称（用于输出）
            timeout: 超时时间（秒，默认300）

        Returns:
            Dict: 包含性能指标的字典

        流程:
            1. 创建临时测试脚本
            2. 脚本内容:
               - 导入算法类
               - 创建算法实例（enable_logging=False）
               - 调用 algorithm.start()
            3. 执行脚本并捕获输出
            4. 解析性能指标
            5. 清理临时文件
        """

    def parse_metrics(self, output: str) -> Dict:
        """
        从算法输出中解析性能指标

        支持的指标:
            - avg_wait: 平均等待时间
            - p95_wait: P95 等待时间
            - avg_system: 平均系统时间
            - p95_system: P95 系统时间
            - served: 已服务乘客数
            - total: 总乘客数
            - completion_rate: 完成率
        """

    def run_test(self, algorithm: str, scenario_file: Path) -> Tuple[bool, Dict]:
        """
        运行单次测试（完整流程）

        流程:
            1. 准备场景
            2. 启动服务器
            3. 运行算法
            4. 解析结果
            5. 停止服务器（在 finally 块中，确保执行）
        """

    def run_all_tests(self, algorithms: List[str] = None,
                     scenarios: List[str] = None) -> Dict:
        """
        运行所有测试组合

        Args:
            algorithms: 要测试的算法列表（None = 所有）
            scenarios: 要测试的场景列表（None = 所有）

        Returns:
            Dict: 嵌套字典 {algorithm: {scenario: result}}
        """

    def generate_report(self, results: Dict, output_dir: Path):
        """
        生成测试报告

        输出:
            1. JSON 文件: test_results/auto_test_TIMESTAMP.json
            2. Markdown 文件: docs/auto_test_report_TIMESTAMP.md
        """
```

#### 测试脚本模板

自动化测试中，每个算法测试都会生成一个临时脚本：

```python
test_script = f"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from algo import {algorithm_name}

# 创建算法实例（关闭日志避免输出污染）
algorithm = {algorithm_name}(enable_logging=False)

# 启动算法
algorithm.start()
"""
```

**为什么需要 sys.path 操作？**

临时脚本从 `tests/` 目录执行，需要访问 `algo/` 模块：
```
project_root/
├── algo/              # 算法模块
│   └── __init__.py
└── tests/
    └── temp_test.py   # 临时脚本（这里执行）
```

不添加路径会导致 `ModuleNotFoundError: No module named 'algo'`。

### 3. MetricsParser 组件

**职责**：从算法输出中提取性能指标

#### 解析策略

算法输出格式示例：
```python
{
    'average_wait_time': 104.68,
    'p95_wait_time': 191.0,
    'average_system_time': 120.55,
    'p95_system_time': 194.0,
    'served_passengers': 74,
    'total_passengers': 74
}
```

解析流程：

```python
def parse_metrics(self, output: str) -> Dict:
    # 1. 使用正则表达式查找字典模式
    dict_pattern = r'\{[^}]*\'average_wait_time\'[^}]*\}'
    match = re.search(dict_pattern, output, re.DOTALL)

    if not match:
        return {}

    # 2. 使用 ast.literal_eval 安全解析
    try:
        result_dict = ast.literal_eval(match.group(0))
    except (SyntaxError, ValueError):
        return {}

    # 3. 提取并标准化指标
    metrics = {
        'avg_wait': result_dict.get('average_wait_time'),
        'p95_wait': result_dict.get('p95_wait_time'),
        'avg_system': result_dict.get('average_system_time'),
        'p95_system': result_dict.get('p95_system_time'),
        'served': result_dict.get('served_passengers'),
        'total': result_dict.get('total_passengers'),
    }

    # 4. 计算衍生指标
    if metrics['served'] and metrics['total']:
        metrics['completion_rate'] = (metrics['served'] / metrics['total']) * 100

    return metrics
```

**为什么使用 ast.literal_eval？**

- ✅ 安全：只解析字面值，不执行代码
- ✅ 准确：支持 Python 字典语法
- ❌ 不使用 `eval()`：存在代码注入风险
- ❌ 不使用 `json.loads()`：Python 字典用单引号，JSON 用双引号

### 4. ReportGenerator 组件

**职责**：生成人类可读和机器可读的测试报告

#### JSON 报告结构

```json
{
  "AlgorithmName": {
    "scenario_name": {
      "info": {
        "filename": "scenario.json",
        "name": "scenario_name",
        "description": "场景描述",
        "floors": 6,
        "elevators": 2,
        "capacity": 8,
        "duration": 200,
        "passengers": 160,
        "scenario_type": "morning_rush"
      },
      "metrics": {
        "avg_wait": 122.47,
        "p95_wait": 194.0,
        "avg_system": 122.47,
        "p95_system": 194.0,
        "served": 74,
        "total": 74,
        "completion_rate": 100.0
      },
      "success": true
    }
  }
}
```

#### Markdown 报告示例

```markdown
# 自动化测试报告
生成时间: 2025-10-03 20:33:55
---

## 测试概览

**测试算法**: OptimizedScanAlgorithm, RLDQNAlgorithm

**测试场景数**: 10

**测试方法**: 每个测试都在独立的服务器实例中运行，确保完全隔离

## 详细测试结果

| 算法 | 场景 | 规模 | 平均等待 | P95等待 | 平均系统时间 | 完成率 | 状态 |
|------|------|------|----------|---------|-------------|--------|----- |
| OptimizedScanAlgorithm | small_burst_traffic | 6层/2梯/73人 | 122.5 | 194.0 | 122.5 | 100.0% | ✅ |

## 算法性能统计

| 算法 | 成功率 | 平均等待时间 (均值) | P95等待时间 (均值) | 完成率 (均值) |
|------|--------|---------------------|--------------------|--------------|
| OptimizedScanAlgorithm | 100% | 122.47 | 194.00 | 100.0% |
```

---

## 使用指南

### 基础用法

#### 1. 测试所有算法和场景

```bash
uv run python tests/auto_test.py
```

**执行内容**：
- 测试 `algo/__all__` 中定义的所有算法
- 测试 `data/` 目录中的所有场景（共10个）

**预计时间**：20-40 分钟

**输出**：
- `test_results/auto_test_YYYYMMDD_HHMMSS.json`
- `docs/auto_test_report_YYYYMMDD_HHMMSS.md`

#### 2. 测试特定算法

```bash
# 单个算法
uv run python tests/auto_test.py --algorithms OptimizedScanAlgorithm

# 多个算法（逗号分隔，无空格）
uv run python tests/auto_test.py --algorithms OptimizedScanAlgorithm,RLDQNAlgorithm
```

#### 3. 测试特定场景

```bash
# 单个场景
uv run python tests/auto_test.py --scenarios small_morning_rush

# 多个场景
uv run python tests/auto_test.py --scenarios small_morning_rush,medium_inter_floor
```

#### 4. 组合筛选

```bash
uv run python tests/auto_test.py \
    --algorithms OptimizedScanAlgorithm \
    --scenarios small_morning_rush,small_evening_rush,small_burst_traffic
```

#### 5. 自定义输出目录

```bash
uv run python tests/auto_test.py --output-dir my_test_results
```

### 进阶用法

#### 快速验证测试（开发阶段）

只测试小型场景，快速验证算法改动：

```bash
uv run python tests/auto_test.py \
    --scenarios small_morning_rush,small_evening_rush,small_burst_traffic
```

**预计时间**：5-10 分钟

#### 大规模性能测试

只测试大型场景，评估算法极限性能：

```bash
uv run python tests/auto_test.py \
    --scenarios large_mixed_traffic,extreme_stress_test
```

#### 单算法完整验证

测试新开发的算法在所有场景下的表现：

```bash
uv run python tests/auto_test.py --algorithms MyNewAlgorithm
```

---

## 测试流程详解

### 完整测试流程图

```
开始测试
    │
    ├─> 读取命令行参数
    │   ├─ --algorithms (算法过滤)
    │   ├─ --scenarios (场景过滤)
    │   └─ --output-dir (输出目录)
    │
    ├─> 发现算法
    │   └─ 从 algo/__init__.py 的 __all__ 读取
    │
    ├─> 发现场景
    │   └─ 扫描 data/*.json
    │
    ├─> 应用过滤器
    │   └─ 根据参数筛选算法和场景
    │
    ├─> 开始测试循环
    │   │
    │   FOR 每个算法:
    │       │
    │       FOR 每个场景:
    │           │
    │           ├─> [1] 准备场景
    │           │   ├─ 备份 sample_traffic.json
    │           │   └─ 复制场景到 sample_traffic.json
    │           │
    │           ├─> [2] 检查端口
    │           │   └─ 如果占用，等待释放（最长30秒）
    │           │
    │           ├─> [3] 启动服务器
    │           │   ├─ 启动 uv run -m elevator server
    │           │   └─ 健康检查（最长60秒，需3次成功）
    │           │
    │           ├─> [4] 运行算法
    │           │   ├─ 创建临时测试脚本
    │           │   ├─ 执行脚本（超时300秒）
    │           │   ├─ 捕获 stdout/stderr
    │           │   └─ 删除临时脚本
    │           │
    │           ├─> [5] 解析结果
    │           │   ├─ 正则提取性能字典
    │           │   ├─ 解析各项指标
    │           │   └─ 计算完成率
    │           │
    │           ├─> [6] 停止服务器
    │           │   ├─ 发送 SIGTERM
    │           │   ├─ 等待退出（10秒）
    │           │   ├─ 必要时 SIGKILL
    │           │   └─ 等待端口释放 + 冷却2秒
    │           │
    │           └─> [7] 记录结果
    │               └─ 存储到结果字典
    │
    ├─> 生成报告
    │   ├─ 保存 JSON（原始数据）
    │   └─ 生成 Markdown（可读报告）
    │
    └─> 显示摘要
        ├─ 总测试数
        ├─ 成功/失败数
        └─ 总耗时
```

### 关键时间节点

| 阶段 | 典型耗时 | 说明 |
|------|---------|------|
| 服务器启动 | 10-30秒 | 取决于系统负载 |
| 健康检查 | 3-10秒 | 需3次连续成功 |
| 算法执行 | 10-300秒 | 取决于场景规模 |
| 服务器停止 | 2-5秒 | 包括端口释放和冷却 |
| 结果解析 | < 1秒 | 正则匹配很快 |
| 报告生成 | < 1秒 | 文件写入操作 |

### 测试隔离机制

#### 为什么需要完全隔离？

**问题场景**：共享服务器实例

```
测试1: OptimizedScan on Morning Rush
    服务器启动
    算法运行 ✓
    结果: 平均等待120秒

测试2: RLDQNAlgorithm on Morning Rush (同一服务器)
    算法运行
    结果: 平均等待80秒 ← 但这个结果可靠吗？
```

可能的问题：
- 服务器状态污染（电梯位置、队列残留）
- 内存泄漏累积
- 日志文件混淆
- 竞态条件

**解决方案**：每个测试独立服务器

```
测试1: OptimizedScan on Morning Rush
    服务器 A 启动
    算法运行 ✓
    服务器 A 停止 ✓

测试2: RLDQNAlgorithm on Morning Rush
    服务器 B 启动（全新实例）
    算法运行 ✓
    服务器 B 停止 ✓
```

#### 隔离机制实现

1. **进程隔离**：每次启动新的服务器进程
2. **数据隔离**：每次复制新的场景文件
3. **端口验证**：启动前确认端口完全释放
4. **冷却期**：停止后等待2秒，确保资源释放
5. **临时文件清理**：每次删除测试脚本

---

## 配置与定制

### 修改超时时间

编辑 `tests/auto_test.py`：

```python
class ServerManager:
    def __init__(self, port: int = 8000, startup_timeout: int = 60):
        # 修改 startup_timeout 增加服务器启动时间限制
        self.startup_timeout = 120  # 改为120秒

class AutoTester:
    def run_algorithm(self, algorithm_name: str, scenario_name: str,
                     timeout: int = 300):  # 修改 timeout 增加算法运行时间限制
```

### 修改端口

```python
# 初始化时指定端口
tester = AutoTester(port=8080)
```

### 添加自定义性能指标

在 `parse_metrics` 方法中添加：

```python
def parse_metrics(self, output: str) -> Dict:
    # 现有代码...

    metrics = {
        'avg_wait': result_dict.get('average_wait_time'),
        # ... 现有指标 ...

        # 添加新指标
        'max_wait': result_dict.get('max_wait_time'),
        'elevator_distance': result_dict.get('total_distance'),
    }

    return metrics
```

### 自定义报告格式

修改 `generate_report` 方法：

```python
def generate_report(self, results: Dict, output_dir: Path):
    # 现有 JSON 和 Markdown 生成...

    # 添加 HTML 报告
    html_report = self._generate_html_report(results)
    html_file = output_dir / f"auto_test_report_{timestamp}.html"
    html_file.write_text(html_report)

    # 添加 CSV 导出
    csv_file = output_dir / f"auto_test_results_{timestamp}.csv"
    self._export_to_csv(results, csv_file)
```

---

## 故障排查

### 常见错误及解决方案

#### 错误 1: 端口占用

**症状**：
```
⚠ Port 8000 is in use, waiting for it to be freed...
✗ Port 8000 is still in use after timeout
```

**原因**：
- 之前的服务器进程未正确终止
- 其他程序占用端口 8000

**解决方案**：

```bash
# 方案1: 查找并杀死占用进程
lsof -i :8000
kill -9 <PID>

# 方案2: 使用其他端口
uv run python tests/auto_test.py  # 修改脚本中的端口号

# 方案3: 等待一段时间后重试
# 端口可能处于 TIME_WAIT 状态，等待 1-2 分钟
```

#### 错误 2: 服务器启动超时

**症状**：
```
Starting simulator server on port 8000...
✗ Server failed to start within timeout
```

**可能原因**：
1. 系统资源不足
2. `elevator-py` 未正确安装
3. Python 环境问题
4. 防火墙阻止端口

**诊断步骤**：

```bash
# 1. 检查 elevator-py 安装
uv run python -c "import elevator; print(elevator.__version__)"

# 2. 手动启动服务器测试
uv run -m elevator server

# 3. 检查系统资源
top  # 查看 CPU/内存使用

# 4. 检查防火墙
# macOS
sudo pfctl -s rules | grep 8000

# Linux
sudo iptables -L | grep 8000
```

**解决方案**：

```python
# 增加启动超时时间
class ServerManager:
    def __init__(self, port: int = 8000, startup_timeout: int = 120):  # 增加到120秒
```

#### 错误 3: 测试超时

**症状**：
```
Running OptimizedScanAlgorithm... ✗ Timeout (300s exceeded)
```

**原因**：
- 场景规模过大
- 算法效率低
- 系统负载高

**解决方案**：

```python
# 增加测试超时时间
def run_algorithm(self, algorithm_name: str, scenario_name: str,
                 timeout: int = 600):  # 增加到600秒（10分钟）
```

**或者，先测试小场景**：

```bash
uv run python tests/auto_test.py --scenarios small_morning_rush
```

#### 错误 4: No metrics found

**症状**：
```
Running OptimizedScanAlgorithm... ✗ No metrics found in output
```

**原因**：
1. 算法执行出错
2. 输出格式不符合预期
3. 场景数据损坏
4. 算法未正确输出结果

**调试步骤**：

```bash
# 1. 手动运行算法查看输出
uv run python -c "
from algo import OptimizedScanAlgorithm
algorithm = OptimizedScanAlgorithm(enable_logging=True)
algorithm.start()
"

# 2. 检查场景文件
cat data/small_morning_rush.json | python -m json.tool

# 3. 启用调试模式
# 编辑 auto_test.py，临时添加：
print(f"Algorithm output: {output}")
print(f"Stderr: {stderr}")
```

#### 错误 5: ModuleNotFoundError

**症状**：
```
ModuleNotFoundError: No module named 'algo'
```

**原因**：
- Python 路径问题
- 项目结构变化

**解决方案**：

确保测试脚本模板包含路径设置：

```python
test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from algo import {algorithm_name}
# ...
"""
```

#### 错误 6: 权限错误

**症状**：
```
PermissionError: [Errno 13] Permission denied: 'traffic/sample_traffic.json'
```

**原因**：
- 文件权限问题
- 文件被其他进程锁定

**解决方案**：

```bash
# 检查文件权限
ls -la traffic/

# 修复权限
chmod 644 traffic/sample_traffic.json

# 检查是否有进程占用文件
lsof traffic/sample_traffic.json
```

### 调试技巧

#### 启用详细日志

修改算法调用：

```python
algorithm = {algorithm_name}(enable_logging=True)  # 启用日志
```

#### 查看服务器输出

修改 `ServerManager.start()`：

```python
# 不重定向 stdout/stderr
self.process = subprocess.Popen(
    ["uv", "run", "-m", "elevator", "server", f"--port={self.port}"],
    # 移除 stdout/stderr 重定向，直接输出到终端
)
```

#### 保留临时脚本

修改 `run_algorithm()`：

```python
finally:
    # 注释掉删除操作，保留脚本供调试
    # test_script_path.unlink()
    pass
```

---

## 性能优化

### 测试速度优化

#### 1. 选择性测试

**场景**：只测试修改过的算法

```bash
uv run python tests/auto_test.py --algorithms MyModifiedAlgorithm
```

**场景**：跳过大型场景

```bash
# 只测试 small 和 medium 场景
uv run python tests/auto_test.py \
    --scenarios small_morning_rush,small_evening_rush,medium_inter_floor
```

#### 2. 调整超时时间

如果确信算法会快速完成：

```python
def run_algorithm(self, algorithm_name: str, scenario_name: str,
                 timeout: int = 120):  # 降低到120秒
```

#### 3. 减少健康检查次数

如果服务器启动稳定：

```python
def wait_for_server(self) -> bool:
    required_successes = 1  # 从3改为1
```

⚠️ **注意**：可能导致 Flask debug 模式下的不稳定

### 系统资源优化

#### 1. 关闭不必要的服务

测试期间关闭其他占用 CPU/内存的程序。

#### 2. 使用 SSD

将项目放在 SSD 上，提高文件 I/O 速度。

#### 3. 增加系统资源

- 增加 Python 进程内存限制
- 提高 CPU 优先级（仅在必要时）

```bash
# macOS/Linux: 提高优先级
nice -n -10 uv run python tests/auto_test.py
```

### 未来优化方向

#### 1. 并行测试

**当前**：串行执行（算法1场景1 → 算法1场景2 → ...）

**优化**：并行执行（多个服务器实例，不同端口）

```python
# 伪代码
from concurrent.futures import ProcessPoolExecutor

def run_test_parallel(algorithms, scenarios):
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = []
        base_port = 8000

        for i, (algo, scenario) in enumerate(product(algorithms, scenarios)):
            port = base_port + i
            future = executor.submit(run_single_test, algo, scenario, port)
            futures.append(future)

        results = [f.result() for f in futures]
    return results
```

**预期提升**：4核并行可提速 3-4 倍

#### 2. 测试缓存

**策略**：如果算法和场景未变化，复用之前的结果

```python
def run_test_cached(self, algorithm: str, scenario: Path):
    cache_key = f"{algorithm}_{scenario.stem}_{self._get_code_hash(algorithm)}"

    if cache_key in self.cache:
        return self.cache[cache_key]

    result = self.run_test(algorithm, scenario)
    self.cache[cache_key] = result
    return result
```

#### 3. 增量测试

**策略**：只测试代码变化影响的部分

```bash
# 检测 git 变化
git diff --name-only | grep algo/optimized_scan.py

# 只测试 OptimizedScanAlgorithm
uv run python tests/auto_test.py --algorithms OptimizedScanAlgorithm
```

---

## 最佳实践

### 开发工作流

#### 日常开发

```bash
# 1. 修改算法代码
vim algo/my_algorithm.py

# 2. 快速验证（只测试一个小场景）
uv run python tests/auto_test.py \
    --algorithms MyAlgorithm \
    --scenarios small_morning_rush

# 3. 查看结果
cat docs/auto_test_report_*.md | tail -20

# 4. 如果通过，测试更多场景
uv run python tests/auto_test.py --algorithms MyAlgorithm
```

#### 提交前检查

```bash
# 1. 运行完整测试
uv run python tests/auto_test.py

# 2. 检查所有测试通过
grep "✅" docs/auto_test_report_*.md

# 3. 对比性能是否退化
# 查看之前的报告并对比

# 4. 提交代码
git add .
git commit -m "feat: improve elevator scheduling algorithm"
```

### CI/CD 集成

#### GitHub Actions 示例

```yaml
name: Automated Testing

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Install uv
      run: curl -LsSf https://astral.sh/uv/install.sh | sh

    - name: Setup Python
      run: uv venv && source .venv/bin/activate

    - name: Install dependencies
      run: uv sync

    - name: Run automated tests
      run: uv run python tests/auto_test.py
      timeout-minutes: 60

    - name: Upload test results
      uses: actions/upload-artifact@v3
      with:
        name: test-results
        path: |
          test_results/*.json
          docs/auto_test_report_*.md

    - name: Check test success
      run: |
        if grep -q "✗" docs/auto_test_report_*.md; then
          echo "Some tests failed!"
          exit 1
        fi
```

#### GitLab CI 示例

```yaml
test:
  stage: test
  script:
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - uv sync
    - uv run python tests/auto_test.py
  artifacts:
    paths:
      - test_results/
      - docs/auto_test_report_*.md
    expire_in: 1 week
  timeout: 1h
```

### 性能基准管理

#### 建立基准

```bash
# 1. 在稳定版本上运行完整测试
git checkout v1.0.0
uv run python tests/auto_test.py

# 2. 保存基准报告
cp docs/auto_test_report_*.md docs/baseline_v1.0.0.md
cp test_results/auto_test_*.json test_results/baseline_v1.0.0.json
```

#### 性能回归检测

```bash
# 1. 在新版本上测试
git checkout develop
uv run python tests/auto_test.py

# 2. 对比结果
python scripts/compare_results.py \
    test_results/baseline_v1.0.0.json \
    test_results/auto_test_20251003_203355.json

# 3. 检查是否有性能退化
# 如果平均等待时间增加 > 10%，则需要重新审视代码
```

### 测试策略

#### 金字塔测试策略

```
        /\
       /  \      单元测试 (Unit Tests)
      /____\     - 测试单个函数
     /      \    - 快速、频繁
    /        \
   /__________\  集成测试 (Integration Tests)
  /            \ - 测试模块交互
 /              \- 中等速度
/________________\
                   端到端测试 (E2E Tests) ← auto_test.py 在这里
                   - 测试完整流程
                   - 较慢、提交前运行
```

**推荐频率**：

- **单元测试**：每次代码保存后运行（秒级）
- **集成测试**：每次提交前运行（分钟级）
- **端到端测试**：每次 PR/发布前运行（小时级）

---

## 技术细节

### 为什么选择这些技术？

#### subprocess vs threading vs multiprocessing

**选择 subprocess**：
- ✅ 完全进程隔离
- ✅ 可以运行外部命令（uv run）
- ✅ 易于管理生命周期（SIGTERM/SIGKILL）

**不选 threading**：
- ❌ 共享内存空间，无法完全隔离
- ❌ GIL 限制，无法真正并行

**不选 multiprocessing**：
- ❌ 无法直接运行外部命令
- ⚠️ 可以考虑用于未来的并行优化

#### 健康检查策略

**为什么用 HTTP 请求？**
- ✅ 标准协议，通用性强
- ✅ 可以确认服务器真正就绪（不只是进程启动）
- ✅ 易于调试（可以用 curl 手动测试）

**为什么不用端口检测？**
- ❌ 端口打开 ≠ 服务器就绪
- ❌ 可能出现端口已开但服务器还在初始化

**为什么不用 WebSocket？**
- ❌ 过于复杂，HTTP 足够
- ❌ 需要额外依赖

#### 指标解析方法

**为什么用正则表达式？**
- ✅ 灵活，适应多种输出格式
- ✅ 不需要修改算法代码
- ✅ 容错性好（部分匹配）

**为什么不用结构化日志？**
- ❌ 需要修改所有算法
- ❌ 增加算法复杂度

**为什么不用文件输出？**
- ❌ 需要管理文件生命周期
- ❌ 可能产生大量临时文件

### 关键设计模式

#### 1. Template Method Pattern

```python
class AutoTester:
    def run_test(self, algorithm, scenario):
        # 模板方法，定义测试流程
        self.prepare_scenario(scenario)      # 步骤1
        self.server_manager.start()          # 步骤2
        metrics = self.run_algorithm(...)    # 步骤3
        self.server_manager.stop()           # 步骤4
        return metrics

    # 子类可以重写这些方法
    def prepare_scenario(self, scenario): ...
    def run_algorithm(self, ...): ...
```

#### 2. Context Manager Pattern

```python
class ServerManager:
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

# 使用
with ServerManager() as server:
    # 运行测试
    # 自动清理
```

#### 3. Strategy Pattern

```python
class MetricsParser:
    def __init__(self, strategy: str = 'regex'):
        self.strategies = {
            'regex': self._parse_with_regex,
            'json': self._parse_with_json,
            'xml': self._parse_with_xml,
        }
        self.parse = self.strategies[strategy]
```

### 性能分析

#### 时间复杂度

- **发现算法**: O(1) - 读取 `__all__` 变量
- **发现场景**: O(n) - 扫描目录，n = 文件数
- **单次测试**: O(1) - 固定流程
- **所有测试**: O(a × s) - a = 算法数，s = 场景数
- **报告生成**: O(a × s) - 遍历所有结果

#### 空间复杂度

- **结果存储**: O(a × s) - 每个测试一个结果字典
- **服务器进程**: O(1) - 同时只有一个服务器
- **临时文件**: O(1) - 只有一个临时测试脚本

### 错误处理哲学

**原则**：Fail Fast + Graceful Degradation

```python
def run_test(self, algorithm, scenario):
    try:
        # 尝试运行测试
        self.prepare_scenario(scenario)
        self.server_manager.start()

        if not self.server_manager.is_ready():
            # Fail Fast: 服务器未就绪，立即失败
            return False, {'error': 'Server not ready'}

        metrics = self.run_algorithm(...)
        return True, metrics

    except Exception as e:
        # Graceful Degradation: 记录错误，继续测试其他场景
        logger.error(f"Test failed: {e}")
        return False, {'error': str(e)}

    finally:
        # 确保清理: 无论成功或失败都停止服务器
        self.server_manager.stop()
```

---

## 附录

### A. 完整命令行参数

```bash
uv run python tests/auto_test.py [OPTIONS]

OPTIONS:
  --algorithms ALGO1,ALGO2   要测试的算法列表（逗号分隔）
  --scenarios SCENE1,SCENE2  要测试的场景列表（逗号分隔）
  --output-dir PATH          输出目录（默认: test_results/）
  --port PORT                服务器端口（默认: 8000）
  --timeout SECONDS          单个测试超时时间（默认: 300）
  --startup-timeout SECONDS  服务器启动超时（默认: 60）
  --help                     显示帮助信息
```

### B. 测试场景列表

| 场景名 | 描述 | 楼层 | 电梯 | 乘客 | 类型 |
|--------|------|------|------|------|------|
| small_morning_rush | 小型建筑上班高峰 | 6 | 2 | 160 | morning_rush |
| small_evening_rush | 小型建筑下班高峰 | 6 | 2 | 150 | evening_rush |
| small_burst_traffic | 小型建筑突发流量 | 6 | 2 | 73 | burst_traffic |
| medium_inter_floor | 中型建筑楼层间流动 | 12 | 3 | 300 | inter_floor |
| medium_lunch_rush | 中型建筑午餐高峰 | 12 | 3 | 250 | lunch_rush |
| large_morning_rush | 大型建筑上班高峰 | 20 | 5 | 800 | morning_rush |
| large_evening_rush | 大型建筑下班高峰 | 20 | 5 | 750 | evening_rush |
| large_mixed_traffic | 大型建筑混合流量 | 20 | 5 | 600 | mixed |
| very_large_complex | 超大型建筑复杂场景 | 25 | 6 | 1000 | complex |
| extreme_stress_test | 极限压力测试 | 25 | 6 | 1500 | stress_test |

### C. 性能指标说明

| 指标 | 说明 | 单位 | 目标 |
|------|------|------|------|
| avg_wait | 平均等待时间 | 秒 | 越低越好 |
| p95_wait | 95分位等待时间 | 秒 | 越低越好 |
| avg_system | 平均系统时间 | 秒 | 越低越好 |
| p95_system | 95分位系统时间 | 秒 | 越低越好 |
| served | 已服务乘客数 | 人 | - |
| total | 总乘客数 | 人 | - |
| completion_rate | 完成率 | % | 100% |

**等待时间 vs 系统时间**：
- **等待时间**：乘客从请求到进入电梯的时间
- **系统时间**：乘客从请求到到达目的地的总时间

### D. 与其他测试工具对比

| 特性 | auto_test.py | compare_algorithms.py | manual_comparison.py | run_tests.py |
|------|-------------|----------------------|---------------------|-------------|
| 自动化程度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 测试隔离 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 速度 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 报告质量 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 易用性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| CI/CD 适用 | ✅ | ⚠️ | ❌ | ⚠️ |

**推荐使用场景**：
- **auto_test.py**: 提交前完整测试、CI/CD、性能基准
- **compare_algorithms.py**: 快速对比两个算法
- **manual_comparison.py**: 交互式验证、调试
- **run_tests.py**: 批量测试单个算法

### E. 常见问题快速索引

| 问题 | 章节 |
|------|------|
| 端口被占用 | [故障排查 - 错误1](#错误-1-端口占用) |
| 服务器启动超时 | [故障排查 - 错误2](#错误-2-服务器启动超时) |
| 测试超时 | [故障排查 - 错误3](#错误-3-测试超时) |
| 找不到性能指标 | [故障排查 - 错误4](#错误-4-no-metrics-found) |
| 模块导入错误 | [故障排查 - 错误5](#错误-5-modulenotfounderror) |
| 如何加速测试 | [性能优化](#性能优化) |
| 如何集成 CI/CD | [最佳实践 - CI/CD集成](#cicd-集成) |
| 如何添加自定义指标 | [配置与定制 - 添加自定义性能指标](#添加自定义性能指标) |

---

**文档版本**: 1.0
**最后更新**: 2025-10-03
**维护者**: Elevator Scheduling Project Team

如有问题或建议，请提交 Issue 或 Pull Request。
