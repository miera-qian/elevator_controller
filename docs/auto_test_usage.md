# 自动化测试脚本使用指南

## 概述

`tests/auto_test.py` 是一个完全自动化的测试脚本，能够：

- ✅ 自动启动和停止 elevator simulator 服务器
- ✅ 为每个测试提供完全隔离的环境（独立服务器实例）
- ✅ 测试所有算法在所有数据集上的性能
- ✅ 生成详细的测试报告

## 核心特性

### 完全自动化
- 无需手动启动服务器
- 无需手动切换数据集
- 无需手动清理进程

### 完全隔离
- 每个测试在独立的服务器实例中运行
- 数据集切换时重启服务器
- 算法切换时重启服务器
- 确保测试之间无相互影响

### 可靠性
- 自动端口检测和等待
- 服务器健康检查
- 超时保护
- 进程清理保证

## 使用方法

### 1. 测试所有算法和所有场景（推荐）

```bash
uv run python tests/auto_test.py
```

这将测试：
- 所有在 `algo/__all__` 中定义的算法
- 所有在 `data/` 目录中的测试场景（共10个）

**预计时间**: 约 20-40 分钟（取决于场景复杂度）

### 2. 测试特定算法

```bash
uv run python tests/auto_test.py --algorithms OptimizedScanAlgorithm
```

或测试多个算法：

```bash
uv run python tests/auto_test.py --algorithms OptimizedScanAlgorithm,RLDQNAlgorithm
```

### 3. 测试特定场景

```bash
uv run python tests/auto_test.py --scenarios small_morning_rush,medium_inter_floor
```

### 4. 组合使用

```bash
uv run python tests/auto_test.py \
    --algorithms OptimizedScanAlgorithm \
    --scenarios small_morning_rush,small_evening_rush,small_burst_traffic
```

### 5. 自定义输出目录

```bash
uv run python tests/auto_test.py --output-dir my_test_results
```

## 输出内容

### 实时控制台输出

测试过程中会显示：

```
======================================================================
Automated Testing
======================================================================
Algorithms: OptimizedScanAlgorithm, RLDQNAlgorithm
Scenarios: 10
Total tests: 20
======================================================================

======================================================================
Testing Algorithm: OptimizedScanAlgorithm
======================================================================

[1/20] OptimizedScanAlgorithm on small_morning_rush

  Scenario: small_morning_rush
    小型建筑上班高峰 - 6层楼，2部电梯
    6 floors, 2 elevators, 160 passengers
Starting simulator server on port 8000...
  ✓ Server is ready
    Running OptimizedScanAlgorithm... ✓ Avg=175.5, P95=198.0
  Stopping server...
  ✓ Server stopped

...
```

### 生成的文件

#### 1. JSON 原始数据

**位置**: `test_results/auto_test_TIMESTAMP.json`

**格式**:
```json
{
  "OptimizedScanAlgorithm": {
    "small_morning_rush": {
      "info": {
        "name": "small_morning_rush",
        "description": "...",
        "floors": 6,
        "elevators": 2,
        "passengers": 160
      },
      "metrics": {
        "avg_wait": 175.5,
        "p95_wait": 198.0,
        "avg_system": 180.2,
        "served": 160,
        "total": 160,
        "completion_rate": 100.0
      },
      "success": true
    }
  }
}
```

#### 2. Markdown 测试报告

**位置**: `docs/auto_test_report_TIMESTAMP.md`

**内容包括**:
- 测试概览
- 详细测试结果表格
- 算法性能统计
- 成功率分析

## 测试流程说明

### 单次测试的完整流程

对于每个 (算法, 场景) 组合：

1. **启动服务器**
   - 检查端口是否可用
   - 启动 simulator 进程
   - 等待服务器就绪（HTTP 健康检查）

2. **准备场景**
   - 复制场景文件到 `traffic/test_scenario.json`
   - 等待文件系统同步

3. **运行算法**
   - 创建临时测试脚本
   - 执行算法
   - 捕获输出
   - 解析性能指标

4. **清理**
   - 删除临时脚本
   - 终止服务器进程
   - 等待端口释放
   - 短暂冷却期

5. **记录结果**
   - 保存性能指标
   - 标记成功/失败状态

### 隔离保证

每次测试都：
- ✅ 使用全新的服务器实例
- ✅ 独立的场景数据
- ✅ 独立的算法实例
- ✅ 完全的进程清理

## 故障排查

### 问题：端口被占用

