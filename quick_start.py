#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunASR 快速开始脚本
最简单的使用方式
"""

from funasr import AutoModel
import sys
import os

def quick_recognition(audio_file):
    """快速语音识别"""
    print(f"🎤 正在识别音频文件: {audio_file}")
    
    try:
        # 加载中文语音识别模型
        model = AutoModel(
            model="paraformer-zh",
            device="cpu"  # 如果有GPU，可以改为 "cuda:0"
        )
        
        # 进行语音识别
        result = model.generate(input=audio_file)
        
        # 输出结果
        print("📝 识别结果:")
        print("-" * 50)
        print(result[0]['text'])
        print("-" * 50)
        
        return result[0]['text']
        
    except Exception as e:
        print(f"❌ 识别失败: {e}")
        return None

def main():
    """主函数"""
    print("🚀 FunASR 快速开始")
    print("=" * 40)
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        if os.path.exists(audio_file):
            quick_recognition(audio_file)
        else:
            print(f"❌ 音频文件不存在: {audio_file}")
    else:
        print("💡 使用方法:")
        print("   python3 quick_start.py 音频文件路径")
        print("\n📝 示例:")
        print("   python3 quick_start.py test_chinese.wav")
        print("   python3 quick_start.py your_audio.mp3")
        
        # 检查是否有测试文件
        test_files = ["test_chinese.wav", "demo_chinese.wav"]
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"\n🎯 发现测试文件: {test_file}")
                response = input("是否使用此文件进行测试? (y/n): ")
                if response.lower() in ['y', 'yes', '是']:
                    quick_recognition(test_file)
                break

if __name__ == "__main__":
    main() 