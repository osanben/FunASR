#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音识别测试脚本
测试WebSocket通信是否正常
"""
import asyncio
import websockets
import json
import time

async def test_speech_recognition():
    """测试语音识别功能"""
    uri = "ws://127.0.0.1:10095"
    
    try:
        print("🔌 连接到WebSocket服务器...")
        async with websockets.connect(uri) as websocket:
            print("✅ 连接成功!")
            
            # 1. 发送初始化消息
            init_message = {
                "chunk_size": [5, 10, 5],
                "wav_name": "h5",
                "is_speaking": True,
                "chunk_interval": 10,
                "mode": "2pass"
            }
            
            print(f"📤 发送初始化消息: {init_message}")
            await websocket.send(json.dumps(init_message))
            
            # 2. 模拟发送一些音频数据
            print("🎵 模拟发送音频数据...")
            for i in range(5):
                # 发送一些模拟音频数据
                audio_data = b'\x00' * 1920  # 1920字节的模拟音频数据
                await websocket.send(audio_data)
                
                # 检查是否有响应
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    if isinstance(response, str):
                        data = json.loads(response)
                        print(f"📨 收到中间结果: {data}")
                except asyncio.TimeoutError:
                    print(f"⏰ 第{i+1}次音频数据发送完毕，无中间结果")
                
                await asyncio.sleep(0.5)  # 等待0.5秒
            
            # 3. 发送停止说话消息
            stop_message = {
                "is_speaking": False
            }
            
            print(f"🛑 发送停止消息: {stop_message}")
            await websocket.send(json.dumps(stop_message))
            
            # 4. 等待最终结果
            print("⏳ 等待最终识别结果...")
            try:
                final_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                if isinstance(final_response, str):
                    final_data = json.loads(final_response)
                    print(f"🎯 收到最终结果: {final_data}")
                    
                    if final_data.get("is_final"):
                        print("✅ 语音识别测试成功!")
                    else:
                        print("⚠️ 未收到最终结果标记")
                        
            except asyncio.TimeoutError:
                print("❌ 等待最终结果超时")
                
    except ConnectionRefusedError:
        print("❌ 无法连接到WebSocket服务器，请确保服务器正在运行")
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")

if __name__ == "__main__":
    print("🧪 开始语音识别测试...")
    asyncio.run(test_speech_recognition())
    print("🏁 测试完成") 