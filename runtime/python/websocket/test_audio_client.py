#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FunASR WebSocket 音频测试客户端
直接加载本地音频文件测试服务器，避免前端传输问题
"""

import asyncio
import websockets
import json
import numpy as np
import argparse
import os
import sys
import ssl
from pathlib import Path

# 音频处理库
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("⚠️ 警告: librosa未安装，只能处理WAV文件")

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    print("⚠️ 警告: soundfile未安装，音频处理功能受限")

class AudioTestClient:
    def __init__(self, server_url="wss://127.0.0.1:10095/"):
        self.server_url = server_url
        self.websocket = None
        self.results = []
        
    async def connect(self):
        """连接到WebSocket服务器"""
        try:
            print(f"🔗 正在连接到服务器: {self.server_url}")
            
            # 如果是WSS协议，创建SSL上下文（忽略证书验证）
            ssl_context = None
            if self.server_url.startswith("wss://"):
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                print("🔒 使用WSS协议（忽略SSL证书验证）")
            
            self.websocket = await websockets.connect(
                self.server_url, 
                subprotocols=["binary"],
                ssl=ssl_context
            )
            print("✅ 连接成功!")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
            
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 连接已断开")
    
    def load_audio(self, audio_path, target_sr=16000):
        """加载音频文件并转换为16kHz单声道"""
        print(f"🎵 正在加载音频文件: {audio_path}")
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        file_ext = Path(audio_path).suffix.lower()
        print(f"📄 文件格式: {file_ext}")
        
        # 使用librosa加载音频（支持多种格式）
        if LIBROSA_AVAILABLE:
            try:
                audio_data, sr = librosa.load(audio_path, sr=target_sr, mono=True)
                print(f"✅ 使用librosa加载成功")
                print(f"   原始采样率: {sr}Hz")
                print(f"   目标采样率: {target_sr}Hz") 
                print(f"   音频长度: {len(audio_data)/sr:.2f}秒")
                print(f"   音频范围: [{audio_data.min():.3f}, {audio_data.max():.3f}]")
                
                # 转换为16位整数
                audio_int16 = (audio_data * 32767).astype(np.int16)
                return audio_int16, target_sr, file_ext[1:]  # 去掉点号
                
            except Exception as e:
                print(f"⚠️ librosa加载失败: {e}")
        
        # 备用方案：使用soundfile
        if SOUNDFILE_AVAILABLE and file_ext in ['.wav', '.flac']:
            try:
                audio_data, sr = sf.read(audio_path)
                
                # 转换为单声道
                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1)
                
                # 重采样到目标采样率
                if sr != target_sr:
                    # 简单重采样
                    ratio = target_sr / sr
                    new_length = int(len(audio_data) * ratio)
                    indices = np.linspace(0, len(audio_data) - 1, new_length)
                    audio_data = np.interp(indices, np.arange(len(audio_data)), audio_data)
                
                print(f"✅ 使用soundfile加载成功")
                print(f"   采样率: {target_sr}Hz")
                print(f"   音频长度: {len(audio_data)/target_sr:.2f}秒")
                
                # 转换为16位整数
                if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
                    audio_int16 = (audio_data * 32767).astype(np.int16)
                else:
                    audio_int16 = audio_data.astype(np.int16)
                
                return audio_int16, target_sr, file_ext[1:]
                
            except Exception as e:
                print(f"⚠️ soundfile加载失败: {e}")
        
        # 最后尝试：直接读取WAV文件头（简单实现）
        if file_ext == '.wav':
            try:
                with open(audio_path, 'rb') as f:
                    # 跳过WAV文件头（简化处理）
                    f.read(44)
                    audio_bytes = f.read()
                    audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                    
                print(f"✅ 直接读取WAV文件成功")
                print(f"   音频长度: {len(audio_int16)/target_sr:.2f}秒（假设16kHz）")
                
                return audio_int16, target_sr, 'wav'
                
            except Exception as e:
                print(f"❌ 直接读取WAV失败: {e}")
        
        raise Exception("所有音频加载方法都失败了，请安装librosa: pip install librosa")
    
    async def send_control_message(self, **kwargs):
        """发送控制消息"""
        default_config = {
            "chunk_size": [5, 10, 5],
            "wav_name": "test_audio",
            "is_speaking": True,
            "chunk_interval": 10,
            "itn": True,
            "mode": "offline"
        }
        
        # 更新配置
        default_config.update(kwargs)
        
        message = json.dumps(default_config)
        print(f"📨 发送控制消息: {message}")
        await self.websocket.send(message)
    
    async def send_audio_data(self, audio_data, chunk_size=960):
        """发送音频数据"""
        print(f"🎵 开始发送音频数据...")
        print(f"   总样本数: {len(audio_data)}")
        print(f"   块大小: {chunk_size}")
        print(f"   预计块数: {len(audio_data) // chunk_size + 1}")
        
        total_chunks = len(audio_data) // chunk_size + (1 if len(audio_data) % chunk_size > 0 else 0)
        sent_chunks = 0
        
        # 分块发送
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            
            # 转换为字节数据
            chunk_bytes = chunk.tobytes()
            
            # 发送音频块
            await self.websocket.send(chunk_bytes)
            
            sent_chunks += 1
            progress = (sent_chunks / total_chunks) * 100
            print(f"   进度: {progress:.1f}% ({sent_chunks}/{total_chunks})")
            
            # 小延迟，避免发送过快
            await asyncio.sleep(0.01)
        
        print("✅ 音频数据发送完成")
    
    async def send_end_message(self):
        """发送结束消息"""
        end_message = {
            "chunk_size": [5, 10, 5],
            "wav_name": "test_audio", 
            "is_speaking": False,
            "chunk_interval": 10,
            "mode": "offline"
        }
        
        message = json.dumps(end_message)
        print(f"📨 发送结束消息: {message}")
        await self.websocket.send(message)
    
    async def listen_for_results(self, timeout=300):
        """监听服务器返回的结果"""
        print("👂 开始监听服务器响应...")
        self.results = []
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            async for message in self.websocket:
                current_time = asyncio.get_event_loop().time()
                if current_time - start_time > timeout:
                    print(f"⏰ 超时 ({timeout}秒)，停止监听")
                    break
                
                try:
                    if isinstance(message, str):
                        result = json.loads(message)
                        print(f"📥 收到结果: {result}")
                        self.results.append(result)
                        
                        # 检查是否是最终结果
                        if result.get('is_final', False):
                            print("🏁 收到最终结果，停止监听")
                            break
                            
                    elif isinstance(message, bytes):
                        print(f"📥 收到二进制数据: {len(message)} 字节")
                        
                except json.JSONDecodeError:
                    print(f"⚠️ 无法解析消息: {message[:100]}...")
                    
        except websockets.exceptions.ConnectionClosed:
            print("🔌 连接已断开")
        except Exception as e:
            print(f"❌ 监听过程中出错: {e}")
    
    async def test_audio_file(self, audio_path, timeout=300):
        """测试单个音频文件"""
        print(f"\n{'='*60}")
        print(f"🧪 开始测试音频文件: {audio_path}")
        print(f"{'='*60}")
        
        try:
            # 1. 加载音频
            audio_data, sample_rate, file_ext = self.load_audio(audio_path)
            
            # 2. 连接服务器
            if not await self.connect():
                return False
            
            # 3. 发送控制消息
            await self.send_control_message(
                wav_format="PCM" if file_ext == "wav" else file_ext.upper(),
                audio_fs=sample_rate
            )
            
            # 4. 启动结果监听任务
            listen_task = asyncio.create_task(self.listen_for_results(timeout))
            
            # 5. 发送音频数据
            await self.send_audio_data(audio_data)
            
            # 6. 发送结束消息
            await self.send_end_message()
            
            # 7. 等待结果
            await listen_task
            
            # 8. 显示结果
            self.display_results()
            
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await self.disconnect()
    
    def display_results(self):
        """显示测试结果"""
        print(f"\n{'='*60}")
        print("📊 测试结果汇总")
        print(f"{'='*60}")
        
        if not self.results:
            print("❌ 没有收到任何结果")
            return
        
        print(f"✅ 总共收到 {len(self.results)} 条结果")
        
        for i, result in enumerate(self.results):
            print(f"\n📋 结果 {i+1}:")
            
            if 'text' in result:
                print(f"   文本: {result['text']}")
            
            if 'timestamp' in result:
                print(f"   时间戳: {result['timestamp']}")
            
            if 'mode' in result:
                print(f"   模式: {result['mode']}")
            
            if 'wav_name' in result:
                print(f"   音频名称: {result['wav_name']}")
            
            # 显示其他字段
            other_fields = {k: v for k, v in result.items() 
                          if k not in ['text', 'timestamp', 'mode', 'wav_name']}
            if other_fields:
                print(f"   其他信息: {other_fields}")


async def main():
    parser = argparse.ArgumentParser(description="FunASR WebSocket 音频测试客户端")
    parser.add_argument("audio_path", help="音频文件路径")
    parser.add_argument("--server", default="wss://127.0.0.1:10095/", 
                       help="WebSocket服务器地址 (默认: wss://127.0.0.1:10095/)")
    parser.add_argument("--timeout", type=int, default=300,
                       help="超时时间（秒，默认300）")
    
    args = parser.parse_args()
    
    print("🌟 FunASR WebSocket 音频测试客户端")
    print("="*60)
    print(f"音频文件: {args.audio_path}")
    print(f"服务器: {args.server}")
    print(f"超时时间: {args.timeout}秒")
    
    # 检查音频文件是否存在
    if not os.path.exists(args.audio_path):
        print(f"❌ 音频文件不存在: {args.audio_path}")
        sys.exit(1)
    
    # 创建测试客户端
    client = AudioTestClient(args.server)
    
    # 执行测试
    success = await client.test_audio_file(args.audio_path, args.timeout)
    
    if success:
        print("\n🎉 测试完成！")
        sys.exit(0)
    else:
        print("\n💥 测试失败！")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 