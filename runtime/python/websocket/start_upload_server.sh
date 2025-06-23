#!/bin/bash

# FunASR 文件上传服务器启动脚本

echo "🚀 启动 FunASR 文件上传服务器..."

# 检查conda环境
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "⚠️  未检测到conda环境，尝试激活funasr环境..."
    source ~/miniconda3/etc/profile.d/conda.sh 2>/dev/null || source ~/anaconda3/etc/profile.d/conda.sh 2>/dev/null
    conda activate funasr 2>/dev/null || echo "❌ 无法激活funasr环境，请手动激活"
fi

echo "📦 当前环境: $CONDA_DEFAULT_ENV"

# 检查必要的依赖
echo "🔍 检查依赖..."
python -c "import aiohttp, aiohttp_cors, librosa, websockets" 2>/dev/null || {
    echo "❌ 缺少依赖，正在安装..."
    pip install aiohttp aiohttp-cors librosa websockets
}

# 设置参数
MODEL_TYPE=${1:-"whisper"}  # 默认使用whisper
WHISPER_MODEL=${2:-"base"}  # 默认使用base模型
HTTP_PORT=${3:-8080}        # HTTP端口
WS_PORT=${4:-10095}         # WebSocket端口
DEVICE=${5:-"cpu"}          # 设备类型

echo "🎯 配置信息:"
echo "   模型类型: $MODEL_TYPE"
echo "   Whisper模型: $WHISPER_MODEL"
echo "   HTTP端口: $HTTP_PORT"
echo "   WebSocket端口: $WS_PORT"
echo "   设备: $DEVICE"

# 启动服务器
python funasr_upload_server.py \
    --model_type "$MODEL_TYPE" \
    --whisper_model "$WHISPER_MODEL" \
    --http_port "$HTTP_PORT" \
    --port "$WS_PORT" \
    --device "$DEVICE" \
    --host "127.0.0.1"

echo "👋 服务器已停止" 