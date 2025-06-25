#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
说话人音频文件调试工具
用于检查音频文件是否可以正常处理和提取声纹特征
"""

import os
import sys
import numpy as np
import librosa
import traceback

def check_audio_file(file_path):
    """检查音频文件基本信息"""
    print(f"🔍 检查音频文件: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    file_size = os.path.getsize(file_path)
    print(f"📊 文件大小: {file_size / 1024 / 1024:.2f} MB")
    
    # 检查文件扩展名
    ext = os.path.splitext(file_path)[1].lower()
    print(f"📁 文件扩展名: {ext}")
    
    return True

def load_audio_with_librosa(file_path):
    """使用librosa加载音频"""
    print("\n🎵 使用librosa加载音频...")
    
    try:
        # 加载音频
        audio_data, sample_rate = librosa.load(file_path, sr=16000, dtype=np.float32)
        
        print(f"✅ 加载成功!")
        print(f"📊 采样率: {sample_rate} Hz")
        print(f"📊 音频长度: {len(audio_data)} 采样点")
        print(f"📊 时长: {len(audio_data) / sample_rate:.2f} 秒")
        print(f"📊 数据类型: {audio_data.dtype}")
        print(f"📊 数据范围: [{audio_data.min():.6f}, {audio_data.max():.6f}]")
        print(f"📊 均值: {audio_data.mean():.6f}")
        print(f"📊 标准差: {audio_data.std():.6f}")
        
        # 检查是否有静音
        silence_threshold = 0.001
        non_silence_samples = np.sum(np.abs(audio_data) > silence_threshold)
        silence_ratio = 1 - (non_silence_samples / len(audio_data))
        print(f"📊 静音比例: {silence_ratio:.2%}")
        
        return audio_data, sample_rate
        
    except Exception as e:
        print(f"❌ librosa加载失败: {e}")
        traceback.print_exc()
        return None, None

def test_speaker_manager_basic():
    """测试说话人管理器基本功能"""
    print("\n🧪 测试说话人管理器基本功能...")
    
    try:
        from speaker_manager import SpeakerManager
        
        # 创建测试管理器
        manager = SpeakerManager(database_dir="./debug_speaker_db")
        print("✅ 说话人管理器创建成功")
        
        return manager
        
    except Exception as e:
        print(f"❌ 说话人管理器创建失败: {e}")
        traceback.print_exc()
        return None

def test_funasr_model():
    """测试FunASR模型加载"""
    print("\n🤖 测试FunASR模型加载...")
    
    try:
        from funasr import AutoModel
        
        print("📦 加载说话人识别模型...")
        spk_model = AutoModel(
            model="iic/speech_campplus_sv_zh-cn_16k-common",
            device="cpu",
            disable_pbar=True,
            disable_log=True,
            disable_update=True
        )
        print("✅ FunASR说话人模型加载成功")
        
        return spk_model
        
    except Exception as e:
        print(f"❌ FunASR模型加载失败: {e}")
        traceback.print_exc()
        return None

def test_embedding_extraction(manager, model, audio_data):
    """测试嵌入向量提取"""
    print("\n🔬 测试嵌入向量提取...")
    
    if manager is None or audio_data is None:
        print("⚠️ 跳过测试：管理器或音频数据为空")
        return None
    
    try:
        # 方法1：使用说话人管理器提取
        print("🔧 方法1：使用SpeakerManager提取...")
        embedding1 = manager.extract_speaker_embedding(audio_data, model_asr=model)
        
        if embedding1 is not None:
            print(f"✅ 方法1成功! 嵌入向量维度: {len(embedding1)}")
            print(f"📊 嵌入向量范围: [{embedding1.min():.6f}, {embedding1.max():.6f}]")
            print(f"📊 嵌入向量均值: {embedding1.mean():.6f}")
        else:
            print("❌ 方法1失败: 返回None")
        
        # 方法2：直接使用FunASR模型
        if model is not None:
            print("\n🔧 方法2：直接使用FunASR模型...")
            try:
                result = model.generate(
                    input=audio_data,
                    cache={},
                    return_spk_res=True,
                    return_spk_embedding=True
                )
                
                if result and len(result) > 0:
                    embedding2 = result[0].get("spk_embedding", None)
                    if embedding2 is not None:
                        if hasattr(embedding2, 'detach'):
                            embedding2 = embedding2.detach().cpu().numpy()
                        if isinstance(embedding2, np.ndarray):
                            if embedding2.ndim > 1:
                                embedding2 = embedding2.flatten()
                            print(f"✅ 方法2成功! 嵌入向量维度: {len(embedding2)}")
                            print(f"📊 嵌入向量范围: [{embedding2.min():.6f}, {embedding2.max():.6f}]")
                        else:
                            print(f"❌ 方法2失败: 嵌入向量类型错误 {type(embedding2)}")
                    else:
                        print("❌ 方法2失败: 嵌入向量为None")
                        print(f"🔍 FunASR结果键: {list(result[0].keys())}")
                else:
                    print("❌ 方法2失败: FunASR返回空结果")
                    
            except Exception as e:
                print(f"❌ 方法2失败: {e}")
                traceback.print_exc()
        
        return embedding1
        
    except Exception as e:
        print(f"❌ 嵌入向量提取失败: {e}")
        traceback.print_exc()
        return None

def test_registration(manager, file_path):
    """测试说话人注册"""
    print("\n📝 测试说话人注册...")
    
    if manager is None:
        print("⚠️ 跳过测试：管理器为空")
        return False
    
    try:
        speaker_name = "测试说话人_王占分"
        success, message = manager.register_speaker(speaker_name, file_path)
        
        if success:
            print(f"✅ 注册成功: {message}")
            
            # 查看注册的说话人
            speakers = manager.get_registered_speakers()
            print(f"📋 已注册说话人数量: {len(speakers)}")
            for speaker in speakers:
                print(f"👤 {speaker['name']} (ID: {speaker['id']}, 时长: {speaker['audio_duration']:.1f}秒)")
            
            return True
        else:
            print(f"❌ 注册失败: {message}")
            return False
            
    except Exception as e:
        print(f"❌ 注册过程失败: {e}")
        traceback.print_exc()
        return False

def cleanup_test_data():
    """清理测试数据"""
    print("\n🧹 清理测试数据...")
    try:
        import shutil
        if os.path.exists("./debug_speaker_db"):
            shutil.rmtree("./debug_speaker_db")
            print("✅ 测试数据库已清理")
    except Exception as e:
        print(f"⚠️ 清理失败: {e}")

def main():
    if len(sys.argv) != 2:
        print("❌ 使用方法: python debug_speaker_audio.py <音频文件路径>")
        print("📝 例如: python debug_speaker_audio.py /Users/csdn/Desktop/王占分-音色.m4a")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    print("🔧 说话人音频文件调试工具")
    print("=" * 60)
    
    # 1. 检查文件
    if not check_audio_file(file_path):
        return
    
    # 2. 加载音频
    audio_data, sample_rate = load_audio_with_librosa(file_path)
    if audio_data is None:
        print("❌ 无法加载音频文件，退出")
        return
    
    # 3. 测试说话人管理器
    manager = test_speaker_manager_basic()
    
    # 4. 测试FunASR模型
    model = test_funasr_model()
    
    # 5. 测试嵌入向量提取
    embedding = test_embedding_extraction(manager, model, audio_data)
    
    # 6. 测试注册功能
    if embedding is not None:
        test_registration(manager, file_path)
    else:
        print("⚠️ 跳过注册测试：嵌入向量提取失败")
    
    # 7. 清理
    cleanup_test_data()
    
    print("\n🎉 调试完成!")
    
    # 总结
    print("\n📊 调试总结:")
    print(f"{'文件检查':<15}: {'✅ 通过' if os.path.exists(file_path) else '❌ 失败'}")
    print(f"{'音频加载':<15}: {'✅ 通过' if audio_data is not None else '❌ 失败'}")
    print(f"{'管理器创建':<15}: {'✅ 通过' if manager is not None else '❌ 失败'}")
    print(f"{'模型加载':<15}: {'✅ 通过' if model is not None else '❌ 失败'}")
    print(f"{'嵌入向量提取':<15}: {'✅ 通过' if embedding is not None else '❌ 失败'}")
    
    if audio_data is not None and len(audio_data) / sample_rate < 2.0:
        print("\n⚠️ 警告: 音频时长少于2秒，可能影响说话人识别效果")
    
    if embedding is None:
        print("\n🔍 建议检查:")
        print("1. 确保音频文件完整且未损坏")
        print("2. 确保音频时长至少2秒")
        print("3. 确保音频包含清晰的语音内容")
        print("4. 检查FunASR模型是否正确安装")

if __name__ == "__main__":
    main() 