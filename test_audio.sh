#!/bin/bash

# FunASR WebSocket 音频测试脚本

echo "🌟 FunASR WebSocket 音频测试工具"
echo "================================"

# 设置环境
export PYTHONPATH="/Users/csdn/github_projects/FunASR:$PYTHONPATH"
cd /Users/csdn/github_projects/FunASR/runtime/python/websocket

# 确保使用conda环境中的python
if [[ "$CONDA_DEFAULT_ENV" != "funasr" ]]; then
    echo "⚠️  警告: 当前不在funasr conda环境中"
    echo "请先执行: conda activate funasr"
    exit 1
fi

# 检查参数
if [ "$1" = "help" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ] || [ -z "$1" ]; then
    echo "使用方法:"
    echo "  $0 <音频文件路径> [WebSocket服务器地址] [超时时间]"
    echo ""
    echo "参数:"
    echo "  音频文件路径    - 要测试的音频文件 (支持MP3/WAV/M4A/AAC/FLAC等)"
    echo "  服务器地址      - WebSocket服务器地址 (默认: wss://127.0.0.1:10095/)"
    echo "  超时时间        - 超时时间秒数 (默认: 300)"
    echo ""
    echo "示例:"
    echo "  $0 ~/音频文件.mp3"
    echo "  $0 ~/音频文件.wav wss://127.0.0.1:10095/"
    echo "  $0 ~/音频文件.m4a wss://127.0.0.1:10095/ 600"
    echo ""
    echo "注意:"
    echo "  - 请确保WebSocket服务器已启动"
    echo "  - 建议先安装librosa: pip install librosa"
    exit 0
fi

AUDIO_FILE="$1"
SERVER_URL="${2:-wss://127.0.0.1:10095/}"
TIMEOUT="${3:-300}"

echo "🎯 测试参数:"
echo "  音频文件: $AUDIO_FILE"
echo "  服务器: $SERVER_URL"
echo "  超时时间: ${TIMEOUT}秒"
echo ""

# 检查音频文件是否存在
if [ ! -f "$AUDIO_FILE" ]; then
    echo "❌ 音频文件不存在: $AUDIO_FILE"
    exit 1
fi

# 检查依赖
echo "🔍 检查依赖..."
python -c "import websockets" 2>/dev/null || {
    echo "❌ 缺少websockets依赖"
    echo "请安装: pip install websockets"
    exit 1
}

python -c "import numpy" 2>/dev/null || {
    echo "❌ 缺少numpy依赖"
    echo "请安装: pip install numpy"
    exit 1
}

echo "✅ 基础依赖检查通过"

# 检查音频处理库
python -c "import librosa" 2>/dev/null && echo "✅ librosa可用 - 支持多种音频格式"
python -c "import soundfile" 2>/dev/null && echo "✅ soundfile可用 - 音频处理增强"

echo ""
echo "🚀 开始测试..."
echo ""

# 运行测试
python test_audio_client.py "$AUDIO_FILE" --server "$SERVER_URL" --timeout "$TIMEOUT"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "🎉 测试成功完成！"
    echo "💡 如果结果满意，可以继续前端联调"
else
    echo ""
    echo "💥 测试失败！"
    echo "💡 请检查:"
    echo "   1. WebSocket服务器是否正常运行"
    echo "   2. 音频文件是否完整"
    echo "   3. 网络连接是否正常"
    echo "   4. 服务器日志中的错误信息"
fi

exit $exit_code 