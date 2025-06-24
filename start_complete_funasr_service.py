#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunASR 完整服务启动脚本
同时启动文件上传服务器和实时WebSocket语音识别服务器
"""

import subprocess
import time
import os
import sys
import signal
import threading
from pathlib import Path
import argparse

class CompleteFunASRService:
    def __init__(self):
        self.processes = []
        self.project_root = Path(__file__).parent
        
    def start_upload_server(self, model_type="paraformer", device="cuda", ngpu=1):
        """启动文件上传服务器"""
        print("📁 启动文件上传服务器...")
        upload_script = self.project_root / "runtime" / "python" / "websocket" / "funasr_upload_server.py"
        
        cmd = [
            sys.executable, str(upload_script),
            "--host", "0.0.0.0",
            "--http_port", "8080",
            "--port", "10096",  # 使用不同的端口避免冲突
            "--model_type", model_type,
            "--device", device,
            "--ngpu", str(ngpu)
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.project_root)
            )
            self.processes.append(("文件上传服务器", process))
            print("✅ 文件上传服务器启动成功")
            print(f"   HTTP服务: http://0.0.0.0:8080")
            print(f"   实时录音页面: http://your-domain:8080/realtime")
            return True
        except Exception as e:
            print(f"❌ 文件上传服务器启动失败: {e}")
            return False
    
    def start_realtime_websocket_server(self, device="cuda", ngpu=1):
        """启动实时WebSocket语音识别服务器"""
        print("🎤 启动实时WebSocket语音识别服务器...")
        ws_script = self.project_root / "runtime" / "python" / "websocket" / "funasr_wss_server.py"
        
        cmd = [
            sys.executable, str(ws_script),
            "--host", "0.0.0.0",
            "--port", "10095",
            "--device", device,
            "--ngpu", str(ngpu),
            "--certfile", "",  # 禁用SSL证书
            "--keyfile", ""    # 禁用SSL密钥
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.project_root)
            )
            self.processes.append(("实时WebSocket服务器", process))
            print("✅ 实时WebSocket服务器启动成功")
            print(f"   WebSocket服务: ws://0.0.0.0:10095")
            return True
        except Exception as e:
            print(f"❌ 实时WebSocket服务器启动失败: {e}")
            return False
    
    def check_dependencies(self):
        """检查依赖是否安装"""
        print("🔍 检查依赖...")
        
        required_packages = ['funasr', 'websockets', 'aiohttp', 'aiohttp_cors']
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
    
    def start_all(self, model_type="paraformer", device="cuda", ngpu=1):
        """启动所有服务"""
        print("🚀 FunASR 完整服务启动器")
        print("=" * 60)
        print(f"🎯 模型类型: {model_type}")
        print(f"🖥️  设备: {device}")
        print(f"🔢 GPU数量: {ngpu}")
        print("=" * 60)
        
        # 检查依赖
        if not self.check_dependencies():
            return False
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 启动服务
        upload_ok = self.start_upload_server(model_type, device, ngpu)
        time.sleep(3)  # 等待上传服务器启动
        
        realtime_ok = self.start_realtime_websocket_server(device, ngpu)
        time.sleep(3)  # 等待WebSocket服务器启动
        
        if upload_ok and realtime_ok:
            print("\n🎉 所有服务启动成功!")
            print("=" * 60)
            print("📁 文件上传服务:")
            print("   HTTP上传: https://gpu-cqao559xgb-8080.node.inscode.run/")
            print("   实时录音页面: https://gpu-cqao559xgb-8080.node.inscode.run/realtime")
            print("")
            print("🎤 实时语音识别:")
            print("   WebSocket: wss://gpu-cqao559xgb-10095.node.inscode.run/")
            print("")
            print("💡 功能说明:")
            print("   1. 文件上传: 支持MP3、WAV、M4A等格式的音频文件识别")
            print("   2. 实时录音: 支持麦克风实时语音识别")
            print("   3. 说话人分离: 自动识别不同说话人")
            print("   4. 热词支持: 可配置专业词汇提升识别准确率")
            print("")
            print("🔧 使用方法:")
            print("   - 文件上传: 直接访问上传页面，选择音频文件上传")
            print("   - 实时录音: 访问实时录音页面，点击连接后开始录音")
            print("   - 按 Ctrl+C 停止所有服务")
            print("=" * 60)
            
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
    parser = argparse.ArgumentParser(description="FunASR 完整服务启动器")
    parser.add_argument("--model_type", type=str, default="paraformer", 
                       choices=["paraformer", "whisper", "sensevoice", "hybrid"],
                       help="模型类型")
    parser.add_argument("--device", type=str, default="cuda", 
                       choices=["cuda", "cpu"],
                       help="设备类型")
    parser.add_argument("--ngpu", type=int, default=1, help="GPU数量")
    
    args = parser.parse_args()
    
    service = CompleteFunASRService()
    service.start_all(args.model_type, args.device, args.ngpu)

if __name__ == "__main__":
    main() 