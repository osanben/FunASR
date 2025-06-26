# FunASR GPU 性能优化指南

## 🚀 概述

本指南将帮助你最大化FunASR服务器的GPU性能，实现更高的并发处理能力和转录效率。

## 📊 优化特性

### 1. 动态并发控制
- **智能线程池调整**：根据GPU/CPU资源自动调整最优worker数量
- **负载感知**：实时监控CPU、内存使用率，动态调整并发数
- **过载保护**：当系统负载过高时自动拒绝新任务

### 2. GPU内存管理
- **显存优化**：自动设置90%显存使用率
- **内存清理**：当GPU内存使用率超过85%时自动清理缓存
- **批处理优化**：根据显存大小动态调整批处理大小

### 3. 并发负载分析
- **实时监控**：系统监控页面显示并发数与负载关系
- **性能对照表**：不同并发数下的系统负载对比
- **最佳配置推荐**：自动推荐最优并发数

## 🔧 快速开始

### 1. 使用优化启动脚本（推荐）

```bash
# 自动检测系统配置并启动优化服务器
python3 start_optimized_server.py

# 指定模型类型
python3 start_optimized_server.py --model-type paraformer

# 自定义端口
python3 start_optimized_server.py --port 8080
```

### 2. 手动启动（高级用户）

```bash
# GPU环境启动
python3 runtime/python/websocket/funasr_upload_server.py \
    --model-type paraformer \
    --device cuda \
    --ngpu 1 \
    --host 0.0.0.0 \
    --port 8080
```

### 3. 性能测试

```bash
# 运行并发性能测试
python3 test_concurrent_performance.py --audio your_audio_file.wav

# 指定并发数测试
python3 test_concurrent_performance.py --audio your_audio_file.wav --concurrent 8
```

## 📈 配置优化建议

### GPU配置矩阵

| GPU显存 | 推荐并发数 | 批处理大小 | 适用场景 |
|---------|------------|------------|----------|
| 4GB     | 4-6        | 1          | 轻量级使用 |
| 8GB     | 6-8        | 2          | 中等负载 |
| 12GB    | 8-12       | 2          | 高负载 |
| 16GB+   | 12-16      | 4          | 极高负载 |
| 24GB+   | 16-20      | 4          | 企业级 |

### CPU配置建议

| CPU核心数 | GPU环境并发数 | CPU环境并发数 |
|-----------|---------------|---------------|
| 4核       | 4-6           | 4             |
| 8核       | 8-12          | 6             |
| 16核      | 12-16         | 8             |
| 32核+     | 16-20         | 12            |

## 🎯 性能调优步骤

### 1. 基线测试
```bash
# 测试当前配置性能
python3 test_concurrent_performance.py --audio test_audio.wav --concurrent 2
```

### 2. 逐步增加并发
```bash
# 测试不同并发级别
python3 test_concurrent_performance.py --audio test_audio.wav --concurrent 4
python3 test_concurrent_performance.py --audio test_audio.wav --concurrent 6
python3 test_concurrent_performance.py --audio test_audio.wav --concurrent 8
```

### 3. 监控系统负载
访问 `http://localhost:8080/system_monitor` 查看：
- CPU和内存使用率
- GPU内存使用情况
- 并发任务趋势
- 并发负载关系图

### 4. 分析性能报告
访问 `http://localhost:8080/performance_report` 查看：
- 机器效率统计
- 转录效率比
- 吞吐量分析

## 🔍 故障排除

### 常见问题

#### 1. 服务器过载 (503错误)
**症状**：上传文件时返回"服务器负载过高"
**解决方案**：
- 降低并发数
- 增加系统资源
- 检查GPU内存使用率

#### 2. GPU内存不足
**症状**：CUDA out of memory错误
**解决方案**：
- 减少批处理大小
- 降低并发数
- 清理GPU缓存

#### 3. CPU使用率过高
**症状**：系统响应缓慢，CPU > 90%
**解决方案**：
- 减少worker数量
- 优化音频预处理
- 考虑增加CPU资源

### 性能优化检查清单

- [ ] GPU驱动程序最新
- [ ] CUDA版本兼容
- [ ] 足够的系统内存 (推荐16GB+)
- [ ] SSD存储用于音频文件
- [ ] 网络带宽充足
- [ ] 系统监控正常运行

## 📊 监控指标说明

### 关键性能指标 (KPI)

1. **转录效率比**：转录时间 / 音频时长
   - 目标：< 0.5x (GPU环境)
   - 优秀：< 0.3x

2. **平均并发数**：同时处理的任务数
   - 监控趋势变化
   - 与系统负载关联分析

3. **吞吐量**：每小时处理的音频时长
   - 计算公式：1 / 转录效率比
   - 目标：> 2小时音频/小时

4. **系统负载**：
   - CPU使用率 < 80%
   - 内存使用率 < 85%
   - GPU内存使用率 < 90%

## 🎛️ 高级配置

### 环境变量配置

```bash
# GPU优化
export CUDA_VISIBLE_DEVICES=0,1  # 指定使用的GPU
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512  # GPU内存分配优化

# 并发控制
export FUNASR_MAX_WORKERS=12     # 最大worker数
export FUNASR_BATCH_SIZE=2       # 批处理大小

# 监控配置
export FUNASR_MONITOR_INTERVAL=30  # 监控间隔(秒)
```

### 配置文件示例

```python
# optimized_config.py
DEVICE = "cuda"
NGPU = 1
MAX_WORKERS = 12
BATCH_SIZE = 2
ENABLE_GPU_OPTIMIZATION = True
ENABLE_DYNAMIC_CONCURRENCY = True
ENABLE_LOAD_BALANCING = True
```

## 📞 技术支持

如果遇到性能问题，请提供以下信息：
1. 系统配置（CPU、内存、GPU）
2. 并发测试结果
3. 系统监控截图
4. 错误日志

---

**🎯 目标：通过合理配置，在GPU环境下实现10+并发转录，转录效率比 < 0.3x** 