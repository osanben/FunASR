#!/usr/bin/env python3
"""
说话人相似度诊断脚本
用于分析注册音频长度对说话人识别相似度的影响
"""

import os
import sys
import numpy as np
import librosa
import json
import pickle
from pathlib import Path
import time

# 添加项目路径
sys.path.append('./runtime/python/websocket')
from speaker_manager import SpeakerManager

def analyze_audio_segments(audio_file, segments_info):
    """分析音频片段特征"""
    print(f"\n🔍 分析音频文件: {audio_file}")
    
    # 加载音频
    audio_data, sr = librosa.load(audio_file, sr=16000, dtype=np.float32)
    total_duration = len(audio_data) / sr
    
    print(f"📊 音频总时长: {total_duration:.2f}秒")
    print(f"📊 音频总长度: {len(audio_data)} 样本")
    print(f"📊 采样率: {sr}Hz")
    
    # 分析每个片段
    for i, segment in enumerate(segments_info):
        start_time = segment.get("start", 0) / 1000  # 转换为秒
        end_time = segment.get("end", 0) / 1000
        text = segment.get("text", "").strip()
        
        duration = end_time - start_time
        start_sample = int(start_time * sr)
        end_sample = int(end_time * sr)
        segment_audio = audio_data[start_sample:end_sample]
        
        print(f"\n📝 片段 {i+1}:")
        print(f"   文本: {text}")
        print(f"   时间: {start_time:.3f}s - {end_time:.3f}s")
        print(f"   时长: {duration:.3f}s")
        print(f"   样本数: {len(segment_audio)}")
        
        # 音频质量分析
        if len(segment_audio) > 0:
            energy = np.mean(segment_audio ** 2)
            rms = np.sqrt(energy)
            max_amplitude = np.max(np.abs(segment_audio))
            
            print(f"   能量: {energy:.6f}")
            print(f"   RMS: {rms:.6f}")
            print(f"   最大振幅: {max_amplitude:.6f}")
            
            # 静音检测
            silence_threshold = 0.01
            silence_ratio = np.sum(np.abs(segment_audio) < silence_threshold) / len(segment_audio)
            print(f"   静音比例: {silence_ratio:.2%}")

def test_embedding_similarity(manager, audio_file, segments_info):
    """测试不同长度音频片段的嵌入向量相似度"""
    print(f"\n🧪 测试嵌入向量相似度...")
    
    # 加载音频
    audio_data, sr = librosa.load(audio_file, sr=16000, dtype=np.float32)
    
    embeddings = []
    similarities = []
    
    # 获取注册的说话人信息
    speakers = manager.get_registered_speakers()
    if not speakers:
        print("❌ 没有注册的说话人")
        return
    
    target_speaker = speakers[0]  # 假设是第一个注册的说话人
    print(f"🎯 目标说话人: {target_speaker['name']} (时长: {target_speaker['audio_duration']:.2f}s)")
    
    # 测试每个片段
    for i, segment in enumerate(segments_info):
        start_time = segment.get("start", 0) / 1000
        end_time = segment.get("end", 0) / 1000
        text = segment.get("text", "").strip()
        
        start_sample = int(start_time * sr)
        end_sample = int(end_time * sr)
        segment_audio = audio_data[start_sample:end_sample]
        
        if len(segment_audio) > 1600:  # 至少100ms
            # 提取嵌入向量
            embedding = manager.extract_speaker_embedding(segment_audio, sr)
            
            if embedding is not None:
                embeddings.append(embedding)
                
                # 计算与注册说话人的相似度
                speaker_name, similarity, message = manager.match_speaker(segment_audio)
                similarities.append(similarity)
                
                print(f"\n📊 片段 {i+1} ({end_time-start_time:.3f}s): 相似度 {similarity:.3f}")
                print(f"   匹配结果: {speaker_name or '未匹配'}")
                print(f"   消息: {message}")
            else:
                print(f"\n❌ 片段 {i+1}: 嵌入向量提取失败")
    
    return embeddings, similarities

