#!/usr/bin/env python3
"""
FunASR 优化启动脚本
应用所有性能优化设置，包括GPU优化、动态并发控制等
"""

import os
import sys
import subprocess
import argparse
import psutil

def check_system_requirements():
    """检查系统要求"""
    print("🔍 检查系统要求...")
    
    # 检查CPU核心数
    cpu_count = os.cpu_count()
    print(f"💻 CPU核心数: {cpu_count}")
    
    # 检查内存
    memory = psutil.virtual_memory()
    memory_gb = memory.total / (1024**3)
    print(f"🧠 总内存: {memory_gb:.1f}GB")
    
    # 检查GPU
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            print(f"🎮 检测到GPU: {gpu_count}个")
            for i in range(gpu_count):
                gpu_name = torch.cuda.get_device_name(i)
                gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                print(f"   GPU {i}: {gpu_name} ({gpu_memory:.1f}GB)")
        else:
            print("⚠️ 未检测到可用GPU，将使用CPU模式")
    except ImportError:
        print("⚠️ PyTorch未安装，无法检测GPU")
    
    # 检查磁盘空间
    disk = psutil.disk_usage('.')
    disk_free_gb = disk.free / (1024**3)
    print(f"💾 可用磁盘空间: {disk_free_gb:.1f}GB")
    
    return {
        'cpu_count': cpu_count,
        'memory_gb': memory_gb,
        'disk_free_gb': disk_free_gb
    }

def get_optimal_settings(system_info):
    """根据系统配置获取最优设置"""
    print("\n🔧 计算最优配置...")
    
    cpu_count = system_info['cpu_count']
    memory_gb = system_info['memory_gb']
    
    # 检测GPU
    device = "cpu"
    ngpu = 0
    
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda"
            ngpu = torch.cuda.device_count()
    except ImportError:
        pass
    
    # 根据设备类型和资源计算最优设置
    if device == "cuda":
        # GPU环境优化设置
        if ngpu >= 2:
            # 多GPU环境
            optimal_workers = min(cpu_count * 2, 20)
            batch_size = 4
        else:
            # 单GPU环境
            optimal_workers = min(cpu_count, 16)
            batch_size = 2 if memory_gb >= 16 else 1
    else:
        # CPU环境设置
        optimal_workers = min(cpu_count, 12)
        batch_size = 1
    
    # 内存限制调整
    if memory_gb < 8:
        optimal_workers = min(optimal_workers, 4)
        batch_size = 1
    elif memory_gb < 16:
        optimal_workers = min(optimal_workers, 8)
    
    settings = {
        'device': device,
        'ngpu': ngpu,
        'workers': optimal_workers,
        'batch_size': batch_size,
        'host': '0.0.0.0',
        'port': 8080,
        'http_port': 8080
    }
    
    print(f"📊 推荐配置:")
    print(f"   设备类型: {device}")
    print(f"   GPU数量: {ngpu}")
    print(f"   线程池大小: {optimal_workers}")
    print(f"   批处理大小: {batch_size}")
    
    return settings

def install_dependencies():
    """安装必要依赖"""
    print("\n📦 检查并安装依赖...")
    
    required_packages = [
        'psutil',
        'aiohttp',
        'websockets',
        'numpy',
        'librosa',
        'soundfile'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} 已安装")
        except ImportError:
            print(f"📦 安装 {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

def create_optimized_config(settings):
    """创建优化配置文件"""
    config_content = f"""# FunASR 优化配置
# 自动生成于系统检测

# 设备配置
DEVICE = "{settings['device']}"
NGPU = {settings['ngpu']}

# 并发配置
MAX_WORKERS = {settings['workers']}
BATCH_SIZE = {settings['batch_size']}

# 网络配置
HOST = "{settings['host']}"
PORT = {settings['port']}
HTTP_PORT = {settings['http_port']}"

# 性能优化配置
ENABLE_GPU_OPTIMIZATION = {settings['device'] == 'cuda'}
ENABLE_DYNAMIC_CONCURRENCY = True
ENABLE_LOAD_BALANCING = True

# 监控配置
ENABLE_SYSTEM_MONITOR = True
MONITOR_INTERVAL = 30  # 秒
"""
    
    with open('optimized_config.py', 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print("✅ 优化配置文件已创建: optimized_config.py")

def start_server(settings, model_type="paraformer"):
    """启动优化的服务器"""
    print(f"\n🚀 启动FunASR优化服务器...")
    
    cmd = [
        sys.executable,
        "runtime/python/websocket/funasr_upload_server.py",
        "--model-type", model_type,
        "--device", settings['device'],
        "--ngpu", str(settings['ngpu']),
        "--host", settings['host'],
        "--port", str(settings['port']),
        "--http-port", str(settings['http_port'])
    ]
    
    print(f"📝 执行命令: {' '.join(cmd)}")
    print(f"🌐 服务地址: http://{settings['host']}:{settings['http_port']}")
    print(f"📊 系统监控: http://{settings['host']}:{settings['http_port']}/system_monitor")
    print(f"📈 性能报告: http://{settings['host']}:{settings['http_port']}/performance_report")
    print("\n按 Ctrl+C 停止服务器")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")

def main():
    parser = argparse.ArgumentParser(description='FunASR 优化启动脚本')
    parser.add_argument('--model-type', default='paraformer', 
                       choices=['paraformer', 'whisper', 'conformer'],
                       help='模型类型')
    parser.add_argument('--skip-check', action='store_true',
                       help='跳过系统检查')
    parser.add_argument('--port', type=int, default=8080,
                       help='服务端口')
    parser.add_argument('--host', default='0.0.0.0',
                       help='服务主机')
    
    args = parser.parse_args()
    
    print("🌟 FunASR 性能优化启动器")
    print("=" * 50)
    
    if not args.skip_check:
        # 检查系统要求
        system_info = check_system_requirements()
        
        # 安装依赖
        install_dependencies()
        
        # 获取最优设置
        settings = get_optimal_settings(system_info)
        
        # 应用用户指定的设置
        settings['host'] = args.host
        settings['port'] = args.port
        settings['http_port'] = args.port
        
        # 创建配置文件
        create_optimized_config(settings)
    else:
        print("⚠️ 跳过系统检查，使用默认设置")
        settings = {
            'device': 'cpu',
            'ngpu': 0,
            'workers': 4,
            'batch_size': 1,
            'host': args.host,
            'port': args.port,
            'http_port': args.port
        }
    
    # 启动服务器
    start_server(settings, args.model_type)

if __name__ == "__main__":
    main() 