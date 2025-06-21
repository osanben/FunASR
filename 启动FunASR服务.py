#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunASR 完整服务启动脚本
包含HTML5界面服务器和WebSocket语音识别服务器
"""

import subprocess
import time
import os
import sys
import signal
import threading
from pathlib import Path

class FunASRService:
    def __init__(self):
        self.processes = []
        self.project_root = Path(__file__).parent
        
    def start_html5_server(self):
        """启动HTML5服务器"""
        print("🌐 启动HTML5服务器...")
        html5_script = self.project_root / "runtime" / "html5" / "h5Server.py"
        
        cmd = [
            sys.executable, str(html5_script),
            "--host", "0.0.0.0",
            "--port", "1337"
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.project_root)
            )
            self.processes.append(("HTML5服务器", process))
            print("✅ HTML5服务器启动成功")
            print("   访问地址: http://127.0.0.1:1337/static/index.html")
            return True
        except Exception as e:
            print(f"❌ HTML5服务器启动失败: {e}")
            return False
    
    def start_websocket_server(self):
        """启动WebSocket服务器"""
        print("🎤 启动WebSocket语音识别服务器...")
        ws_script = self.project_root / "runtime" / "python" / "websocket" / "funasr_wss_server.py"
        
        cmd = [
            sys.executable, str(ws_script),
            "--port", "10095",
            "--host", "0.0.0.0"
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.project_root)
            )
            self.processes.append(("WebSocket服务器", process))
            print("✅ WebSocket服务器启动成功")
            print("   服务地址: ws://127.0.0.1:10095")
            return True
        except Exception as e:
            print(f"❌ WebSocket服务器启动失败: {e}")
            return False
    
    def check_dependencies(self):
        """检查依赖是否安装"""
        print("🔍 检查依赖...")
        
        required_packages = ['flask', 'funasr', 'modelscope', 'websockets']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"   ✅ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"   ❌ {package} (缺失)")
        
        if missing_packages:
            print(f"\n📦 需要安装缺失的包:")
            print(f"   pip install {' '.join(missing_packages)}")
            return False
        
        print("✅ 所有依赖已安装")
        return True
    
    def monitor_processes(self):
        """监控进程状态"""
        while True:
            for name, process in self.processes:
                if process.poll() is not None:
                    print(f"⚠️  {name} 进程已退出")
                    # 读取错误输出
                    stderr = process.stderr.read().decode('utf-8', errors='ignore')
                    if stderr:
                        print(f"   错误信息: {stderr}")
            time.sleep(5)
    
    def stop_all_services(self):
        """停止所有服务"""
        print("\n🛑 正在停止所有服务...")
        
        for name, process in self.processes:
            if process.poll() is None:
                print(f"   停止 {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    
        print("✅ 所有服务已停止")
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        self.stop_all_services()
        sys.exit(0)
    
    def start_all(self):
        """启动所有服务"""
        print("🚀 FunASR 服务启动器")
        print("=" * 50)
        
        # 检查依赖
        if not self.check_dependencies():
            return False
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 启动服务
        html5_ok = self.start_html5_server()
        time.sleep(2)  # 等待HTML5服务器启动
        
        ws_ok = self.start_websocket_server()
        time.sleep(3)  # 等待WebSocket服务器启动
        
        if html5_ok and ws_ok:
            print("\n🎉 所有服务启动成功!")
            print("=" * 50)
            print("📱 Web界面: http://127.0.0.1:1337/static/index.html")
            print("🔌 WebSocket: ws://127.0.0.1:10095")
            print("=" * 50)
            print("💡 使用说明:")
            print("   1. 打开Web界面")
            print("   2. 输入WebSocket地址: ws://127.0.0.1:10095")
            print("   3. 点击连接开始语音识别")
            print("   4. 按 Ctrl+C 停止服务")
            print("=" * 50)
            
            # 启动监控线程
            monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
            monitor_thread.start()
            
            # 保持主线程运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop_all_services()
        else:
            print("❌ 服务启动失败")
            return False

def main():
    service = FunASRService()
    service.start_all()

if __name__ == "__main__":
    main() 