def test_different_audio_lengths():
    """测试不同音频长度对相似度的影响"""
    print(f"\n🔬 测试不同音频长度的影响...")
    
    # 创建测试音频片段（不同长度）
    test_lengths = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]  # 秒
    
    # 这里需要真实的音频文件来测试
    # 由于我们没有原始注册音频，这部分需要用户提供音频文件
    print("💡 建议测试步骤:")
    print("1. 准备同一个人不同长度的音频片段")
    print("2. 分别注册不同长度的音频")
    print("3. 用相同的测试音频进行识别")
    print("4. 比较相似度差异")

def analyze_speaker_database():
    """分析说话人数据库"""
    print(f"\n📂 分析说话人数据库...")
    
    db_path = Path("./speaker_database")
    if not db_path.exists():
        print("❌ 说话人数据库不存在")
        return
    
    # 读取元数据
    metadata_file = db_path / "speaker_metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        print(f"📊 已注册说话人数量: {len(metadata)}")
        
        for speaker_id, info in metadata.items():
            print(f"\n👤 说话人: {info['name']} (ID: {speaker_id})")
            print(f"   注册时间: {time.ctime(info['register_time'])}")
            print(f"   音频时长: {info['audio_duration']:.2f}秒")
            print(f"   音频文件: {info['audio_file']}")
            print(f"   嵌入向量维度: {info['embedding_dim']}")
    
    # 读取嵌入向量
    embeddings_file = db_path / "speaker_embeddings.pkl"
    if embeddings_file.exists():
        with open(embeddings_file, 'rb') as f:
            embeddings = pickle.load(f)
        
        print(f"\n🔢 嵌入向量统计:")
        for speaker_id, embedding in embeddings.items():
            print(f"   {speaker_id}: 维度={len(embedding)}, 范围=[{embedding.min():.6f}, {embedding.max():.6f}]")

def main():
    print("🔍 说话人相似度诊断工具")
    print("=" * 50)
    
    # 分析说话人数据库
    analyze_speaker_database()
    
    # 创建说话人管理器
    manager = SpeakerManager()
    
    # 模拟测试数据（基于之前的日志）
    test_segments = [
        {"start": 1070, "end": 2170, "text": "我是王王杰，"},
        {"start": 2250, "end": 3570, "text": "王杰跟本杰在说话。"},
        {"start": 3870, "end": 4015, "text": "王，"}
    ]
    
    print(f"\n📋 测试片段信息:")
    for i, seg in enumerate(test_segments):
        duration = (seg["end"] - seg["start"]) / 1000
        print(f"   片段{i+1}: {seg['text']} ({duration:.3f}s)")
    
    # 分析片段特征
    # 注意：这里需要实际的音频文件
    print(f"\n💡 诊断建议:")
    print("1. 音频长度影响:")
    print("   - 注册音频: 6.06秒 (较长)")
    print("   - 识别片段: 1.1s, 1.32s, 0.145s (较短)")
    print("   - 短片段可能包含信息不足，影响特征提取")
    
    print("\n2. 音频质量影响:")
    print("   - 录制环境差异")
    print("   - 噪音水平不同")
    print("   - 音频压缩格式")
    
    print("\n3. 说话内容影响:")
    print("   - 注册时的语音内容 vs 识别时的内容")
    print("   - 语音的音调、语速变化")
    
    print("\n4. 模型特性:")
    print("   - CamPlus模型对长音频的特征提取更稳定")
    print("   - 短片段可能导致特征不完整")
    
    print("\n🔧 改进建议:")
    print("1. 降低相似度阈值 (从0.75降到0.6-0.65)")
    print("2. 使用更长的注册音频 (10-15秒)")
    print("3. 在相同环境下录制注册和测试音频")
    print("4. 对短片段进行特殊处理或跳过")

if __name__ == "__main__":
    main() 