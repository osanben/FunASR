#!/usr/bin/env python3
"""
测试线程控制是否有效
"""
import os
import sys

def test_thread_control():
    """测试线程控制设置"""
    print("🧪 测试线程控制设置...")
    
    # 检查环境变量
    thread_vars = [
        'OMP_NUM_THREADS',
        'MKL_NUM_THREADS', 
        'OPENBLAS_NUM_THREADS',
        'VECLIB_MAXIMUM_THREADS',
        'NUMEXPR_NUM_THREADS',
        'BLIS_NUM_THREADS'
    ]
    
    print("📊 当前环境变量:")
    for var in thread_vars:
        value = os.environ.get(var, '未设置')
        print(f"  {var} = {value}")
    
    # 测试PyTorch线程设置
    try:
        import torch
        print(f"\n🔧 PyTorch线程数:")
        print(f"  torch.get_num_threads() = {torch.get_num_threads()}")
        print(f"  torch.get_num_interop_threads() = {torch.get_num_interop_threads()}")
    except ImportError:
        print("⚠️ PyTorch未安装")
    
    # 测试OpenMP
    try:
        import multiprocessing
        print(f"\n💻 系统信息:")
        print(f"  CPU核心数: {multiprocessing.cpu_count()}")
        print(f"  当前进程PID: {os.getpid()}")
    except:
        pass
    
    print("\n✅ 线程控制测试完成")

if __name__ == "__main__":
    test_thread_control() 