#!/bin/bash

echo "🎯 FunASR WebSocket服务日志查看工具"
echo "=================================="

# 停止现有服务
echo "🛑 停止现有WebSocket服务..."
pkill -f "修复后的websocket服务.py" 2>/dev/null

# 等待服务完全停止
sleep 2

# 创建日志目录
mkdir -p logs

# 启动服务并将日志输出到文件和控制台
echo "🚀 启动WebSocket服务（带日志输出）..."
echo "📝 日志文件: logs/websocket.log"
echo "🔍 实时查看日志，按Ctrl+C停止"
echo "=================================="
echo ""

# 启动服务，同时输出到文件和控制台
python3 修复后的websocket服务.py 2>&1 | tee logs/websocket.log 