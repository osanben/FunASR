#!/bin/zsh

# FunASR服务器启动脚本
# 确保使用正确的conda环境

echo "🔧 FunASR服务器启动脚本"
echo "=========================="

# 设置环境变量
export SHELL=/bin/zsh
export CONDA_DEFAULT_ENV=funasr

# 检查conda是否可用
if ! command -v conda &> /dev/null; then
    echo "❌ conda命令未找到，请确保conda已安装并在PATH中"
    exit 1
fi

# 初始化conda（如果需要）
if [[ -f ~/.zshrc ]]; then
    source ~/.zshrc
fi

# 激活funasr环境
echo "🔄 激活funasr conda环境..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate funasr

# 检查环境
echo "📊 当前环境检查:"
echo "   Shell: $SHELL"
echo "   Conda环境: $(conda info --envs | grep '*' | awk '{print $1}')"
echo "   Python路径: $(which python)"
echo "   Python版本: $(python --version)"

# 切换到项目目录
cd /Users/csdn/github_projects/FunASR/runtime/python/websocket

# 检查必要文件
if [[ ! -f "funasr_upload_server.py" ]]; then
    echo "❌ 未找到funasr_upload_server.py文件"
    exit 1
fi

if [[ ! -f "speaker_manager_debug.py" ]]; then
    echo "❌ 未找到speaker_manager_debug.py文件"
    exit 1
fi

# 启动服务器
echo "🚀 启动FunASR服务器..."
python funasr_upload_server.py --host 0.0.0.0 --http_port 8080 --port 10096 --model_type paraformer --ngpu 0 --env local 