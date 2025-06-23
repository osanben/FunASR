#!/bin/bash

# FunASR + Whisper WebSocket 服务器启动脚本

echo "🌟 FunASR + Whisper 语音识别服务器"
echo "=================================="

# 设置环境
export PYTHONPATH="/Users/csdn/github_projects/FunASR:$PYTHONPATH"
cd /Users/csdn/github_projects/FunASR/runtime/python/websocket

# 确保使用conda环境中的python
# 检查是否在conda环境中
if [[ "$CONDA_DEFAULT_ENV" != "funasr" ]]; then
    echo "⚠️  警告: 当前不在funasr conda环境中"
    echo "请先执行: conda activate funasr"
    echo "然后再运行此脚本"
    exit 1
fi

# 使用conda环境中的python
PYTHON_CMD="python"

# 检查参数
if [ "$1" = "help" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "使用方法:"
    echo "  $0 [模型类型] [模型大小] [端口] [设备]"
    echo ""
    echo "模型类型:"
    echo "  whisper     - 使用Whisper模型 (第一梯队，免费开源)"
    echo "  paraformer  - 使用Paraformer模型 (FunASR原生)"
    echo "  sensevoice  - 使用SenseVoice模型 (最新多任务)"
    echo "  hybrid      - 同时使用多个模型进行对比"
    echo ""
    echo "Whisper模型大小:"
    echo "  tiny   - 39M参数，最快但准确率较低"
    echo "  base   - 74M参数，平衡速度和准确率"
    echo "  small  - 244M参数，较好的准确率"
    echo "  medium - 769M参数，高准确率"
    echo "  large  - 1550M参数，最高准确率"
    echo "  large-v2 - 1550M参数，改进版"
    echo "  large-v3 - 1550M参数，最新版本 (推荐)"
    echo ""
    echo "示例:"
    echo "  $0 whisper large-v3 10095 cuda    # 使用Whisper Large-V3，CUDA加速"
    echo "  $0 paraformer \"\" 10096 cuda       # 使用Paraformer"
    echo "  $0 hybrid large-v3 10097 cuda     # 同时使用两个模型对比"
    exit 0
fi

# 默认参数
MODEL_TYPE=${1:-"whisper"}
WHISPER_MODEL=${2:-"large-v3"}
PORT=${3:-"10095"}
DEVICE=${4:-"cuda"}

echo "🎯 启动参数:"
echo "  模型类型: $MODEL_TYPE"
if [ "$MODEL_TYPE" = "whisper" ] || [ "$MODEL_TYPE" = "hybrid" ]; then
    echo "  Whisper模型: $WHISPER_MODEL"
fi
echo "  端口: $PORT"
echo "  设备: $DEVICE"
echo ""

# 检查设备
if [ "$DEVICE" = "cuda" ]; then
    $PYTHON_CMD -c "import torch; print('🚀 CUDA可用:', torch.cuda.is_available())"
elif [ "$DEVICE" = "mps" ]; then
    $PYTHON_CMD -c "import torch; print('🚀 MPS可用:', torch.backends.mps.is_available())"
fi

echo ""
echo "🔄 启动服务器..."

# 根据模型类型启动服务器
case $MODEL_TYPE in
    "whisper")
        $PYTHON_CMD funasr_wss_server_whisper.py \
            --model_type whisper \
            --whisper_model $WHISPER_MODEL \
            --whisper_language zh \
            --port $PORT \
            --device $DEVICE \
            --host 0.0.0.0
        ;;
    "paraformer")
        $PYTHON_CMD funasr_wss_server_whisper.py \
            --model_type paraformer \
            --port $PORT \
            --device $DEVICE \
            --host 0.0.0.0
        ;;
    "sensevoice")
        $PYTHON_CMD funasr_wss_server_whisper.py \
            --model_type sensevoice \
            --port $PORT \
            --device $DEVICE \
            --host 0.0.0.0
        ;;
    "hybrid")
        $PYTHON_CMD funasr_wss_server_whisper.py \
            --model_type hybrid \
            --whisper_model $WHISPER_MODEL \
            --whisper_language zh \
            --port $PORT \
            --device $DEVICE \
            --host 0.0.0.0
        ;;
    *)
        echo "❌ 不支持的模型类型: $MODEL_TYPE"
        echo "支持的类型: whisper, paraformer, sensevoice, hybrid"
        exit 1
        ;;
esac 
