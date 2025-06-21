#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import sys
import time
import os
import signal

def start_h5_server():
    """启动HTML5服务器"""
    try:
        print("🚀 启动HTML5服务器...")
        os.chdir("runtime/html5")
        h5_process = subprocess.Popen([
            sys.executable, "h5Server.py", 
            "--host", "0.0.0.0", 
            "--port", "1337"
        ])
        print(f"✅ HTML5服务器已启动 (PID: {h5_process.pid})")
        print("📱 访问地址: https://127.0.0.1:1337/static/index.html")
        print("🎛️ Dashboard: https://127.0.0.1:1337/static/dashboard.html")
        return h5_process
    except Exception as e:
        print(f"❌ HTML5服务器启动失败: {e}")
        return None

def start_websocket_server():
    """启动WebSocket服务器"""
    try:
        print("\n🚀 启动WebSocket服务器...")
        os.chdir("../python/websocket")
        ws_process = subprocess.Popen([
            sys.executable, "funasr_wss_server.py",
            "--port", "10095",
            "--host", "0.0.0.0"
        ])
        print(f"✅ WebSocket服务器已启动 (PID: {ws_process.pid})")
        print("🔗 WebSocket地址: wss://127.0.0.1:10095")
        return ws_process
    except Exception as e:
        print(f"❌ WebSocket服务器启动失败: {e}")
        return None

def signal_handler(sig, frame):
    """信号处理器"""
    print("\n🛑 收到停止信号，正在关闭服务...")
    sys.exit(0)

def main():
    print("🎯 FunASR 服务启动器")
    print("=" * 50)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 回到项目根目录
    os.chdir("/Users/csdn/github_projects/FunASR")
    
    # 启动HTML5服务器
    h5_process = start_h5_server()
    if not h5_process:
        return
    
    # 等待HTML5服务器启动
    time.sleep(2)
    
    # 启动WebSocket服务器
    ws_process = start_websocket_server()
    if not ws_process:
        h5_process.terminate()
        return
    
    print("\n" + "=" * 50)
    print("🎉 所有服务启动成功！")
    print("📋 服务信息:")
    print(f"   📱 HTML5服务器: PID {h5_process.pid}, 端口 1337")
    print(f"   🔗 WebSocket服务器: PID {ws_process.pid}, 端口 10095")
    print("\n🌐 访问地址:")
    print("   原版界面: https://127.0.0.1:1337/static/index.html")
    print("   Dashboard: https://127.0.0.1:1337/static/dashboard.html")
    print("\n💡 提示: 按 Ctrl+C 停止所有服务")
    print("=" * 50)
    
    try:
        # 等待进程
        while True:
            # 检查进程是否还在运行
            if h5_process.poll() is not None:
                print("❌ HTML5服务器已停止")
                break
            if ws_process.poll() is not None:
                print("❌ WebSocket服务器已停止")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 收到停止信号...")
    finally:
        # 清理进程
        print("🧹 清理进程...")
        try:
            h5_process.terminate()
            ws_process.terminate()
            time.sleep(2)
            if h5_process.poll() is None:
                h5_process.kill()
            if ws_process.poll() is None:
                ws_process.kill()
        except:
            pass
        print("✅ 所有服务已停止")

if __name__ == "__main__":
    main() 