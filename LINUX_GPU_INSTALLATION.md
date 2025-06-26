# Linux GPU环境FunASR安装指南

## 系统要求

- Ubuntu 18.04+ / CentOS 7+ / 其他Linux发行版
- Python 3.8-3.11
- NVIDIA GPU (支持CUDA 11.0+)
- 至少8GB内存
- 至少20GB磁盘空间

## 1. 系统准备

### 更新系统
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 安装系统依赖
```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv git wget curl
sudo apt install -y build-essential cmake pkg-config
sudo apt install -y libsndfile1 libsndfile1-dev
sudo apt install -y ffmpeg

# CentOS/RHEL
sudo yum install -y python3 python3-pip git wget curl
sudo yum groupinstall -y "Development Tools"
sudo yum install -y cmake pkgconfig
sudo yum install -y libsndfile libsndfile-devel
sudo yum install -y ffmpeg
```

## 2. NVIDIA驱动和CUDA安装

### 检查GPU
```bash
lspci | grep -i nvidia
```

### 安装NVIDIA驱动
```bash
# Ubuntu (自动安装推荐驱动)
sudo ubuntu-drivers autoinstall

# 或手动安装
sudo apt install -y nvidia-driver-470
```

### 安装CUDA Toolkit
```bash
# 下载CUDA 11.8 (推荐版本)
wget https://developer.download.nvidia.com/compute/cuda/11.8.0/local_installers/cuda_11.8.0_520.61.05_linux.run
sudo sh cuda_11.8.0_520.61.05_linux.run

# 添加环境变量
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

### 验证安装
```bash
nvidia-smi
nvcc --version
```

## 3. Python环境设置

### 创建虚拟环境
```bash
python3 -m venv funasr_env
source funasr_env/bin/activate
```

### 升级pip
```bash
pip install --upgrade pip setuptools wheel
```

## 4. 安装PyTorch (GPU版本)

```bash
# CUDA 11.8版本
pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118

# 验证PyTorch GPU支持
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU count: {torch.cuda.device_count()}')"
```

## 5. 安装FunASR依赖

### 使用完整依赖文件
```bash
# 克隆项目
git clone <your-funasr-repo>
cd FunASR

# 安装依赖
pip install -r requirements_complete.txt
```

### 或逐步安装
```bash
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
```

## 6. 系统优化配置

### 设置系统限制
```bash
# 编辑 /etc/security/limits.conf
sudo nano /etc/security/limits.conf

# 添加以下行
* soft nproc 4096
* hard nproc 8192
* soft nofile 4096
* hard nofile 8192
```

### 设置内核参数
```bash
# 编辑 /etc/sysctl.conf
sudo nano /etc/sysctl.conf

# 添加以下行
kernel.threads-max = 4096
vm.max_map_count = 262144

# 应用设置
sudo sysctl -p
```

## 7. 启动服务器

### 使用安全启动脚本
```bash
chmod +x start_linux_gpu_server.sh
./start_linux_gpu_server.sh
```

### 或手动启动
```bash
# 设置环境变量
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export NUMEXPR_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export CUDA_VISIBLE_DEVICES=0

# 启动服务器
python runtime/python/websocket/funasr_upload_server.py \
    --host 0.0.0.0 \
    --port 10095 \
    --http_port 8080 \
    --model_type paraformer \
    --device cuda \
    --ngpu 1 \
    --env local
```

## 8. 验证安装

### 检查服务状态
```bash
# 检查端口是否监听
netstat -tlnp | grep :8080
netstat -tlnp | grep :10095

# 检查GPU使用情况
nvidia-smi

# 测试API
curl http://localhost:8080/api/status
```

### 访问Web界面
```
http://your-server-ip:8080
```

## 9. 故障排除

### 常见问题

#### libgomp线程创建失败
```bash
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
ulimit -u 1024
```

#### CUDA内存不足
```bash
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
```

#### 模型下载失败
```bash
# 设置国内镜像
export HF_ENDPOINT=https://hf-mirror.com
export MODELSCOPE_CACHE=/path/to/cache
```

### 日志查看
```bash
# 查看系统日志
journalctl -f

# 查看GPU状态
watch -n 1 nvidia-smi

# 监控系统资源
htop
```

## 10. 性能优化

### GPU优化
```bash
# 设置GPU性能模式
sudo nvidia-smi -pm 1
sudo nvidia-smi -pl 300  # 设置功率限制
```

### 系统优化
```bash
# 禁用swap (如果内存充足)
sudo swapoff -a

# 设置CPU调度器
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

## 11. 自动启动配置

### 创建systemd服务
```bash
sudo nano /etc/systemd/system/funasr.service
```

```ini
[Unit]
Description=FunASR Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/FunASR
Environment=OMP_NUM_THREADS=2
Environment=MKL_NUM_THREADS=2
Environment=CUDA_VISIBLE_DEVICES=0
ExecStart=/path/to/FunASR/start_linux_gpu_server.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 启用服务
```bash
sudo systemctl daemon-reload
sudo systemctl enable funasr
sudo systemctl start funasr
sudo systemctl status funasr
```

## 12. 备份和维护

### 定期备份
```bash
# 备份数据库
cp funasr_data.db funasr_data.db.backup

# 备份说话人数据
tar -czf speaker_backup.tar.gz speaker_database/
```

### 清理缓存
```bash
# 清理模型缓存
rm -rf ~/.cache/modelscope/
rm -rf ~/.cache/huggingface/

# 清理临时文件
rm -rf uploads/*
rm -rf audio_segments/*
``` 