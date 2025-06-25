#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试说话人注册API
"""

import requests
import os
import sys

def test_register_speaker(audio_file_path, speaker_name="测试说话人"):
    """测试说话人注册接口"""
    
    if not os.path.exists(audio_file_path):
        print(f"❌ 音频文件不存在: {audio_file_path}")
        return False
    
    print(f"🧪 测试说话人注册API")
    print(f"📁 音频文件: {audio_file_path}")
    print(f"👤 说话人姓名: {speaker_name}")
    
    # 准备请求数据
    url = "http://127.0.0.1:8080/register_speaker"
    
    try:
        with open(audio_file_path, 'rb') as f:
            files = {
                'speaker_audio': (os.path.basename(audio_file_path), f, 'audio/m4a')
            }
            data = {
                'speaker_name': speaker_name
            }
            
            print(f"🚀 发送请求到: {url}")
            response = requests.post(url, files=files, data=data, timeout=60)
            
            print(f"📊 响应状态码: {response.status_code}")
            print(f"📄 响应内容: {response.text}")
            
            if response.status_code == 200:
                print("✅ 注册成功!")
                return True
            else:
                print(f"❌ 注册失败: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_list_speakers():
    """测试获取说话人列表"""
    print(f"\n🧪 测试获取说话人列表")
    
    url = "http://127.0.0.1:8080/list_speakers"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"📊 响应状态码: {response.status_code}")
        print(f"📄 响应内容: {response.text}")
        
        if response.status_code == 200:
            print("✅ 获取列表成功!")
            return True
        else:
            print(f"❌ 获取列表失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("❌ 使用方法: python test_register_api.py <音频文件路径>")
        print("📝 例如: python test_register_api.py /Users/csdn/Desktop/王占分-音色.m4a")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    print("🔧 说话人注册API测试工具")
    print("=" * 50)
    
    # 测试注册
    success = test_register_speaker(audio_file, "王占分")
    
    # 测试获取列表
    test_list_speakers()
    
    if success:
        print("\n🎉 测试完成!")
    else:
        print("\n❌ 测试失败!")

if __name__ == "__main__":
    main() 