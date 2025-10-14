# WebUI真实算法集成 - 快速开始

## 🎯 快速启动

### 使用启动脚本 (推荐)

```bash
./start_webui.sh
```

然后选择模式:
- 选择 `1` → Mock模式 (快速演示)
- 选择 `2` → Real模式 (真实算法)

### 手动启动

**Mock模式**:
```bash
# 1. 确保配置为Mock模式
# 编辑 webui/app.py,设置: USE_REAL_SIMULATION = False

# 2. 启动WebUI
cd webui
python app.py

# 3. 访问
open http://localhost:8080
```

**Real模式**:
```bash
# 1. 确保配置为Real模式
# 编辑 webui/app.py,设置: USE_REAL_SIMULATION = True

# 2. 确保端口18000未被占用
lsof -i :18000  # 应该无输出

# 3. 启动WebUI
cd webui
python app.py

# 4. 访问
open http://localhost:8080
```

## 📊 模式对比

| 特性 | Mock模式 | Real模式 |
|------|---------|---------|
| 🚀 启动速度 | 快 (< 0.1秒) | 较慢 (1-2秒) |
| 💻 资源占用 | 低 | 中等 |
| 🎯 准确性 | 仅供演示 | 真实算法性能 |
| ✅ 适用场景 | UI开发、快速演示 | 算法测试、性能评估 |
| 🔧 依赖 | FastAPI, Uvicorn | + requests |

## 🎮 使用步骤

1. **启动WebUI**
   - Mock模式: `./start_webui.sh` → 选择 `1`
   - Real模式: `./start_webui.sh` → 选择 `2`

2. **访问界面**
   - 浏览器打开: http://localhost:8080

3. **选择配置**
   - 算法: 选择调度算法 (推荐: Hybrid SCAN-RL)
   - 场景: 选择测试场景 (推荐: small_morning_rush)
   - 速度: 调整模拟速度 (1x - 10x)

4. **开始模拟**
   - 点击 "Start Simulation" 按钮
   - 观察电梯运行和乘客流动
   - 查看实时统计数据

5. **控制模拟**
   - ⏸️ Pause: 暂停模拟
   - ▶️ Resume: 继续模拟
   - ⏹️ Stop: 停止模拟
   - 🎚️ Speed: 调整速度

## 🧪 测试建议

### 新手测试 (Mock模式)

1. **小规模场景**:
   ```
   算法: HybridScanRLAlgorithm
   场景: small_morning_rush (6层,2电梯,160人)
   速度: 2x
   ```

2. **观察要点**:
   - 电梯如何响应呼叫
   - 乘客等待时间分布
   - 电梯利用率

### 高级测试 (Real模式)

1. **性能对比**:
   ```
   # 测试1: SCAN算法
   算法: ScanController
   场景: medium_lunch_rush

   # 测试2: 混合算法
   算法: HybridScanRLAlgorithm
   场景: medium_lunch_rush

   # 对比平均等待时间和P95等待时间
   ```

2. **压力测试**:
   ```
   算法: OptimizedScanAlgorithm
   场景: xlarge_stress_test (12层,4电梯,200人)
   速度: 5x
   ```

## 📁 项目结构

```
elevator_controller/
├── webui/
│   ├── app.py                    # FastAPI主应用 ⚙️
│   ├── mock_simulation.py        # Mock模拟引擎 🎭
│   ├── real_simulation.py        # Real模拟引擎 ⚡
│   └── static/
│       └── index.html            # 前端界面 🎨
├── algo/
│   ├── base_algorithm.py         # 算法基类
│   ├── optimized_scan.py         # SCAN算法
│   ├── rl_dqn.py                 # RL算法
│   └── hybrid_scan_rl.py         # 混合算法
├── data/                          # 场景数据 📊
│   ├── small_morning_rush.json
│   ├── medium_lunch_rush.json
│   └── xlarge_stress_test.json
├── simulator.py                   # 模拟器服务器 🏗️
├── start_webui.sh                # 启动脚本 🚀
└── docs/
    ├── webui_usage_guide.md      # 详细使用指南 📖
    └── webui_implementation_summary.md  # 实现总结
```

## 🐛 常见问题

### Q1: Real模式启动失败?

**A**: 检查端口18000是否被占用:
```bash
lsof -i :18000
# 如果被占用,杀掉进程:
kill -9 <PID>
```

### Q2: 没有看到电梯移动?

**A**: 可能原因:
- 场景还未开始 (等待first tick)
- 模拟速度太快 (降低速度)
- 浏览器WebSocket断开 (刷新页面)

### Q3: Real模式性能慢?

**A**:
- 降低模拟速度
- 选择小规模场景
- 关闭浏览器开发者工具

### Q4: 如何添加新场景?

**A**:
1. 在 `data/` 目录创建JSON文件
2. 参考 `small_morning_rush.json` 格式
3. 刷新页面,新场景会自动出现

## 📚 更多文档

- **详细使用指南**: [docs/webui_usage_guide.md](docs/webui_usage_guide.md)
- **实现总结**: [docs/webui_implementation_summary.md](docs/webui_implementation_summary.md)
- **API参考**: [docs/simulator_api_reference.md](docs/simulator_api_reference.md)
- **作业说明**: [电梯调度编程任务说明.pdf](电梯调度编程任务说明.pdf)

## 🎓 学习路径

### 第1阶段: 熟悉系统
1. ✅ 使用Mock模式快速体验
2. ✅ 尝试不同算法和场景
3. ✅ 理解评价指标 (等待时间、完成率等)

### 第2阶段: 开发算法
1. ✅ 阅读现有算法代码
2. ✅ 实现自己的算法
3. ✅ 使用Real模式测试

### 第3阶段: 优化性能
1. ✅ 对比不同算法性能
2. ✅ 分析瓶颈和改进点
3. ✅ 在各种场景下测试

## 🚀 开始使用

```bash
# 克隆或进入项目目录
cd elevator_controller

# 安装依赖 (如果还没安装)
pip install fastapi uvicorn websockets requests

# 启动WebUI
./start_webui.sh

# 选择模式后访问
# http://localhost:8080
```

祝你使用愉快! 🎉
