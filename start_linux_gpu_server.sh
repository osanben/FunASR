#!/bin/bash

# Linux GPU环境FunASR服务器启动脚本
# 包含资源限制和错误处理

echo "🚀 启动Linux GPU FunASR服务器"
echo "=================================="

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    echo "⚠️ 警告: 不建议以root用户运行"
fi

# 设置环境变量防止线程创建失败
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export NUMEXPR_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

echo "🔧 已设置环境变量:"
echo "   OMP_NUM_THREADS=$OMP_NUM_THREADS"
echo "   MKL_NUM_THREADS=$MKL_NUM_THREADS"
echo "   NUMEXPR_NUM_THREADS=$NUMEXPR_NUM_THREADS"
echo "   OPENBLAS_NUM_THREADS=$OPENBLAS_NUM_THREADS"
echo "   CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"

# 设置系统资源限制
echo "🔒 设置资源限制..."
ulimit -u 1024    # 限制用户进程数
ulimit -n 1024    # 限制文件描述符数
ulimit -v 8388608 # 限制虚拟内存 (8GB)

echo "📊 当前资源限制:"
echo "   最大进程数: $(ulimit -u)"
echo "   最大文件描述符: $(ulimit -n)"
echo "   最大虚拟内存: $(ulimit -v) KB"

# 检查GPU状态
echo "🎮 检查GPU状态..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv,noheader,nounits | while IFS=, read -r idx name total used; do
        usage_percent=$((used * 100 / total))
        echo "   GPU $idx: $name, 显存: ${used}MB/${total}MB (${usage_percent}%)"
    done
else
    echo "   ⚠️ nvidia-smi 未找到，无法检查GPU状态"
fi

# 检查系统负载
echo "💻 系统状态:"
echo "   CPU核心数: $(nproc)"
echo "   内存总量: $(free -h | awk '/^Mem:/ {print $2}')"
echo "   当前负载: $(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')"

# 清理可能存在的旧进程
echo "🧹 清理旧进程..."
pkill -f "funasr_upload_server.py" 2>/dev/null || true
sleep 2

# 启动服务器
echo "🎯 启动服务器..."
python3 runtime/python/websocket/funasr_upload_server.py \
    --host 0.0.0.0 \
    --port 10095 \
    --http_port 8080 \
    --model_type paraformer \
    --device cuda \
    --ngpu 1 \
    --env local \
    2>&1 | while IFS= read -r line; do
        echo "[$(date '+%H:%M:%S')] $line"
        
        # 检查错误模式
        if echo "$line" | grep -qi "libgomp.*thread creation failed"; then
            echo "❌ 检测到libgomp线程创建失败，正在重启..."
            pkill -f "funasr_upload_server.py"
            exit 1
        fi
        
        if echo "$line" | grep -qi "segmentation fault\|段错误"; then
            echo "❌ 检测到段错误，正在重启..."
            pkill -f "funasr_upload_server.py"
            exit 1
        fi
        
        if echo "$line" | grep -qi "resource temporarily unavailable"; then
            echo "❌ 检测到资源不可用错误，正在重启..."
            pkill -f "funasr_upload_server.py"
            exit 1
        fi
        
        # 检查成功启动
        if echo "$line" | grep -qi "服务器启动完成\|server.*start"; then
            echo "✅ 服务器启动成功!"
        fi
    done

# 如果到这里说明服务器异常退出
echo "❌ 服务器异常退出"
exit 1 