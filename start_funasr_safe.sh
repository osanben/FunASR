#!/bin/bash
# FunASR 安全启动脚本 - 最保守配置

echo "🚀 FunASR 安全启动脚本"
echo "=================================="

# 1. 设置最严格的OpenMP限制
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export BLIS_NUM_THREADS=1

# 2. 内存管理优化
export MALLOC_ARENA_MAX=2
export MALLOC_MMAP_THRESHOLD_=131072
export MALLOC_TRIM_THRESHOLD_=131072

# 3. OpenMP行为控制
export OMP_WAIT_POLICY=PASSIVE
export OMP_PROC_BIND=FALSE
export OMP_DYNAMIC=TRUE

# 4. Python内存管理
export PYTHONMALLOC=malloc

echo "🔧 环境变量设置:"
echo "   OMP_NUM_THREADS=$OMP_NUM_THREADS"
echo "   MKL_NUM_THREADS=$MKL_NUM_THREADS"
echo "   MALLOC_ARENA_MAX=$MALLOC_ARENA_MAX"

# 5. 检查系统资源
echo ""
echo "📊 系统资源检查:"
echo "   CPU核心数: $(nproc)"
echo "   内存总量: $(free -h | grep '^Mem:' | awk '{print $2}')"
echo "   当前进程数: $(ps aux | wc -l)"

# 6. 启动服务（单任务模式）
echo ""
echo "🌟 启动FunASR服务（单任务模式）..."

# 使用最保守的参数
python runtime/python/websocket/funasr_upload_server.py \
    --host 0.0.0.0 \
    --port 10095 \
    --http_port 8080 \
    --model_type paraformer \
    --device cuda \
    --ngpu 1 \
    --ncpu 1 \
    --env test

echo "🏁 服务已停止" 