#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

def test_realtime_files():
    """测试实时录音相关文件是否存在"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    files_to_check = [
        'realtime_demo.html',
        'recorder-core.js', 
        'pcm.js'
    ]
    
    print("🔍 检查实时录音相关文件...")
    print(f"📁 当前目录: {current_dir}")
    
    all_exist = True
    for filename in files_to_check:
        filepath = os.path.join(current_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"✅ {filename} - 存在 ({size} 字节)")
        else:
            print(f"❌ {filename} - 不存在")
            all_exist = False
    
    if all_exist:
        print("\n🎉 所有文件都存在，实时录音功能应该可以正常工作！")
        print("🌐 启动服务后访问: http://your-server:8080/realtime")
    else:
        print("\n⚠️ 有文件缺失，请检查文件完整性")
    
    return all_exist

if __name__ == "__main__":
    test_realtime_files() 