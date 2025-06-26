# LibGOMP问题最终解决方案 🎯

## 问题根源分析 🔍

**核心问题**: CAM++说话人识别模型在并发环境下创建过多OpenMP线程导致资源耗尽

**错误表现**:
```
libgomp: Thread creation failed: Resource temporarily unavailable
malloc(): unsorted double linked list corrupted
```

**根本原因**: 4个并发任务 × 默认OpenMP线程数 = 系统线程数超限

## 已实施的多层修复 🛡️

### 第1层：全局环境变量控制
```bash
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1  
export OPENBLAS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export BLIS_NUM_THREADS=1
export KMP_DUPLICATE_LIB_OK=TRUE
```

### 第2层：Python代码内控制
在 `funasr_upload_server.py` 文件开头：
```python
# 在所有导入之前设置
os.environ['OMP_NUM_THREADS'] = '1'
# ... 其他设置
```

### 第3层：PyTorch专用控制
```python
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
```

### 第4层：函数级别保护
在CAM++函数内再次确保单线程模式

## 推荐使用方案 ⭐

### 方案1：使用安全启动脚本（推荐）
```bash
./start_with_thread_control.sh
```

### 方案2：手动设置环境变量
```bash
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
python runtime/python/websocket/funasr_upload_server.py --ncpu 2 --device cuda
```

### 方案3：完全禁用CAM++模型
如果问题仍然存在，可以在代码中注释掉CAM++相关调用

## 验证步骤 ✅

1. **启动前检查**:
   ```bash
   echo $OMP_NUM_THREADS  # 应该输出 1
   ```

2. **启动服务器**:
   ```bash
   ./start_with_thread_control.sh
   ```

3. **观察日志**: 应该看到以下信息:
   - ✅ 全局线程控制设置完成
   - 🔧 PyTorch线程已设置为1
   - 🔧 CAM++函数已强制设置单线程模式

## 故障排除 🔧

如果问题仍然存在：

1. **检查系统限制**:
   ```bash
   ulimit -u  # 查看用户进程限制
   ulimit -v  # 查看虚拟内存限制
   ```

2. **降低并发数**:
   ```bash
   --ncpu 1  # 使用单任务模式
   ```

3. **使用CPU模式**:
   ```bash
   --device cpu  # 避免GPU相关的线程问题
   ```

## 技术细节 📋

- **OpenMP**: 多平台共享内存并行编程API
- **libgomp**: GNU OpenMP运行时库
- **线程池**: 每个并发任务默认创建8个OpenMP线程
- **资源限制**: 系统对单用户线程数有限制

## 成功标志 🎉

启动成功的标志：
- ✅ 无libgomp错误信息
- ✅ CAM++模型正常加载
- ✅ 说话人识别功能正常
- ✅ 服务器稳定运行

---

**最终建议**: 使用 `./start_with_thread_control.sh` 启动，这是最安全的方式。 