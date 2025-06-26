#!/usr/bin/env python3
"""
修复FunASR并发和OpenMP问题的脚本
"""
import os
import sys

def fix_openmp_environment():
    """强制设置OpenMP环境变量"""
    openmp_vars = {
        'OMP_NUM_THREADS': '1',
        'MKL_NUM_THREADS': '1', 
        'OPENBLAS_NUM_THREADS': '1',
        'NUMEXPR_NUM_THREADS': '1',
        'VECLIB_MAXIMUM_THREADS': '1',
        'BLIS_NUM_THREADS': '1',
        # 内存相关
        'MALLOC_ARENA_MAX': '2',
        'MALLOC_MMAP_THRESHOLD_': '131072',
        'MALLOC_TRIM_THRESHOLD_': '131072',
        # OpenMP特定设置
        'OMP_WAIT_POLICY': 'PASSIVE',
        'OMP_PROC_BIND': 'FALSE',  # 不绑定CPU
        'OMP_DYNAMIC': 'TRUE',     # 允许动态调整
    }
    
    print("🔧 设置OpenMP环境变量...")
    for var, value in openmp_vars.items():
        os.environ[var] = value
        print(f"   {var}={value}")
    
    return openmp_vars

def patch_funasr_concurrency():
    """运行时patch并发控制"""
    try:
        # 导入并修改funasr_upload_server的并发控制
        import runtime.python.websocket.funasr_upload_server as server
        
        # 强制设置最大并发数为1（最保守）
        if hasattr(server, 'concurrency_controller'):
            server.concurrency_controller.max_workers = 1
            print("🚦 强制设置并发数为1")
        
        # 强制设置线程池大小
        if hasattr(server, 'executor'):
            server.executor._max_workers = 2
            print("🧵 强制设置线程池大小为2")
            
    except Exception as e:
        print(f"⚠️ 运行时patch失败: {e}")

def monitor_resources():
    """监控系统资源"""
    import psutil
    import threading
    
    process = psutil.Process()
    
    print(f"📊 系统状态:")
    print(f"   线程数: {process.num_threads()}")
    print(f"   内存使用: {process.memory_info().rss / 1024**2:.1f}MB")
    print(f"   活跃线程: {threading.active_count()}")
    
    # 检查OpenMP环境变量
    print(f"📊 OpenMP配置:")
    for var in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS']:
        value = os.environ.get(var, 'NOT_SET')
        print(f"   {var}={value}")

if __name__ == "__main__":
    print("🚀 开始修复FunASR并发问题...")
    
    # 1. 设置环境变量
    fix_openmp_environment()
    
    # 2. 监控资源
    monitor_resources()
    
    # 3. 启动服务（如果提供了启动参数）
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        print("🌟 启动FunASR服务...")
        import subprocess
        cmd = [
            "python", "runtime/python/websocket/funasr_upload_server.py",
            "--host", "0.0.0.0",
            "--port", "10095", 
            "--http_port", "8080",
            "--model_type", "paraformer",
            "--device", "cuda",
            "--ngpu", "1",
            "--ncpu", "2",  # 强制限制为2
            "--env", "test"
        ]
        subprocess.run(cmd)
    else:
        print("✅ 环境变量设置完成，请手动启动服务")
        print("💡 使用: python fix_concurrency_issue.py start") 