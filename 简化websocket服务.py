#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的FunASR WebSocket服务
为图形化界面提供WebSocket连接支持
"""

import asyncio
import websockets
import json
import logging
import signal
import sys
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FunASRWebSocketServer:
    def __init__(self, host="127.0.0.1", port=10095):
        self.host = host
        self.port = port
        self.server = None
        self.connected_clients = set()
        
    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        client_address = websocket.remote_address
        logger.info(f"新客户端连接: {client_address}")
        
        # 添加到连接列表
        self.connected_clients.add(websocket)
        
        try:
            await websocket.send(json.dumps({
                "type": "connection",
                "status": "connected",
                "message": "FunASR WebSocket服务连接成功",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False))
            
            async for message in websocket:
                await self.process_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"客户端断开连接: {client_address}")
        except Exception as e:
            logger.error(f"处理客户端消息时出错: {e}")
        finally:
            # 从连接列表移除
            self.connected_clients.discard(websocket)
    
    async def process_message(self, websocket, message):
        """处理客户端消息"""
        try:
            # 尝试解析JSON消息
            data = json.loads(message)
            logger.info(f"收到消息: {data}")
            
            # 根据消息类型处理
            if data.get("type") == "ping":
                await self.handle_ping(websocket)
            elif data.get("type") == "start_recognition":
                await self.handle_start_recognition(websocket, data)
            elif data.get("type") == "stop_recognition":
                await self.handle_stop_recognition(websocket, data)
            elif data.get("type") == "audio_data":
                await self.handle_audio_data(websocket, data)
            else:
                await self.handle_unknown_message(websocket, data)
                
        except json.JSONDecodeError:
            # 可能是音频二进制数据
            await self.handle_binary_data(websocket, message)
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"处理消息时出错: {str(e)}"
            }, ensure_ascii=False))
    
    async def handle_ping(self, websocket):
        """处理心跳检测"""
        await websocket.send(json.dumps({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False))
    
    async def handle_start_recognition(self, websocket, data):
        """处理开始识别请求"""
        mode = data.get("mode", "2pass")
        
        response = {
            "type": "recognition_started",
            "mode": mode,
            "message": f"开始{mode}模式语音识别",
            "status": "ready"
        }
        
        await websocket.send(json.dumps(response, ensure_ascii=False))
        logger.info(f"开始语音识别，模式: {mode}")
    
    async def handle_stop_recognition(self, websocket, data):
        """处理停止识别请求"""
        response = {
            "type": "recognition_stopped",
            "message": "语音识别已停止",
            "status": "stopped"
        }
        
        await websocket.send(json.dumps(response, ensure_ascii=False))
        logger.info("停止语音识别")
    
    async def handle_audio_data(self, websocket, data):
        """处理音频数据"""
        # 模拟语音识别结果
        demo_results = [
            "这是一个语音识别演示",
            "FunASR工具包功能强大",
            "支持实时语音转文字",
            "阿里巴巴达摩院开发",
            "语音识别效果很好"
        ]
        
        import random
        result_text = random.choice(demo_results)
        
        # 发送中间结果
        await websocket.send(json.dumps({
            "type": "partial_result",
            "text": result_text[:len(result_text)//2] + "...",
            "is_final": False,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False))
        
        # 等待一下模拟处理时间
        await asyncio.sleep(1)
        
        # 发送最终结果
        await websocket.send(json.dumps({
            "type": "final_result", 
            "text": result_text,
            "is_final": True,
            "confidence": 0.95,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False))
        
        logger.info(f"音频识别结果: {result_text}")
    
    async def handle_binary_data(self, websocket, data):
        """处理二进制音频数据"""
        logger.info(f"收到二进制音频数据，大小: {len(data)} 字节")
        
        # 模拟处理音频
        await asyncio.sleep(0.5)
        
        # 返回识别结果
        await websocket.send(json.dumps({
            "type": "binary_result",
            "text": "收到音频数据，这是模拟识别结果",
            "data_size": len(data),
            "is_final": True,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False))
    
    async def handle_unknown_message(self, websocket, data):
        """处理未知消息"""
        response = {
            "type": "unknown_message",
            "message": "收到未知消息类型",
            "original_data": data
        }
        
        await websocket.send(json.dumps(response, ensure_ascii=False))
        logger.warning(f"收到未知消息: {data}")
    
    async def start_server(self):
        """启动WebSocket服务器"""
        logger.info(f"启动FunASR WebSocket服务器...")
        logger.info(f"监听地址: {self.host}:{self.port}")
        
        try:
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10
            )
            
            logger.info("🎉 WebSocket服务器启动成功!")
            logger.info(f"🔗 连接地址: ws://{self.host}:{self.port}")
            logger.info("等待客户端连接...")
            
            # 保持服务器运行
            await self.server.wait_closed()
            
        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            raise
    
    async def stop_server(self):
        """停止服务器"""
        if self.server:
            logger.info("正在停止WebSocket服务器...")
            
            # 通知所有连接的客户端
            if self.connected_clients:
                disconnect_message = json.dumps({
                    "type": "server_shutdown",
                    "message": "服务器即将关闭"
                }, ensure_ascii=False)
                
                await asyncio.gather(
                    *[client.send(disconnect_message) for client in self.connected_clients],
                    return_exceptions=True
                )
            
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket服务器已停止")

def signal_handler(server):
    """信号处理函数"""
    def handler(signum, frame):
        logger.info(f"收到信号 {signum}，准备关闭服务器...")
        asyncio.create_task(server.stop_server())
        sys.exit(0)
    return handler

async def main():
    """主函数"""
    server = FunASRWebSocketServer()
    
    # 注册信号处理器
    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, signal_handler(server))
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("收到键盘中断，关闭服务器...")
        await server.stop_server()
    except Exception as e:
        logger.error(f"服务器运行时出错: {e}")
        await server.stop_server()

if __name__ == "__main__":
    print("🎤" + "=" * 50 + "🎤")
    print("       FunASR 简化 WebSocket 服务")
    print("🎤" + "=" * 50 + "🎤")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 服务已停止，再见！")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1) 