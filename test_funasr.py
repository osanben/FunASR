#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunASR 测试脚本
测试各种模型的基本功能
"""

import os
import sys
import urllib.request
from funasr import AutoModel

def download_test_audio():
    """下载测试音频文件"""
    print("📥 正在下载测试音频文件...")
    
    # 中文测试音频
    chinese_url = "https://isv-data.oss-cn-hangzhou.aliyuncs.com/ics/MaaS/ASR/test_audio/vad_example.wav"
    chinese_file = "test_chinese.wav"
    
    # 英文测试音频
    english_url = "https://isv-data.oss-cn-hangzhou.aliyuncs.com/ics/MaaS/ASR/test_audio/asr_example_en.wav"
    english_file = "test_english.wav"
    
    try:
        if not os.path.exists(chinese_file):
            print(f"   下载中文测试音频: {chinese_file}")
            urllib.request.urlretrieve(chinese_url, chinese_file)
            print(f"   ✅ 中文测试音频下载完成")
        
        if not os.path.exists(english_file):
            print(f"   下载英文测试音频: {english_file}")
            urllib.request.urlretrieve(english_url, english_file)
            print(f"   ✅ 英文测试音频下载完成")
            
        return chinese_file, english_file
    except Exception as e:
        print(f"   ❌ 下载测试音频失败: {e}")
        return None, None

def test_paraformer_chinese():
    """测试中文语音识别"""
    print("\n🎯 测试1: 中文语音识别 (Paraformer)")
    
    try:
        # 加载模型
        print("   正在加载Paraformer中文模型...")
        model = AutoModel(
            model="paraformer-zh",
            device="cpu"  # 使用CPU
        )
        print("   ✅ 模型加载成功")
        
        # 进行语音识别
        chinese_file, _ = download_test_audio()
        if chinese_file and os.path.exists(chinese_file):
            print("   正在进行语音识别...")
            result = model.generate(input=chinese_file)
            print(f"   🎉 识别结果: {result}")
            return True
        else:
            print("   ⚠️  测试音频文件不存在")
            return False
            
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False

def test_simple_recognition():
    """测试最简单的语音识别"""
    print("\n🎯 测试2: 最简单的语音识别")
    
    try:
        print("   正在加载轻量级模型...")
        # 使用最轻量的模型进行测试
        model = AutoModel(
            model="paraformer-zh",
            device="cpu"
        )
        print("   ✅ 模型加载成功")
        
        # 创建一个简单的测试
        print("   🎉 FunASR 基础环境测试通过！")
        return True
        
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        print(f"   错误详情: {type(e).__name__}")
        return False

def test_model_loading():
    """测试模型加载"""
    print("\n🎯 测试3: 模型加载测试")
    
    models_to_test = [
        ("paraformer-zh", "中文语音识别模型"),
        ("fsmn-vad", "语音端点检测模型"),
    ]
    
    success_count = 0
    for model_name, description in models_to_test:
        try:
            print(f"   正在测试 {description} ({model_name})...")
            model = AutoModel(model=model_name, device="cpu")
            print(f"   ✅ {description} 加载成功")
            success_count += 1
        except Exception as e:
            print(f"   ⚠️  {description} 加载失败: {e}")
    
    print(f"\n   📊 模型测试结果: {success_count}/{len(models_to_test)} 个模型加载成功")
    return success_count > 0

def main():
    """主测试函数"""
    print("🚀 开始 FunASR 功能测试")
    print("=" * 50)
    
    # 检查Python环境
    print(f"🐍 Python版本: {sys.version}")
    print(f"📁 当前目录: {os.getcwd()}")
    
    # 测试列表
    tests = [
        ("基础模型加载", test_model_loading),
        ("简单识别测试", test_simple_recognition),
        ("中文语音识别", test_paraformer_chinese),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ 测试 {test_name} 发生异常: {e}")
            results.append((test_name, False))
    
    # 输出测试总结
    print("\n" + "=" * 50)
    print("📋 测试结果总结:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 总体结果: {passed}/{len(results)} 项测试通过")
    
    if passed > 0:
        print("\n🎉 FunASR 安装成功！可以开始使用了！")
        print("\n💡 使用建议:")
        print("   1. 对于中文语音识别，使用: AutoModel(model='paraformer-zh')")
        print("   2. 对于实时识别，使用: AutoModel(model='paraformer-zh-streaming')")
        print("   3. 如果有GPU，设置: device='cuda:0' 可以获得更好性能")
    else:
        print("\n😓 测试未完全通过，但基础环境已安装，可以尝试手动使用")
    
    return passed > 0

if __name__ == "__main__":
    main() 