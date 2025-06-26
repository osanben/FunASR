#!/bin/bash

# FunASR Linux GPU环境一键安装脚本
# 适用于 Ubuntu 18.04+ / CentOS 7+

set -e  # 遇到错误立即退出

echo "🚀 FunASR Linux GPU环境一键安装脚本"
echo "=========================================="

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    echo "❌ 无法检测操作系统"
    exit 1
fi

echo "📋 检测到操作系统: $OS $VER"

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    echo "⚠️ 警告: 不建议以root用户运行此脚本"
    read -p "是否继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 1. 更新系统
echo "🔄 更新系统..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    sudo apt update && sudo apt upgrade -y
    PACKAGE_MANAGER="apt"
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    sudo yum update -y
    PACKAGE_MANAGER="yum"
else
    echo "⚠️ 未知的操作系统，尝试使用apt..."
    PACKAGE_MANAGER="apt"
fi

# 2. 安装系统依赖
echo "📦 安装系统依赖..."
if [ "$PACKAGE_MANAGER" = "apt" ]; then
    sudo apt install -y python3 python3-pip python3-venv git wget curl
    sudo apt install -y build-essential cmake pkg-config
    sudo apt install -y libsndfile1 libsndfile1-dev
    sudo apt install -y ffmpeg
elif [ "$PACKAGE_MANAGER" = "yum" ]; then
    sudo yum install -y python3 python3-pip git wget curl
    sudo yum groupinstall -y "Development Tools"
    sudo yum install -y cmake pkgconfig
    sudo yum install -y libsndfile libsndfile-devel
    sudo yum install -y ffmpeg
fi

# 3. 检查NVIDIA GPU
echo "🎮 检查NVIDIA GPU..."
if lspci | grep -i nvidia > /dev/null; then
    echo "✅ 检测到NVIDIA GPU:"
    lspci | grep -i nvidia
else
    echo "❌ 未检测到NVIDIA GPU"
    read -p "是否继续安装CPU版本? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    DEVICE_TYPE="cpu"
fi

# 4. 检查NVIDIA驱动
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA驱动已安装:"
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
    DEVICE_TYPE="cuda"
else
    echo "⚠️ 未检测到NVIDIA驱动"
    if [ "$PACKAGE_MANAGER" = "apt" ]; then
        echo "🔧 尝试安装NVIDIA驱动..."
        sudo ubuntu-drivers autoinstall
        echo "🔄 请重启系统后重新运行此脚本"
        exit 0
    else
        echo "❌ 请手动安装NVIDIA驱动后重新运行此脚本"
        exit 1
    fi
fi

# 5. 创建Python虚拟环境
echo "🐍 创建Python虚拟环境..."
if [ ! -d "funasr_env" ]; then
    python3 -m venv funasr_env
fi

# 激活虚拟环境
source funasr_env/bin/activate

# 6. 升级pip
echo "⬆️ 升级pip..."
pip install --upgrade pip setuptools wheel

# 7. 安装PyTorch
echo "🔥 安装PyTorch..."
if [ "$DEVICE_TYPE" = "cuda" ]; then
    # GPU版本
    pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
else
    # CPU版本
    pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu
fi

# 验证PyTorch安装
echo "🔍 验证PyTorch安装..."
python -c "import torch; print(f'PyTorch版本: {torch.__version__}')"
if [ "$DEVICE_TYPE" = "cuda" ]; then
    python -c "import torch; print(f'CUDA可用: {torch.cuda.is_available()}')"
    python -c "import torch; print(f'GPU数量: {torch.cuda.device_count()}')" 2>/dev/null || true
fi

# 8. 安装FunASR依赖
echo "📦 安装FunASR依赖..."

# 核心依赖
pip install funasr>=1.0.25
pip install numpy>=1.21.0 scipy>=1.7.0

# 音频处理
pip install librosa==0.10.1 soundfile==0.12.1
pip install pyannote.audio>=3.0.0

# 机器学习
pip install scikit-learn>=1.0.0

# Web服务
pip install aiohttp==3.8.6 aiohttp-cors==0.7.0 websockets==11.0.3

# 系统监控
pip install psutil>=5.8.0

# 文本处理
pip install opencc-python-reimplemented>=1.1.0

