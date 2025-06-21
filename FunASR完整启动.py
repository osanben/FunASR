#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunASR 完整启动和管理脚本
"""

import subprocess
import sys
import os
import time
import signal
import psutil
from pathlib import Path

class FunASRManager:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.html5_process = None
        self.ws_process = None
        
    def check_port(self, port):
        """检查端口是否被占用"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return True
        return False
    
    def kill_process_on_port(self, port):
        """杀死占用指定端口的进程"""
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.info['connections'] or []:
                    if conn.laddr.port == port:
                        print(f"🔪 杀死占用端口{port}的进程 (PID: {proc.info['pid']})")
                        proc.kill()
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    
    def start_html5_server(self):
        """启动HTML5服务器"""
        print("🌐 启动HTML5服务器...")
        
        # 检查端口是否被占用
        if self.check_port(1337):
            print("⚠️  端口1337被占用，尝试释放...")
            self.kill_process_on_port(1337)
            time.sleep(2)
        
        html5_dir = self.project_root / "runtime" / "html5"
        html5_cmd = [
            sys.executable, "h5Server.py",
            "--host", "0.0.0.0",
            "--port", "1337"
        ]
        
        try:
            self.html5_process = subprocess.Popen(
                html5_cmd,
                cwd=html5_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"✅ HTML5服务器已启动 (PID: {self.html5_process.pid})")
            return True
        except Exception as e:
            print(f"❌ HTML5服务器启动失败: {e}")
            return False
    
    def start_websocket_server(self):
        """启动WebSocket服务器"""
        print("🔌 启动WebSocket服务器...")
        
        # 检查端口是否被占用
        if self.check_port(10095):
            print("⚠️  端口10095被占用，尝试释放...")
            self.kill_process_on_port(10095)
            time.sleep(2)
        
        ws_dir = self.project_root / "runtime" / "python" / "websocket"
        ws_cmd = [
            sys.executable, "funasr_wss_server.py",
            "--port", "10095",
            "--host", "0.0.0.0"
        ]
        
        try:
            self.ws_process = subprocess.Popen(
                ws_cmd,
                cwd=ws_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"✅ WebSocket服务器已启动 (PID: {self.ws_process.pid})")
            return True
        except Exception as e:
            print(f"❌ WebSocket服务器启动失败: {e}")
            return False
    
    def check_services(self):
        """检查服务状态"""
        print("📊 检查服务状态...")
        
        html5_running = self.check_port(1337)
        ws_running = self.check_port(10095)
        
        print(f"HTML5服务器 (端口1337): {'✅ 运行中' if html5_running else '❌ 未运行'}")
        print(f"WebSocket服务器 (端口10095): {'✅ 运行中' if ws_running else '❌ 未运行'}")
        
        return html5_running and ws_running
    
    def start_all(self):
        """启动所有服务"""
        print("🚀 启动FunASR完整服务...")
        print("=" * 50)
        
        # 启动HTML5服务器
        html5_ok = self.start_html5_server()
        time.sleep(3)
        
        # 启动WebSocket服务器
        ws_ok = self.start_websocket_server()
        time.sleep(5)  # 等待模型加载
        
        # 检查服务状态
        print("\n📊 最终状态检查:")
        all_ok = self.check_services()
        
        if all_ok:
            print("\n🎉 FunASR服务启动完成！")
            print("=" * 50)
            print("📱 Web界面: http://127.0.0.1:1337")
            print("🔌 WebSocket: ws://127.0.0.1:10095")
            print("=" * 50)
            print("💡 在浏览器中打开 http://127.0.0.1:1337 开始使用")
        else:
            print("\n⚠️  部分服务启动失败，请检查错误信息")
        
        return all_ok
    
    def stop_all(self):
        """停止所有服务"""
        print("🛑 停止FunASR服务...")
        
        # 停止HTML5服务器
        if self.html5_process:
            self.html5_process.terminate()
            print("✅ HTML5服务器已停止")
        
        # 停止WebSocket服务器
        if self.ws_process:
            self.ws_process.terminate()
            print("✅ WebSocket服务器已停止")
        
        # 清理端口
        self.kill_process_on_port(1337)
        self.kill_process_on_port(10095)

def main():
    """主函数"""
    manager = FunASRManager()
    
    try:
        manager.start_all()
        
        # 保持运行
        print("\n按 Ctrl+C 停止服务...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 收到停止信号...")
        manager.stop_all()
        print("👋 服务已停止")

if __name__ == "__main__":
    main() 