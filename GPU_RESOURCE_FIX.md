# GPU资源耗尽问题修复指南

## 问题症状
- `libgomp: Thread creation failed: Resource temporarily unavailable`
- `段错误 (核心已转储)`
- `fork: retry: 资源暂时不可用`

## 根本原因
1. **线程创建过多**: OpenMP、MKL等库创建了过多线程
2. **并发控制不当**: 线程池配置过于激进
3. **GPU内存管理**: CUDA内存分配策略不当

## 已实施的修复

### 1. 环境变量限制
```bash
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export NUMEXPR_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
```

### 2. 保守的线程池配置
- GPU环境: 最多4个worker，通常2-4个
- CPU环境: 最多6个worker，通常2-6个
- 并发控制器: GPU环境下进一步减半

### 3. GPU内存限制
- 显存使用限制: 70%（而非90%）
- 批处理大小: 固定为1（最保守）
- 自动清理GPU缓存

## 使用安全启动脚本

```bash
python start_safe_gpu_server.py
```

该脚本包含：
- 系统资源限制
- 环境变量设置
- 错误检测和重启
- 优雅关闭处理

## 手动启动（如果脚本不可用）

```bash
# 设置环境变量
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export NUMEXPR_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export CUDA_VISIBLE_DEVICES=0

# 启动服务器
python runtime/python/websocket/funasr_upload_server.py \
    --host 0.0.0.0 \
    --port 10095 \
    --http_port 8080 \
    --model_type paraformer \
    --device cuda \
    --ngpu 1 \
    --env local
```

## 系统级修复（如果问题持续）

### 1. 增加系统限制
```bash
# 编辑 /etc/security/limits.conf
* soft nproc 4096
* hard nproc 8192
* soft nofile 4096
* hard nofile 8192
```

### 2. 内核参数调整
```bash
# 编辑 /etc/sysctl.conf
kernel.threads-max = 4096
vm.max_map_count = 262144
```

### 3. 重启系统
```bash
sudo reboot
```

## 监控和调试

### 1. 检查线程数
```bash
ps -eLf | wc -l  # 总线程数
ps -p $PID -T    # 特定进程的线程
```

### 2. 检查内存使用
```bash
nvidia-smi       # GPU内存
free -h          # 系统内存
```

### 3. 检查系统限制
```bash
ulimit -a        # 当前用户限制
cat /proc/sys/kernel/threads-max  # 系统线程上限
```

## 预防措施

1. **始终使用资源限制**: 不要直接启动服务器
2. **监控系统资源**: 定期检查内存和线程使用
3. **保守配置**: 宁可性能低一些，也要保证稳定性
4. **分批处理**: 避免同时处理大量任务

## 应急处理

如果系统已经卡死：
1. `sudo pkill -f funasr` - 强制杀死所有相关进程
2. `sudo reboot` - 重启系统
3. 使用安全启动脚本重新启动

## 性能调优

在稳定运行后，可以逐步调整：
1. 增加worker数量（从2开始，逐步增加到4）
2. 调整GPU内存使用率（从70%开始，逐步增加到85%）
3. 监控系统资源，确保不超过限制 