#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版本：修复CAM++说话人识别模型线程开销问题
"""

import os
import shutil
from datetime import datetime

def backup_file(file_path):
    """备份原文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ 已备份原文件到: {backup_path}")
    return backup_path

def fix_cam_plus_threading():
    """修复CAM++说话人识别模型的线程问题"""
    
    server_file = "runtime/python/websocket/funasr_upload_server.py"
    
    if not os.path.exists(server_file):
        print(f"❌ 文件不存在: {server_file}")
        return False
    
    # 备份原文件
    backup_file(server_file)
    
    # 读取文件内容
    with open(server_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在文件开头添加全局线程控制
    thread_control_imports = '''import os
import torch

# 🔧 全局线程控制设置
def set_single_thread_mode():
    """设置单线程模式"""
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['MKL_NUM_THREADS'] = '1'
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
    os.environ['NUMEXPR_NUM_THREADS'] = '1'
    os.environ['BLIS_NUM_THREADS'] = '1'
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

# 在导入后立即设置线程限制
set_single_thread_mode()

'''
    
    # 检查是否已经添加过这个修复
    if "set_single_thread_mode" not in content:
        # 在第一个import后添加线程控制
        import_pos = content.find("import")
        if import_pos != -1:
            # 找到第一行import的结束位置
            end_pos = content.find("\n", import_pos)
            content = content[:end_pos+1] + thread_control_imports + content[end_pos+1:]
            print("✅ 已添加全局线程控制")
        else:
            print("⚠️ 无法找到合适的位置添加线程控制")
    
    # 在detect_speakers_with_voice_print函数开始处添加线程限制
    function_pattern = "def detect_speakers_with_voice_print("
    if function_pattern in content:
        # 在函数开始处添加线程控制调用
        func_start = content.find(function_pattern)
        if func_start != -1:
            # 找到函数体开始的位置
            func_body_start = content.find(":", func_start)
            if func_body_start != -1:
                next_line = content.find("\n", func_body_start) + 1
                # 添加线程控制调用
                thread_call = '''    # 🔧 强制设置单线程模式
    set_single_thread_mode()
    print("🔧 CAM++模型使用单线程模式")
    
'''
                content = content[:next_line] + thread_call + content[next_line:]
                print("✅ 已在CAM++函数中添加线程控制")
    
    # 写入修改后的内容
    with open(server_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 已修复CAM++说话人识别模型线程问题")
    return True

def main():
    """主函数"""
    print("🔧 开始修复CAM++说话人识别模型线程问题...")
    print("=" * 60)
    
    if fix_cam_plus_threading():
        print("=" * 60)
        print("✅ 修复完成！")
        print()
        print("📝 修复内容:")
        print("  1. 添加全局线程控制函数")
        print("  2. 在程序启动时设置单线程模式")
        print("  3. 在CAM++函数中强制单线程")
        print()
        print("🚀 现在可以重启FunASR服务器")
    else:
        print("❌ 修复失败")

if __name__ == "__main__":
    main() 