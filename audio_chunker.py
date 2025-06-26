#!/usr/bin/env python3
"""
音频分段处理工具 - 解决长音频内存不足问题
"""
import os
import sys
import librosa
import soundfile as sf
import numpy as np
from pathlib import Path

class AudioChunker:
    def __init__(self, chunk_duration=300, overlap=30, target_sr=16000):
        """
        音频分段工具
        
        Args:
            chunk_duration: 每段时长(秒)，默认5分钟
            overlap: 重叠时长(秒)，默认30秒
            target_sr: 目标采样率，默认16kHz
        """
        self.chunk_duration = chunk_duration
        self.overlap = overlap
        self.target_sr = target_sr
        
    def get_audio_info(self, file_path):
        """获取音频文件信息，不加载到内存"""
        try:
            info = sf.info(file_path)
            duration = info.frames / info.samplerate
            return {
                'duration': duration,
                'samplerate': info.samplerate,
                'channels': info.channels,
                'frames': info.frames,
                'estimated_memory': info.frames * info.channels * 4 / 1024**3  # GB
            }
        except Exception as e:
            print(f"❌ 无法获取音频信息: {e}")
            return None
    
    def split_audio_file(self, input_path, output_dir=None):
        """
        将长音频文件分割成小段
        
        Args:
            input_path: 输入音频文件路径
            output_dir: 输出目录，默认为输入文件同目录下的chunks文件夹
        
        Returns:
            list: 分段文件路径列表
        """
        input_path = Path(input_path)
        
        if output_dir is None:
            output_dir = input_path.parent / f"{input_path.stem}_chunks"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        # 获取音频信息
        info = self.get_audio_info(input_path)
        if not info:
            return []
        
        print(f"🎵 音频信息:")
        print(f"   文件: {input_path.name}")
        print(f"   时长: {info['duration']:.1f}秒 ({info['duration']/60:.1f}分钟)")
        print(f"   采样率: {info['samplerate']}Hz")
        print(f"   声道数: {info['channels']}")
        print(f"   预估内存需求: {info['estimated_memory']:.2f}GB")
        
        if info['estimated_memory'] < 0.5:  # 小于500MB直接处理
            print("✅ 文件较小，无需分段")
            return [str(input_path)]
        
        # 计算分段参数
        total_duration = info['duration']
        chunk_samples = int(self.chunk_duration * self.target_sr)
        overlap_samples = int(self.overlap * self.target_sr)
        step_samples = chunk_samples - overlap_samples
        
        chunk_files = []
        chunk_index = 0
        
        print(f"🔪 开始分段处理...")
        print(f"   每段时长: {self.chunk_duration}秒")
        print(f"   重叠时长: {self.overlap}秒")
        
        # 使用流式读取分段
        with sf.SoundFile(input_path, 'r') as audio_file:
            while True:
                # 设置读取位置
                start_frame = chunk_index * step_samples
                if start_frame >= audio_file.frames:
                    break
                
                audio_file.seek(start_frame)
                
                # 读取当前段
                frames_to_read = min(chunk_samples, audio_file.frames - start_frame)
                audio_chunk = audio_file.read(frames_to_read)
                
                if len(audio_chunk) == 0:
                    break
                
                # 转换为单声道（如果是立体声）
                if len(audio_chunk.shape) > 1:
                    audio_chunk = np.mean(audio_chunk, axis=1)
                
                # 重采样到目标采样率
                if audio_file.samplerate != self.target_sr:
                    audio_chunk = librosa.resample(
                        audio_chunk, 
                        orig_sr=audio_file.samplerate, 
                        target_sr=self.target_sr
                    )
                
                # 保存分段文件
                chunk_filename = f"chunk_{chunk_index:04d}.wav"
                chunk_path = output_dir / chunk_filename
                
                sf.write(chunk_path, audio_chunk, self.target_sr)
                chunk_files.append(str(chunk_path))
                
                actual_duration = len(audio_chunk) / self.target_sr
                print(f"   ✅ 第{chunk_index+1}段: {chunk_filename} ({actual_duration:.1f}秒)")
                
                chunk_index += 1
        
        print(f"🎉 分段完成! 共生成 {len(chunk_files)} 个文件")
        print(f"📁 输出目录: {output_dir}")
        
        return chunk_files

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python audio_chunker.py <音频文件路径> [输出目录]")
        print("示例: python audio_chunker.py /path/to/long_audio.wav")
        return
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_file):
        print(f"❌ 文件不存在: {input_file}")
        return
    
    # 创建分段器（5分钟一段，30秒重叠）
    chunker = AudioChunker(chunk_duration=300, overlap=30)
    
    # 分段处理
    chunk_files = chunker.split_audio_file(input_file, output_dir)
    
    if chunk_files:
        print(f"\n📋 生成的分段文件:")
        for i, chunk_file in enumerate(chunk_files, 1):
            print(f"   {i:2d}. {chunk_file}")

if __name__ == "__main__":
    main() 