# 语音识别
pip install openai-whisper>=20230314

# 9. 设置系统限制
echo "🔒 设置系统限制..."
if [ "$EUID" -ne 0 ]; then
    echo "⚠️ 需要sudo权限设置系统限制"
    sudo bash -c 'cat >> /etc/security/limits.conf << EOF
# FunASR limits
* soft nproc 4096
* hard nproc 8192
* soft nofile 4096
* hard nofile 8192
EOF'

    sudo bash -c 'cat >> /etc/sysctl.conf << EOF
# FunASR kernel parameters
kernel.threads-max = 4096
vm.max_map_count = 262144
EOF'

    sudo sysctl -p
fi

# 10. 创建启动脚本
echo "📝 创建启动脚本..."
cat > start_funasr.sh << 'EOF'
#!/bin/bash

# 激活虚拟环境
source funasr_env/bin/activate

# 设置环境变量
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export NUMEXPR_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

# 设置资源限制
ulimit -u 1024
ulimit -n 1024
ulimit -v 8388608

echo "🚀 启动FunASR服务器..."
python runtime/python/websocket/funasr_upload_server.py \
    --host 0.0.0.0 \
    --port 10095 \
    --http_port 8080 \
    --model_type paraformer \
    --device DEVICE_TYPE \
    --ngpu 1 \
    --env local
EOF

# 替换设备类型
sed -i "s/DEVICE_TYPE/$DEVICE_TYPE/g" start_funasr.sh
chmod +x start_funasr.sh

# 11. 创建测试脚本
echo "🧪 创建测试脚本..."
cat > test_installation.py << 'EOF'
#!/usr/bin/env python3
"""测试FunASR安装是否成功"""

import sys
import importlib

def test_import(module_name, description=""):
    try:
        importlib.import_module(module_name)
        print(f"✅ {module_name} {description}")
        return True
    except ImportError as e:
        print(f"❌ {module_name} {description}: {e}")
        return False

def main():
    print("🧪 测试FunASR安装...")
    print("=" * 40)
    
    success = True
    
    # 核心依赖
    success &= test_import("torch", "PyTorch")
    success &= test_import("torchaudio", "PyTorch Audio")
    success &= test_import("numpy", "NumPy")
    success &= test_import("scipy", "SciPy")
    
    # 音频处理
    success &= test_import("librosa", "Librosa")
    success &= test_import("soundfile", "SoundFile")
    
    # Web服务
    success &= test_import("aiohttp", "aiohttp")
    success &= test_import("websockets", "WebSockets")
    
    # 系统监控
    success &= test_import("psutil", "psutil")
    
    # FunASR
    success &= test_import("funasr", "FunASR")
    
    print("=" * 40)
    
    if success:
        print("✅ 所有依赖安装成功!")
        
        # 测试PyTorch GPU支持
        try:
            import torch
            print(f"🔥 PyTorch版本: {torch.__version__}")
            if torch.cuda.is_available():
                print(f"🎮 CUDA可用: True")
                print(f"🎮 GPU数量: {torch.cuda.device_count()}")
                for i in range(torch.cuda.device_count()):
                    print(f"🎮 GPU {i}: {torch.cuda.get_device_name(i)}")
            else:
                print("💻 CUDA不可用，将使用CPU模式")
        except Exception as e:
            print(f"⚠️ PyTorch测试失败: {e}")
        
        return 0
    else:
        print("❌ 部分依赖安装失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

chmod +x test_installation.py

# 12. 运行测试
echo "🧪 运行安装测试..."
python test_installation.py

# 13. 完成安装
echo ""
echo "🎉 安装完成!"
echo "=========================================="
echo "📋 安装总结:"
echo "   - Python虚拟环境: funasr_env/"
echo "   - 设备类型: $DEVICE_TYPE"
echo "   - 启动脚本: start_funasr.sh"
echo "   - 测试脚本: test_installation.py"
echo ""
echo "🚀 启动服务器:"
echo "   ./start_funasr.sh"
echo ""
echo "🌐 访问地址:"
echo "   http://localhost:8080"
echo ""
echo "📚 更多信息请查看: LINUX_GPU_INSTALLATION.md"
echo "==========================================" 