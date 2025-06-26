#!/bin/bash
# 紧急修复脚本 - 解决FunASR并发和线程问题

echo "🚨 紧急修复 FunASR 并发问题"
echo "=================================="

# 1. 强制杀死现有服务
echo "🔪 强制停止现有FunASR服务..."
pkill -f "funasr_upload_server.py" || true
sleep 2

# 2. 清理可能的僵尸进程
echo "🧹 清理僵尸进程..."
pkill -f "python.*funasr" || true
pkill -f "CAM++" || true
sleep 2

# 3. 设置最严格的环境变量
echo "🔧 设置严格的环境限制..."
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export BLIS_NUM_THREADS=1

# 内存管理
export MALLOC_ARENA_MAX=1
export MALLOC_MMAP_THRESHOLD_=65536
export MALLOC_TRIM_THRESHOLD_=65536

# OpenMP特殊设置
export OMP_WAIT_POLICY=PASSIVE
export OMP_PROC_BIND=FALSE
export OMP_DYNAMIC=FALSE
export OMP_NESTED=FALSE

# Python内存优化
export PYTHONMALLOC=malloc
export PYTHONDONTWRITEBYTECODE=1

# 4. 显示当前系统状态
echo ""
echo "📊 当前系统状态:"
echo "   CPU核心数: $(nproc)"
echo "   内存使用: $(free -h | grep '^Mem:' | awk '{print $3"/"$2}')"
echo "   当前进程数: $(ps aux | wc -l)"
echo "   Python进程数: $(ps aux | grep python | wc -l)"

# 5. 检查GPU状态
if command -v nvidia-smi &> /dev/null; then
    echo "   GPU内存使用:"
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits | while read line; do
        used=$(echo $line | cut -d',' -f1)
        total=$(echo $line | cut -d',' -f2)
        echo "      GPU: ${used}MB/${total}MB"
    done
fi

echo ""
echo "🔧 环境变量设置:"
echo "   OMP_NUM_THREADS=$OMP_NUM_THREADS"
echo "   MKL_NUM_THREADS=$MKL_NUM_THREADS"
echo "   MALLOC_ARENA_MAX=$MALLOC_ARENA_MAX"

# 6. 启动单任务模式的FunASR
echo ""
echo "🚀 启动单任务模式 FunASR..."
echo "   并发数: 1"
echo "   CPU线程: 1"
echo "   OpenMP线程: 1"

python runtime/python/websocket/funasr_upload_server.py \
    --host 0.0.0.0 \
    --port 10095 \
    --http_port 8080 \
    --model_type paraformer \
    --device cuda \
    --ngpu 1 \
    --ncpu 1 \
    --env test 