**症状**:
```
⚠ Port 8000 is in use, waiting for it to be freed...
✗ Port 8000 is still in use after timeout
```

**解决**:
```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或等待一段时间后重试
```

### 问题：服务器启动超时

**症状**:
```
✗ Server failed to start within timeout
```

**解决**:
- 检查是否有其他服务占用端口
- 检查 `elevator-py` 是否正确安装
- 增加启动超时时间（修改脚本中的 `startup_timeout`）

### 问题：测试超时

**症状**:
```
Running OptimizedScanAlgorithm... ✗ Timeout
```

**解决**:
- 某些大型场景可能需要更长时间
- 修改脚本中的 `timeout` 参数（默认300秒）

### 问题：No metrics found

**症状**:
```
Running OptimizedScanAlgorithm... ✗ No metrics found in output
```

**可能原因**:
- 算法执行出错
- 输出格式不符合预期
- 场景数据有问题

**调试**:
```bash
# 手动运行单个测试
uv run python -c "
from algo import OptimizedScanAlgorithm
algorithm = OptimizedScanAlgorithm(enable_logging=True)
algorithm.start()
"
```

## 性能优化建议

### 快速测试（开发阶段）

只测试小型场景：

```bash
uv run python tests/auto_test.py \
    --scenarios small_morning_rush,small_evening_rush,small_burst_traffic
```

预计时间：~5-10 分钟

### 完整测试（发布前）

测试所有场景：

```bash
uv run python tests/auto_test.py
```

预计时间：~20-40 分钟

### 并行测试（未来优化）

当前版本串行执行以确保隔离性。未来可以考虑：
- 使用不同端口并行运行多个服务器
- 算法级别的并行（同时测试不同算法）

## 与其他测试工具对比

### auto_test.py vs compare_algorithms.py

| 特性 | auto_test.py | compare_algorithms.py |
|------|-------------|----------------------|
| 服务器管理 | ✅ 自动 | ❌ 需手动启动 |
| 测试隔离 | ✅ 完全隔离（重启） | ⚠️ 共享服务器 |
| 适用场景 | 完整测试、CI/CD | 快速对比 |
| 可靠性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 速度 | 较慢（启动开销） | 较快 |

### auto_test.py vs manual_comparison.py

| 特性 | auto_test.py | manual_comparison.py |
|------|-------------|---------------------|
| 自动化程度 | ✅ 完全自动 | ⚠️ 需手动操作 |
| 适用场景 | 自动化测试 | 交互式验证 |
| 用户介入 | 无需 | 每个场景都需要 |

## 推荐工作流

### 开发阶段

1. 修改算法代码
2. 快速测试：
   ```bash
   uv run python tests/auto_test.py --scenarios small_morning_rush
   ```
3. 检查结果，继续迭代

### 提交前验证

1. 完整测试：
   ```bash
   uv run python tests/auto_test.py
   ```
2. 检查测试报告
3. 确认所有测试通过
4. 提交代码

### CI/CD 集成

```yaml
# .github/workflows/test.yml 示例
- name: Run automated tests
  run: |
    uv sync
    uv run python tests/auto_test.py
```

## 高级用法

### 自定义测试脚本

基于 `auto_test.py` 的结构，你可以：

1. **添加新的性能指标**
   - 修改 `parse_metrics()` 方法
   - 提取额外的性能数据

2. **自定义报告格式**
   - 修改 `generate_report()` 方法
   - 添加图表、可视化等

3. **集成通知系统**
   - 测试完成后发送邮件/Slack通知
   - 失败时自动报警

### 扩展性

脚本设计为易于扩展：

```python
class AutoTester:
    # 可以继承并重写方法
    def custom_metric_parser(self, output):
        # 自定义指标解析
        pass

    def custom_report_generator(self):
        # 自定义报告生成
        pass
```

## 常见问题 (FAQ)

### Q: 测试可以中断吗？

A: 可以。按 `Ctrl+C` 中断测试，脚本会自动清理服务器进程。

### Q: 测试失败后可以重试吗？

A: 可以。使用 `--scenarios` 参数只重新测试失败的场景。

### Q: 如何查看详细日志？

A: 修改算法调用时的 `enable_logging=True`，或查看服务器的 stdout/stderr。

### Q: 可以在远程服务器上运行吗？

A: 可以，但需要确保：
- 端口8000未被占用
- 有足够的系统资源
- Python 和 uv 已正确安装

---

*更新日期: 2025-10-03*
