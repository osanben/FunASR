#!/usr/bin/env python3
"""
安全的GPU服务器启动脚本
包含资源限制和错误处理，防止系统资源耗尽
"""

import os
import sys
import signal
import subprocess
import time
import resource

def set_resource_limits():
    """设置系统资源限制"""
    try:
        # 限制进程数量
        resource.setrlimit(resource.RLIMIT_NPROC, (1024, 2048))
        print("✅ 已设置进程数量限制: 1024")
        
        # 限制内存使用 (8GB)
        memory_limit = 8 * 1024 * 1024 * 1024  # 8GB
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
        print("✅ 已设置内存使用限制: 8GB")
        
        # 限制文件描述符数量
        resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 2048))
        print("✅ 已设置文件描述符限制: 1024")
        
    except Exception as e:
        print(f"⚠️ 设置资源限制失败: {e}")

def set_environment_variables():
    """设置环境变量"""
    env_vars = {
        'OMP_NUM_THREADS': '2',
        'MKL_NUM_THREADS': '2', 
        'NUMEXPR_NUM_THREADS': '2',
        'OPENBLAS_NUM_THREADS': '2',
        'CUDA_VISIBLE_DEVICES': '0',  # 只使用第一个GPU
        'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:128',  # 限制CUDA内存分配
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"🔧 设置环境变量: {key}={value}")

def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n🛑 收到信号 {signum}，正在安全关闭服务器...")
    sys.exit(0)

def main():
    print("🚀 启动安全GPU服务器")
    print("=" * 50)
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 设置资源限制
    print("🔒 设置系统资源限制...")
    set_resource_limits()
    
    # 设置环境变量
    print("🌍 设置环境变量...")
    set_environment_variables()
    
    # 构建启动命令
    cmd = [
        sys.executable,
        "runtime/python/websocket/funasr_upload_server.py",
        "--host", "0.0.0.0",
        "--port", "10095", 
        "--http_port", "8080",
        "--model_type", "paraformer",
        "--device", "cuda",
        "--ngpu", "1",
        "--env", "test"
    ]
    
    print("📋 启动命令:")
    print(" ".join(cmd))
    print("=" * 50)
    
    try:
        # 启动服务器
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        print("🎯 服务器正在启动...")
        
        # 实时输出日志
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line.rstrip())
                
                # 检查是否启动成功
                if "服务器启动完成" in line or "Server started" in line:
                    print("✅ 服务器启动成功!")
                
                # 检查是否有错误
                if "libgomp" in line.lower() or "segment" in line.lower():
                    print("❌ 检测到资源问题，正在重启...")
                    process.terminate()
                    time.sleep(2)
                    process.kill()
                    return False
        
        process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 用户中断，正在关闭服务器...")
        if 'process' in locals():
            process.terminate()
            process.wait()
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("❌ 服务器启动失败")
        sys.exit(1)
    else:
        print("✅ 服务器正常退出") 