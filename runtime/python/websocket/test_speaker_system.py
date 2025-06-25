#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
说话人管理系统测试脚本
用于验证说话人注册、匹配等功能
"""

import os
import sys
import numpy as np
import librosa
from speaker_manager import SpeakerManager

def create_test_audio(duration=3.0, frequency=440, sample_rate=16000):
    """创建测试音频数据"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    # 创建不同频率的正弦波作为不同"说话人"的特征
    audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)
    # 添加一些噪声使其更真实
    noise = np.random.normal(0, 0.1, len(audio)).astype(np.float32)
    audio = audio + noise
    # 归一化
    audio = audio / np.max(np.abs(audio))
    return audio

def test_speaker_manager():
    """测试说话人管理器功能"""
    print("🧪 开始测试说话人管理系统...")
    
    # 初始化管理器
    speaker_manager = SpeakerManager(database_dir="./test_speaker_db")
    
    # 创建测试音频文件
    test_dir = "./test_audio_samples"
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建不同"说话人"的音频样本
    speakers_data = {
        "张三": create_test_audio(duration=3.0, frequency=440),  # A4音符
        "李四": create_test_audio(duration=3.0, frequency=523),  # C5音符
        "王五": create_test_audio(duration=3.0, frequency=659),  # E5音符
    }
    
    # 保存测试音频文件
    test_files = {}
    for name, audio_data in speakers_data.items():
        filename = os.path.join(test_dir, f"{name}_sample.wav")
        librosa.output.write_wav(filename, audio_data, 16000)
        test_files[name] = filename
        print(f"✅ 创建测试音频: {filename}")
    
    try:
        # 测试1: 注册说话人
        print("\n📝 测试1: 注册说话人")
        for name, filepath in test_files.items():
            success, message = speaker_manager.register_speaker(name, filepath)
            if success:
                print(f"✅ {name} 注册成功: {message}")
            else:
                print(f"❌ {name} 注册失败: {message}")
        
        # 测试2: 查看已注册说话人
        print("\n📋 测试2: 查看已注册说话人")
        speakers = speaker_manager.get_registered_speakers()
        for speaker in speakers:
            print(f"👤 {speaker['name']} (ID: {speaker['id']}, 时长: {speaker['audio_duration']:.1f}秒)")
        
        # 测试3: 说话人匹配
        print("\n🔍 测试3: 说话人匹配")
        for name, audio_data in speakers_data.items():
            # 使用相同的音频数据进行匹配测试
            matched_name, similarity, info = speaker_manager.match_speaker(audio_data)
            print(f"🎯 测试音频 {name}: 匹配到 {matched_name}, 相似度: {similarity:.3f}, 信息: {info}")
        
        # 测试4: 使用不同的音频进行匹配
        print("\n🔍 测试4: 使用变化的音频进行匹配")
        for name, audio_data in speakers_data.items():
            # 添加噪声和变化
            modified_audio = audio_data * 0.8 + np.random.normal(0, 0.05, len(audio_data)).astype(np.float32)
            matched_name, similarity, info = speaker_manager.match_speaker(modified_audio)
            print(f"🎯 变化音频 {name}: 匹配到 {matched_name}, 相似度: {similarity:.3f}, 信息: {info}")
        
        # 测试5: 相似度阈值调整
        print("\n⚙️ 测试5: 相似度阈值调整")
        old_threshold = speaker_manager.similarity_threshold
        speaker_manager.update_similarity_threshold(0.9)
        print(f"🔧 阈值从 {old_threshold} 调整为 {speaker_manager.similarity_threshold}")
        
        # 再次测试匹配
        for name, audio_data in speakers_data.items():
            matched_name, similarity, info = speaker_manager.match_speaker(audio_data)
            print(f"🎯 高阈值测试 {name}: 匹配到 {matched_name}, 相似度: {similarity:.3f}, 信息: {info}")
        
        # 恢复阈值
        speaker_manager.update_similarity_threshold(old_threshold)
        
        print("\n✅ 所有测试完成!")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理测试文件
        print("\n🧹 清理测试文件...")
        try:
            import shutil
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
                print("✅ 测试音频文件已清理")
            
            if os.path.exists("./test_speaker_db"):
                shutil.rmtree("./test_speaker_db")
                print("✅ 测试数据库已清理")
        except Exception as e:
            print(f"⚠️ 清理文件时出现错误: {e}")

def test_with_funasr():
    """使用FunASR模型进行测试"""
    print("\n🤖 测试与FunASR模型的集成...")
    
    try:
        from funasr import AutoModel
        
        # 加载说话人识别模型
        spk_model = AutoModel(
            model="iic/speech_campplus_sv_zh-cn_16k-common",
            device="cpu",
            disable_pbar=True,
            disable_log=True,
            disable_update=True
        )
        
        speaker_manager = SpeakerManager(database_dir="./test_speaker_db_funasr")
        
        # 创建测试音频
        test_audio = create_test_audio(duration=2.0, frequency=440)
        
        # 测试嵌入向量提取
        embedding = speaker_manager.extract_speaker_embedding(test_audio, model_asr=spk_model)
        
        if embedding is not None:
            print(f"✅ 成功提取嵌入向量，维度: {len(embedding)}")
            print(f"📊 嵌入向量范围: [{embedding.min():.3f}, {embedding.max():.3f}]")
        else:
            print("❌ 嵌入向量提取失败")
        
        # 清理
        import shutil
        if os.path.exists("./test_speaker_db_funasr"):
            shutil.rmtree("./test_speaker_db_funasr")
            
    except ImportError:
        print("⚠️ FunASR未安装，跳过FunASR集成测试")
    except Exception as e:
        print(f"❌ FunASR测试失败: {e}")

if __name__ == "__main__":
    print("🎯 说话人管理系统测试")
    print("=" * 50)
    
    # 基础功能测试
    test_speaker_manager()
    
    # FunASR集成测试
    test_with_funasr()
    
    print("\n🎉 测试完成!") 