#!/bin/bash
# FunASR 安全启动脚本 - 解决libgomp错误

echo "🔧 设置线程控制环境变量..."

# 设置所有OpenMP相关的环境变量
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export BLIS_NUM_THREADS=1
export KMP_DUPLICATE_LIB_OK=TRUE

# Intel MKL相关设置
export MKL_SERIAL=YES
export MKL_DYNAMIC=FALSE

# NVIDIA相关设置（如果使用GPU）
export CUDA_LAUNCH_BLOCKING=1

echo "✅ 线程控制环境变量已设置："
echo "  OMP_NUM_THREADS=$OMP_NUM_THREADS"
echo "  MKL_NUM_THREADS=$MKL_NUM_THREADS"
echo "  OPENBLAS_NUM_THREADS=$OPENBLAS_NUM_THREADS"
echo "  VECLIB_MAXIMUM_THREADS=$VECLIB_MAXIMUM_THREADS"
echo "  NUMEXPR_NUM_THREADS=$NUMEXPR_NUM_THREADS"
echo "  BLIS_NUM_THREADS=$BLIS_NUM_THREADS"

echo ""
echo "🚀 启动FunASR服务器..."
echo "   使用安全的单线程配置"

# 启动服务器，使用保守的参数
python runtime/python/websocket/funasr_upload_server.py \
    --host 0.0.0.0 \
    --port 10095 \
    --http_port 8080 \
    --model_type paraformer \
    --device cuda \
    --ngpu 1 \
    --ncpu 2 \
    --env test

echo "🔚 FunASR服务器已停止" 