# Traffic Scenarios Directory

This directory contains all traffic scenario files for the elevator simulation system.

## 目录说明

所有的客流场景文件统一存放在此目录中，供以下组件使用：
- **Simulator** (`simulator.py`) - 加载traffic数据进行模拟
- **WebUI** (`webui/`) - 前端选择和显示场景信息

## 文件格式

每个JSON文件包含两部分：

### 1. building配置
```json
{
  "building": {
    "floors": 6,                    // 楼层数
    "elevators": 2,                 // 电梯数量
    "elevator_capacity": 8,         // 电梯容量
    "scenario": "down_peak",        // 场景类型
    "scale": "medium",              // 规模
    "description": "场景描述",       // 显示名称
    "expected_passengers": 74,      // 预期乘客数（必须与traffic数组长度一致）
    "duration": 200                 // 模拟时长（ticks）
  }
}
```

### 2. traffic流量数据
```json
{
  "traffic": [
    {
      "id": 1,              // 乘客ID（可选，会被重新分配）
      "origin": 2,          // 起始楼层
      "destination": 0,     // 目的楼层
      "tick": 0            // 到达时间（tick）
    }
  ]
}
```

## 场景列表

### 高峰场景
- **up_peak.json** - 上行高峰（早晨上班）
- **down_peak.json** - 下行高峰（下班）
- **large_morning_rush.json** - 大规模早高峰
- **small_evening_rush.json** - 小规模晚高峰

### 特殊场景
- **lunch_rush.json** - 午餐高峰
- **meeting_event.json** - 会议集中
- **fire_evacuation.json** - 紧急疏散
- **medical.json** - 医疗紧急

### 测试场景
- **progressive_test.json** - 渐进式测试
- **high_density.json** - 高密度测试
- **random.json** - 随机流量
- **inter_floor.json** - 楼层间移动
- **xlarge_stress_test.json** - 超大压力测试

### 混合场景
- **mixed_scenario.json** - 混合场景
- **large_mixed.json** - 大规模混合

## 重要说明

⚠️ **expected_passengers 必须准确**
- `expected_passengers` 字段必须等于 `traffic` 数组的长度
- 前端会显示此数值，必须与实际乘客数一致
- 生成新场景时务必检查此字段

## 文件位置历史

此目录整合了以下历史位置的文件：
- `./data/` - 旧的数据目录
- `./elevator_saga/traffic/` - elevator_saga包内的traffic目录

现在所有文件统一存放在 `./traffic/` 目录中。
