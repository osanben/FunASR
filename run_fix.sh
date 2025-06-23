#!/bin/bash

echo "🚀 开始修复说话人分离功能..."

# 1. 安装必要的依赖
echo "📦 安装依赖包..."
pip install scikit-learn

# 2. 运行修复脚本
echo "🔧 运行修复脚本..."
python fix_speaker_separation.py

# 3. 重启服务器
echo "🔄 停止当前服务器..."
pkill -f funasr_upload_server.py

echo "⏱️ 等待3秒..."
sleep 3

echo "🚀 重新启动服务器..."
./start_upload_server.sh --model_type paraformer

echo "✅ 修复完成！"
echo "🌐 服务器地址: http://127.0.0.1:8080"
echo "📝 现在可以上传双人对话音频文件测试说话人分离功能" 