#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunASR 服务状态测试脚本
"""

import requests
import websockets
import asyncio
import json

def test_http_server():
    """测试HTTP服务器"""
    try:
        print("🌐 测试HTTP服务器...")
        response = requests.get("http://127.0.0.1:1337", timeout=5)
        print(f"HTTP服务器状态: {response.status_code}")
        
        # 测试静态文件
        static_response = requests.get("http://127.0.0.1:1337/static/index.html", timeout=5)
        print(f"静态文件访问状态: {static_response.status_code}")
        
        if static_response.status_code == 200:
            print("✅ HTTP服务器正常工作")
            return True
        else:
            print("❌ HTTP服务器有问题")
            return False
            
    except Exception as e:
        print(f"❌ HTTP服务器连接失败: {e}")
        return False

async def test_websocket_server():
    """测试WebSocket服务器"""
    try:
        print("🔌 测试WebSocket服务器...")
        uri = "ws://127.0.0.1:10095"
        
        async with websockets.connect(uri, subprotocol="binary") as websocket:
            print("✅ WebSocket连接成功")
            
            # 发送初始化消息
            init_message = {
                "mode": "2pass",
                "chunk_size": [5, 10, 5],
                "chunk_interval": 10,
                "wav_name": "test"
            }
            
            await websocket.send(json.dumps(init_message))
            print("📤 发送初始化消息")
            
            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 收到响应: {response}")
                print("✅ WebSocket服务器正常工作")
                return True
            except asyncio.TimeoutError:
                print("⏰ WebSocket响应超时，但连接正常")
                return True
                
    except Exception as e:
        print(f"❌ WebSocket服务器连接失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 FunASR服务状态检测")
    print("=" * 50)
    
    # 测试HTTP服务器
    http_ok = test_http_server()
    print()
    
    # 测试WebSocket服务器
    websocket_ok = asyncio.run(test_websocket_server())
    print()
    
    # 总结
    print("📊 测试结果总结:")
    print(f"HTTP服务器: {'✅ 正常' if http_ok else '❌ 异常'}")
    print(f"WebSocket服务器: {'✅ 正常' if websocket_ok else '❌ 异常'}")
    
    if http_ok and websocket_ok:
        print("\n🎉 所有服务正常运行！")
        print("📱 访问地址: http://127.0.0.1:1337")
        print("🔌 WebSocket地址: ws://127.0.0.1:10095")
    else:
        print("\n⚠️  部分服务有问题，请检查日志")

if __name__ == "__main__":
    main() 