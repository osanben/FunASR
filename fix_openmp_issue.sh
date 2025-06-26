#!/bin/bash
# 修复OpenMP线程创建失败问题

# 设置OpenMP环境变量
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export VECLIB_MAXIMUM_THREADS=4
export NUMEXPR_NUM_THREADS=4

# 设置内存分配策略
export MALLOC_ARENA_MAX=4

# 启动FunASR服务
python runtime/python/websocket/funasr_upload_server.py \
    --host 0.0.0.0 \
    --port 10095 \
    --http_port 8080 \
    --model_type paraformer \
    --device cuda \
    --ngpu 1 \
    --ncpu 4 \
    --env test 