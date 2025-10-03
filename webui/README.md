# Elevator Scheduling WebUI

实时可视化电梯调度算法的Web界面。

## 功能特性

### 核心功能
- ✅ 实时电梯位置可视化
- ✅ Canvas 2D 渲染电梯、乘客和楼层
- ✅ 支持暂停/继续/停止操作
- ✅ 速度调节 (0.1x - 5x)
- ✅ 实时统计信息（总数/等待/运行中/已完成/平均等待时间）
- ✅ 选择不同测试场景（10+ 预设场景）
- ✅ WebSocket 实时通信

### UI 改进 (2025年最新)
- ✅ **自动加载默认配置**: 页面加载时立即显示第一个场景的电梯布局
- ✅ **左对齐可视化区域**: 优化视觉布局，更符合阅读习惯
- ✅ **场景切换即时更新**: 选择场景时立即更新可视化（无需启动模拟）
- ✅ **模拟完成自动归位**: 所有电梯回到1层，乘客清空，状态重置
- ✅ **平滑动画效果**: 20%插值算法实现流畅的电梯移动
- ✅ **颜色编码状态**:
  - 灰色 = 空闲
  - 绿色 = 上行
  - 橙色 = 下行
  - 深蓝色 = 乘客在电梯中

## 快速开始

### 启动WebUI

```bash
# 方式1：使用启动脚本
./start_webui.sh

# 方式2：直接运行
uv run python -m webui.app

# 方式3：使用Python模块
cd webui && uv run python app.py
```

服务器将在 http://localhost:8080 启动。

### 使用步骤

1. 在浏览器中访问 http://localhost:8080
2. **页面自动加载**：首个场景的电梯配置自动显示在右侧Canvas区域
3. （可选）在左侧边栏选择其他测试场景 → **可视化立即更新**
4. （可选）调整模拟速度（0.1x - 5x）
5. 点击"开始模拟"按钮启动模拟
6. 在右侧Canvas区域观察电梯实时运行
7. 使用暂停/继续/停止按钮控制模拟
8. 查看左下方统计面板中的实时性能指标
9. 模拟完成后，所有电梯自动归位到1层

## 架构说明

### 后端 (FastAPI)

- **app.py**: FastAPI应用主文件
  - `GET /`: 主页面
  - `GET /api/algorithms`: 获取可用算法列表（占位符，当前未使用）
  - `GET /api/scenarios`: 获取测试场景列表（读取data/目录下的JSON文件）
  - `WebSocket /ws/simulation`: 实时模拟通信

- **mock_simulation.py**: Mock模拟引擎
  - 加载场景数据（building配置和traffic事件）
  - 使用简化调度逻辑（最近电梯分配策略）
  - 模拟电梯移动、乘客上下
  - 通过WebSocket广播状态更新（每100ms）
  - 支持暂停/继续/停止/速度调节

### 前端 (HTML + CSS + JavaScript)

- **index.html**: 主页面结构
- **css/style.css**: 完整样式系统
- **js/renderer.js**: Canvas渲染引擎
  - 绘制楼层、电梯、乘客
  - 20%插值算法实现平滑动画
  - 左对齐布局计算
  - 自适应响应式布局
  - 完成状态处理（电梯归位到1层）
- **js/websocket.js**: WebSocket管理
  - 自动重连机制
  - 消息分发系统
- **js/app.js**: 应用主逻辑
  - UI事件处理
  - 状态管理
  - 动画循环（requestAnimationFrame）
  - 默认配置自动加载
  - 场景切换即时更新可视化

## 工作流程

### 当前实现（方案C - Mock模拟）⭐

1. **用户点击"开始模拟"**
2. WebSocket连接到服务器
3. 服务器创建MockSimulationEngine实例并在后台任务中启动
4. MockEngine加载选定的场景数据（JSON文件）
5. MockEngine使用简化的调度逻辑模拟电梯移动
   - 最近电梯分配
   - 简单的上下行逻辑
   - 乘客上下处理
6. MockEngine通过WebSocket广播状态更新（每100ms）
7. 前端接收状态并更新Canvas渲染
8. 前端使用插值实现平滑动画

**优点**：
- ✅ 无需外部服务器
- ✅ 快速响应
- ✅ 完整的视觉效果
- ✅ 适合演示和UI开发
- ✅ 支持暂停/继续/停止/速度调节

**局限**：
- ⚠️ 不运行真实的调度算法
- ⚠️ 使用简化的最近电梯策略
- ⚠️ 性能数据仅供参考
- ⚠️ 不能用于算法对比研究

**已验证功能**：
- ✅ 电梯在不同楼层间移动
- ✅ 乘客上下电梯
- ✅ 实时统计更新（等待/电梯中/已完成）
- ✅ 方向指示器和颜色编码
- ✅ 平滑动画效果（20%插值）
- ✅ 页面加载时自动显示默认配置
- ✅ 场景切换时立即更新可视化
- ✅ 模拟完成后电梯归位到1层

