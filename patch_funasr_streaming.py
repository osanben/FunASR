#!/usr/bin/env python3
"""
FunASR 流式处理补丁 - 解决大音频文件内存问题
"""
import os
import sys
import numpy as np
import soundfile as sf
import librosa
from pathlib import Path

def patch_audio_loading():
    """
    替换原有的音频加载函数，支持流式处理
    """
    
    def safe_load_audio(file_path, sr=16000, chunk_duration=300):
        """
        安全加载音频文件，自动处理大文件
        
        Args:
            file_path: 音频文件路径
            sr: 目标采样率
            chunk_duration: 如果文件过大，分段处理的时长(秒)
        
        Returns:
            audio_data: 音频数据
            sample_rate: 采样率
        """
        try:
            # 先获取文件信息，不加载到内存
            info = sf.info(file_path)
            duration = info.frames / info.samplerate
            estimated_memory = info.frames * info.channels * 4 / 1024**3  # GB
            
            print(f"🎵 音频文件信息: {Path(file_path).name}")
            print(f"   时长: {duration:.1f}秒 ({duration/60:.1f}分钟)")
            print(f"   预估内存: {estimated_memory:.2f}GB")
            
            # 如果文件小于500MB，直接加载
            if estimated_memory < 0.5:
                print("✅ 文件大小适中，直接加载")
                return librosa.load(file_path, sr=sr, dtype=np.float32)
            
            # 大文件处理：分段加载
            print(f"⚠️  大文件检测，采用分段处理 (每段{chunk_duration}秒)")
            
            chunk_samples = int(chunk_duration * sr)
            all_chunks = []
            
            with sf.SoundFile(file_path, 'r') as audio_file:
                chunk_index = 0
                
                while True:
                    # 计算读取位置
                    start_frame = chunk_index * chunk_samples
                    if start_frame >= audio_file.frames:
                        break
                    
                    audio_file.seek(start_frame)
                    
                    # 读取当前段
                    frames_to_read = min(chunk_samples, audio_file.frames - start_frame)
                    audio_chunk = audio_file.read(frames_to_read)
                    
                    if len(audio_chunk) == 0:
                        break
                    
                    # 转换为单声道
                    if len(audio_chunk.shape) > 1:
                        audio_chunk = np.mean(audio_chunk, axis=1)
                    
                    # 重采样
                    if audio_file.samplerate != sr:
                        audio_chunk = librosa.resample(
                            audio_chunk,
                            orig_sr=audio_file.samplerate, 
                            target_sr=sr
                        )
                    
                    all_chunks.append(audio_chunk.astype(np.float32))
                    print(f"   📄 处理第{chunk_index+1}段: {len(audio_chunk)/sr:.1f}秒")
                    
                    chunk_index += 1
                    
                    # 限制最大段数，避免内存爆炸
                    if chunk_index >= 50:  # 最多50段，约4小时
                        print("⚠️  音频过长，只处理前50段")
                        break
            
            # 合并所有段
            if all_chunks:
                print(f"🔗 合并 {len(all_chunks)} 段音频...")
                audio_data = np.concatenate(all_chunks)
                print(f"✅ 最终音频: {len(audio_data)/sr:.1f}秒")
                return audio_data, sr
            else:
                raise ValueError("无法读取任何音频数据")
                
        except Exception as e:
            print(f"❌ 音频加载失败: {e}")
            # 如果流式加载也失败，尝试极小的段
            try:
                print("🔄 尝试使用极小分段...")
                return safe_load_audio(file_path, sr, chunk_duration=60)  # 1分钟段
            except Exception:
                raise Exception(f"无法加载音频文件: {file_path}")
    
    return safe_load_audio

def apply_patch():
    """
    应用补丁到FunASR服务端
    """
    server_file = "runtime/python/websocket/funasr_upload_server.py"
    
    if not os.path.exists(server_file):
        print(f"❌ 找不到服务端文件: {server_file}")
        return False
    
    print("🔧 应用FunASR流式处理补丁...")
    
    # 读取原文件
    with open(server_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找并替换音频加载部分
    old_pattern = "audio_data, sample_rate = librosa.load(file_path, sr=16000, dtype=np.float32)"
    
    if old_pattern in content:
        new_code = '''# 使用安全的音频加载函数
        from patch_funasr_streaming import patch_audio_loading
        safe_load_audio = patch_audio_loading()
        audio_data, sample_rate = safe_load_audio(file_path, sr=16000)'''
        
        content = content.replace(old_pattern, new_code)
        
        # 备份原文件
        backup_file = server_file + ".backup"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 补丁应用成功!")
        print(f"📄 原文件备份至: {backup_file}")
        
        # 写入修改后的文件
        with open(server_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    else:
        print("❌ 未找到需要修改的代码段")
        return False

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "apply":
        apply_patch()
    else:
        print("用法:")
        print("  python patch_funasr_streaming.py apply  # 应用补丁")
        print("  import patch_funasr_streaming           # 导入使用")

if __name__ == "__main__":
    main() 