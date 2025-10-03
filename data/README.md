# 测试数据集说明

本目录包含10个不同复杂度的电梯调度测试场景，用于全面评估算法性能。

## 测试场景概览

### 小型建筑场景 (6层楼)

#### 1. small_morning_rush.json
- **描述**: 小型建筑上班高峰
- **配置**: 6层楼，2部电梯，容量8人
- **时长**: 200 ticks
- **乘客数**: 160人
- **特点**: 80%流量从1楼到上层楼，模拟上班高峰

#### 2. small_evening_rush.json
- **描述**: 小型建筑下班高峰
- **配置**: 6层楼，2部电梯，容量8人
- **时长**: 200 ticks
- **乘客数**: 160人
- **特点**: 80%流量从上层楼到1楼，模拟下班高峰

#### 3. small_burst_traffic.json
- **描述**: 小型建筑突发流量
- **配置**: 6层楼，2部电梯，容量8人
- **时长**: 200 ticks
- **乘客数**: 73人
- **特点**: 5次突发流量，每次10-20人，测试算法对突发负载的应对

---

### 中型建筑场景 (10层楼)

#### 4. medium_inter_floor.json
- **描述**: 中型建筑楼层间流量
- **配置**: 10层楼，3部电梯，容量10人
- **时长**: 300 ticks
- **乘客数**: 120人
- **特点**: 均匀分布的楼层间流量，模拟正常办公时间

#### 5. medium_lunch_rush.json
- **描述**: 中型建筑午餐高峰
- **配置**: 10层楼，3部电梯，容量10人
- **时长**: 300 ticks
- **乘客数**: 180人
- **特点**: 前半段下行到1楼，后半段上行回各楼层

#### 6. medium_high_freq_burst.json
- **描述**: 中型建筑高频突发
- **配置**: 10层楼，3部电梯，容量10人
- **时长**: 300 ticks
- **乘客数**: 137人
- **特点**: 10次高频突发流量，测试算法快速响应能力

#### 7. medium_bottom_heavy.json
- **描述**: 中型建筑底层密集
- **配置**: 10层楼，3部电梯，容量10人
- **时长**: 400 ticks
- **乘客数**: 200人
- **特点**: 80%流量集中在0-2楼，测试非对称流量处理

---

### 大型建筑场景 (15-25层楼)

#### 8. large_mixed.json
- **描述**: 大型建筑混合场景
- **配置**: 15层楼，4部电梯，容量12人
- **时长**: 500 ticks
- **乘客数**: 297人
- **特点**: 包含上班高峰、午餐时段、下班高峰等多种模式

#### 9. large_morning_rush.json
- **描述**: 大型建筑上班高峰
- **配置**: 20层楼，5部电梯，容量15人
- **时长**: 400 ticks
- **乘客数**: 320人
- **特点**: 大规模上班高峰，高容量测试

#### 10. xlarge_stress_test.json
- **描述**: 超大型建筑压力测试
- **配置**: 25层楼，6部电梯，容量20人
- **时长**: 600 ticks
- **乘客数**: 360人
- **特点**: 极限场景，混合多种流量模式，全面压力测试

---

## 流量模式说明

### 1. Morning Rush (上班高峰)
- 大量乘客从1楼前往上层楼
- 流量密度高，集中在起始时段
- 测试单向高密度流量处理

### 2. Evening Rush (下班高峰)
- 大量乘客从上层楼前往1楼
- 流量密度高，集中在起始时段
- 测试反向高密度流量处理

### 3. Inter-floor (楼层间)
- 随机的楼层间流量
- 流量均匀分布
- 测试常规场景下的调度效率

### 4. Lunch Rush (午餐高峰)
- 双向流量：先下后上
- 测试方向转换的处理能力

### 5. Burst Traffic (突发流量)
- 短时间内大量乘客涌入
- 测试突发负载应对能力

### 6. Mixed (混合场景)
- 包含多种流量模式
- 最接近真实场景
- 全面测试算法适应性

### 7. Asymmetric (非对称流量)
- 流量在楼层间分布不均
- 测试对特殊流量分布的优化

---

## 使用方法

### 运行单个测试场景

```bash
# 需要在模拟器配置中指定流量文件
# 或使用自定义测试脚本
uv run python test_scenario.py data/small_morning_rush.json
```

### 批量测试

```bash
# 创建批量测试脚本
uv run python batch_test.py
```

---

## 性能评估指标

对每个场景，建议关注以下指标：

1. **平均等待时间** (Average Wait Time)
   - 所有乘客从呼叫到上电梯的平均时间

2. **P95等待时间** (P95 Wait Time)
   - 95%的乘客等待时间上限

3. **平均系统时间** (Average System Time)
   - 所有乘客从呼叫到到达目的地的平均时间

4. **P95系统时间** (P95 System Time)
   - 95%的乘客系统时间上限

5. **完成率** (Completion Rate)
   - 在规定时间内完成服务的乘客比例

6. **电梯利用率** (Elevator Utilization)
   - 电梯有效运行时间占比

---

## 预期性能基准

以下是各场景的难度评级和参考基准：

| 场景 | 难度 | 预期平均等待时间 | 预期P95等待时间 |
|------|------|------------------|-----------------|
| small_inter_floor | ★☆☆☆☆ | < 60 ticks | < 120 ticks |
| small_burst_traffic | ★★☆☆☆ | < 80 ticks | < 150 ticks |
| small_morning_rush | ★★★☆☆ | < 100 ticks | < 180 ticks |
| small_evening_rush | ★★★☆☆ | < 100 ticks | < 180 ticks |
| medium_inter_floor | ★★★☆☆ | < 80 ticks | < 150 ticks |
| medium_lunch_rush | ★★★★☆ | < 120 ticks | < 200 ticks |
| medium_bottom_heavy | ★★★★☆ | < 100 ticks | < 180 ticks |
| medium_high_freq_burst | ★★★★☆ | < 120 ticks | < 220 ticks |
| large_mixed | ★★★★★ | < 150 ticks | < 250 ticks |
| large_morning_rush | ★★★★★ | < 140 ticks | < 240 ticks |
| xlarge_stress_test | ★★★★★ | < 180 ticks | < 300 ticks |

---

## 生成自定义测试数据

使用 `generate_test_data.py` 脚本可以生成自定义测试数据：

```python
# 编辑 generate_test_data.py 添加新场景
# 然后运行
uv run python generate_test_data.py
```

支持的流量生成函数：
- `generate_morning_rush()` - 上班高峰
- `generate_evening_rush()` - 下班高峰
- `generate_inter_floor()` - 楼层间流量
- `generate_lunch_rush()` - 午餐高峰
- `generate_burst_traffic()` - 突发流量
- `generate_mixed_scenario()` - 混合场景