### 未来实现（方案B - 真实算法）🚀

详见 [`docs/webui_real_algorithm_integration.md`](../docs/webui_real_algorithm_integration.md)

通过直接使用elevator_saga内部API运行真实算法：
1. 创建Simulation实例
2. 加载traffic数据
3. 连接算法控制器
4. 每个tick提取状态并广播

**优点**：
- ✅ 运行真实算法
- ✅ 精确的性能指标
- ✅ 可用于算法研究

**需求**：
- 修改算法基类支持direct模式
- 深入研究elevator_saga内部API
- 预计16-24小时开发时间

## 状态数据格式

### 服务器 → 客户端

#### Init Message
```json
{
  "type": "init",
  "building": {
    "floors": 10,
    "elevators": 3,
    "capacity": 8,
    "description": "场景描述",
    "duration": 300
  },
  "algorithm": "HybridScanRLAlgorithm",
  "scenario": "small_morning_rush"
}
```

#### State Update
```json
{
  "type": "state_update",
  "tick": 42,
  "elevators": [
    {
      "id": 0,
      "floor": 3.5,
      "direction": "up",
      "passengers": [{}, {}],
      "capacity": 8
    }
  ],
  "waiting": {
    "1": [{"id": 1, "from_floor": 1, "to_floor": 5}],
    "4": [{"id": 2, "from_floor": 4, "to_floor": 1}]
  },
  "stats": {
    "total_passengers": 100,
    "waiting": 20,
    "in_elevator": 5,
    "completed": 75,
    "avg_wait_time": 12.5
  }
}
```

#### Complete Message
```json
{
  "type": "complete",
  "tick": 300,
  "stats": {
    "total_passengers": 100,
    "avg_wait_time": 15.2
  }
}
```

### 客户端 → 服务器

```json
{"type": "start", "algorithm": "HybridScanRLAlgorithm", "scenario": "small_morning_rush", "speed": 1.0}
{"type": "pause"}
{"type": "resume"}
{"type": "stop"}
{"type": "set_speed", "speed": 2.0}
```

## 故障排除

### 电梯不显示

**可能原因1**: Canvas未正确初始化
- 打开浏览器开发者工具 (F12)
- 查看Console是否有JavaScript错误
- 检查是否看到 "ElevatorRenderer: Initializing..." 日志

**可能原因2**: WebSocket连接失败
- 查看Console中的WebSocket连接日志
- 确认服务器正在运行
- 检查端口8080是否被占用

**可能原因3**: 场景加载失败
- 检查 `data/` 目录中是否存在场景JSON文件
- 查看服务器端日志是否有错误

**可能原因4**: 电梯服务器未启动
- WebUI会自动启动服务器，但可能失败
- 检查端口8000是否可用
- 查看Console中的错误信息

### 手动测试渲染器

访问 http://localhost:8080/static/test.html 查看渲染器测试页面。
这个页面会独立测试Canvas渲染功能。

### 查看日志

打开浏览器开发者工具 (F12) → Console标签，查看:
- `Initializing application...`
- `Creating renderer...`
- `Renderer created, canvas size: ...`
- `ElevatorRenderer: Initializing with config: ...`
- `WebSocket connected`

## 开发指南

### 修改渲染样式

编辑 `static/js/renderer.js` 中的 `colors` 对象：

```javascript
this.colors = {
    background: '#ffffff',
    elevator: '#3498db',      // 电梯颜色
    elevatorUp: '#27ae60',    // 上行电梯
    elevatorDown: '#e67e22',  // 下行电梯
    passenger: '#e74c3c',     // 等待乘客
    // ...
};
```

### 修改布局

编辑 `static/js/renderer.js` 中的布局参数：

```javascript
this.floorHeight = 60;        // 楼层高度
this.elevatorWidth = 80;      // 电梯宽度
this.elevatorHeight = 50;     // 电梯高度
this.elevatorSpacing = 100;   // 电梯间距
```

### 添加新的UI控件

1. 在 `static/index.html` 中添加HTML元素
2. 在 `static/css/style.css` 中添加样式
3. 在 `static/js/app.js` 中添加事件处理

## 性能优化

- Canvas渲染使用requestAnimationFrame确保60fps
- 状态更新频率: 10次/秒 (可通过speed参数调节)
- WebSocket使用JSON格式最小化传输数据
- 插值算法实现平滑动画而不增加网络负载

## 浏览器兼容性

- ✅ Chrome/Edge (推荐)
- ✅ Firefox
- ✅ Safari
- ⚠️ IE不支持 (使用了Canvas 2D API和WebSocket)
