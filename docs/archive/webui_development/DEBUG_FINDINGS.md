# WebUI Debug Findings and Solutions

## 问题诊断

### 发现的问题

1. **Canvas渲染正常** ✅
   - Canvas成功显示楼层（F1-F15）
   - 4部电梯在初始化时正确显示
   - 渲染引擎工作正常

2. **WebSocket连接正常** ✅
   - WebSocket成功连接
   - Init消息正确发送
   - 前端正确接收并处理init消息

3. **Simulation引擎存在架构问题** ❌
   - 电梯服务器启动命令错误：使用了`uv run -m elevator server`，但正确命令是`uv run python -m elevator_saga.server.simulator`
   - elevator_saga服务器预加载了自己的traffic数据，不支持动态POST自定义场景
   - 没有`/state` API端点用于查询当前状态

### 根本原因

**elevator_saga包的工作模式**：
1. Server先启动并加载默认traffic数据
2. Algorithm通过WebSocket连接到server
3. Algorithm继承`ElevatorController`基类，`start()`方法会自动连接
4. Server不提供HTTP API查询状态，只通过WebSocket通信

**当前WebUI设计的问题**：
- 试图自己启动服务器并动态加载场景 → 不可行
- 试图通过HTTP轮询`/state`获取状态 → API不存在
- Simulation引擎与elevator_saga的设计范式不匹配

## 建议的解决方案

### 方案A：简化WebUI（推荐）⭐

**思路**：WebUI只显示预定义的演示动画，不运行真实算法

**实现**：
1. 在前端JavaScript中创建模拟数据生成器
2. 生成假的电梯移动、乘客上下等事件
3. 用户选择算法/场景后，播放预设的动画序列
4. 保留所有UI元素和控制功能

**优点**：
- 实现简单，无需后端复杂度
- 可以展示所有视觉效果
- 用户体验流畅

**缺点**：
- 不是真实的算法运行
- 只能用于演示目的

**实现步骤**：
```javascript
// 在 simulation.js 中
class MockSimulationEngine {
    start() {
        // 生成假数据并通过WebSocket发送
        setInterval(() => {
            const fakeState = this.generateFakeState();
            this.websocket.send_json(fakeState);
        }, 100);
    }

    generateFakeState() {
        // 随机移动电梯
        // 随机生成/移除乘客
        return {...};
    }
}
```

### 方案B：集成elevator_saga内部API

**思路**：不通过HTTP服务器，直接使用elevator_saga的Python API

**实现**：
1. 从elevator_saga导入Simulation类
2. 在WebUI后端直接创建模拟实例
3. 在内存中运行模拟并提取状态
4. 通过WebSocket广播状态

**优点**：
- 运行真实算法
- 完全控制模拟过程
- 可以动态加载场景

**缺点**：
- 需要深入理解elevator_saga内部API
- 可能需要修改源代码
- 复杂度高

### 方案C：使用elevator_saga CLI + SSE

**思路**：运行elevator-saga CLI工具，捕获输出并转换为WebUI更新

**实现**：
1. 使用subprocess运行`elevator-saga run`
2. 解析CLI输出的实时日志
3. 转换为WebUI状态更新

**优点**：
- 使用官方CLI
- 不需要修改elevator_saga

**缺点**：
- 需要解析文本输出
- 实时性较差
- 控制有限

## 当前代码状态

### 已修复
- ✅ renderer.js 初始化逻辑
- ✅ Canvas显示楼层和电梯
- ✅ WebSocket连接和消息处理
- ✅ UI控制面板

### 需要重构
- ❌ webui/simulation.py - 整个文件需要重写
- ❌ webui/app.py WebSocket处理 - 需要适配新方案

### 可以保留
- ✅ webui/static/index.html
- ✅ webui/static/css/style.css
- ✅ webui/static/js/renderer.js
- ✅ webui/static/js/websocket.js
- ✅ webui/static/js/app.js

## 推荐实施计划

**Phase 1: 快速演示版（方案A）**
1. 创建`webui/mock_simulation.py`
2. 生成假数据序列
3. 通过WebSocket推送
4. 用户可以立即看到电梯移动

**Phase 2: 真实集成版（方案B）**
1. 研究elevator_saga内部API
2. 直接创建Simulation实例
3. 提取真实状态数据
4. 支持所有算法和场景

## 测试记录

### Playwright测试结果
- ✅ 页面加载成功
- ✅ Canvas渲染楼层
- ✅ 电梯显示在底层
- ✅ UI控件响应正常
- ✅ WebSocket连接成功
- ❌ 没有状态更新（simulation引擎问题）

### 服务器测试
```bash
# elevator_saga服务器可以正常启动
uv run python -m elevator_saga.server.simulator
# 输出: Running on http://127.0.0.1:8000

# 但/state端点不存在
curl http://127.0.0.1:8000/state
# 输出: 404 Not Found
```

## 下一步行动

1. **选择方案**：建议从方案A开始（快速见效）
2. **实现mock simulation**：30分钟
3. **测试可视化**：验证电梯移动效果
4. **（可选）升级到方案B**：需要更多时间研究

## 相关文件

- `webui/simulation.py` - 需要重写
- `webui/app.py` - WebSocket处理器（第107-172行）
- `webui/static/js/*` - 前端代码（已完成）
- `algo/base_algorithm.py` - 理解算法如何工作
