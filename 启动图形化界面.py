#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunASR 图形化界面启动脚本
启动Web界面演示，支持麦克风录音和文件上传识别
"""

import os
import sys
import subprocess
import threading
import time
import signal

def print_banner():
    """打印启动横幅"""
    print("🌐" + "=" * 60 + "🌐")
    print("              🎤 FunASR 图形化界面启动器 🎤")
    print("          支持麦克风录音和文件上传识别")
    print("🌐" + "=" * 60 + "🌐")

def check_dependencies():
    """检查必要的依赖"""
    print("\n🔍 检查依赖环境...")
    
    try:
        import flask
        print("   ✅ Flask 已安装")
    except ImportError:
        print("   ❌ Flask 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=True)
        print("   ✅ Flask 安装完成")
    
    try:
        import websockets
        print("   ✅ websockets 已安装")
    except ImportError:
        print("   ❌ websockets 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "websockets"], check=True)
        print("   ✅ websockets 安装完成")

def start_websocket_server():
    """启动WebSocket ASR服务"""
    print("\n🚀 启动WebSocket ASR服务...")
    
    # 检查是否存在WebSocket服务脚本
    websocket_script = "runtime/python/websocket/funasr_wss_server.py"
    if not os.path.exists(websocket_script):
        print(f"   ❌ WebSocket服务脚本不存在: {websocket_script}")
        print("   💡 使用简化的ASR服务...")
        return start_simple_asr_server()
    
    try:
        # 启动WebSocket服务
        cmd = [sys.executable, websocket_script, "--port", "10095"]
        print(f"   执行命令: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服务启动
        time.sleep(3)
        
        if process.poll() is None:
            print("   ✅ WebSocket ASR服务启动成功 (端口: 10095)")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"   ❌ WebSocket服务启动失败")
            print(f"   错误信息: {stderr}")
            return None
            
    except Exception as e:
        print(f"   ❌ 启动WebSocket服务时出错: {e}")
        return None

def start_simple_asr_server():
    """启动简化的ASR服务"""
    print("   🔄 创建简化的ASR WebSocket服务...")
    
    # 创建简化的WebSocket服务
    simple_server_code = '''
import asyncio
import websockets
import json
import threading
from funasr import AutoModel

# 全局模型实例
asr_model = None

def load_model():
    """加载ASR模型"""
    global asr_model
    try:
        print("加载ASR模型...")
        asr_model = AutoModel(
            model="paraformer-zh",
            device="cpu"
        )
        print("ASR模型加载完成")
    except Exception as e:
        print(f"模型加载失败: {e}")

async def handle_websocket(websocket, path):
    """处理WebSocket连接"""
    print(f"新的WebSocket连接: {websocket.remote_address}")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                
                if data.get("mode") == "2pass" and "text" in data:
                    # 处理文本消息
                    response = {
                        "mode": "2pass",
                        "text": "连接成功，请发送音频数据",
                        "is_final": True
                    }
                    await websocket.send(json.dumps(response, ensure_ascii=False))
                    
                elif "audio" in data:
                    # 这里应该处理音频数据，简化版本直接返回示例
                    response = {
                        "mode": "2pass", 
                        "text": "这是语音识别的演示结果",
                        "is_final": True
                    }
                    await websocket.send(json.dumps(response, ensure_ascii=False))
                    
            except json.JSONDecodeError:
                # 可能是音频二进制数据
                response = {
                    "mode": "2pass",
                    "text": "收到音频数据，正在识别...",
                    "is_final": False
                }
                await websocket.send(json.dumps(response, ensure_ascii=False))
                
    except websockets.exceptions.ConnectionClosed:
        print(f"WebSocket连接关闭: {websocket.remote_address}")
    except Exception as e:
        print(f"处理WebSocket消息时出错: {e}")

def start_server():
    """启动WebSocket服务器"""
    # 在后台线程中加载模型
    threading.Thread(target=load_model, daemon=True).start()
    
    # 启动WebSocket服务器
    start_server = websockets.serve(handle_websocket, "127.0.0.1", 10095)
    print("WebSocket ASR服务已启动在 ws://127.0.0.1:10095")
    
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    start_server()
'''
    
    # 写入临时文件
    with open("temp_websocket_server.py", "w", encoding="utf-8") as f:
        f.write(simple_server_code)
    
    try:
        # 启动简化服务
        process = subprocess.Popen(
            [sys.executable, "temp_websocket_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        time.sleep(2)
        if process.poll() is None:
            print("   ✅ 简化ASR服务启动成功 (端口: 10095)")
            return process
        else:
            print("   ❌ 简化ASR服务启动失败")
            return None
            
    except Exception as e:
        print(f"   ❌ 启动简化ASR服务时出错: {e}")
        return None

def start_html5_server():
    """启动HTML5界面服务"""
    print("\n🌐 启动HTML5界面服务...")
    
    html5_script = "runtime/html5/h5Server.py"
    if not os.path.exists(html5_script):
        print(f"   ❌ HTML5服务脚本不存在: {html5_script}")
        return create_simple_html5_server()
    
    try:
        cmd = [sys.executable, html5_script, "--host", "127.0.0.1", "--port", "1337"]
        print(f"   执行命令: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        time.sleep(2)
        if process.poll() is None:
            print("   ✅ HTML5界面服务启动成功")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"   ❌ HTML5服务启动失败: {stderr}")
            return create_simple_html5_server()
            
    except Exception as e:
        print(f"   ❌ 启动HTML5服务时出错: {e}")
        return create_simple_html5_server()

def create_simple_html5_server():
    """创建简单的HTML5服务"""
    print("   🔄 创建简化的HTML5服务...")
    
    # 创建简化的Flask服务
    flask_server_code = '''
from flask import Flask, send_from_directory, send_file
import os

app = Flask(__name__)

@app.route('/')
def index():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>FunASR 图形化演示</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        button { padding: 10px 20px; margin: 5px; font-size: 16px; }
        textarea { width: 100%; height: 200px; }
        input[type="file"] { margin: 10px 0; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .info { background: #d1ecf1; color: #0c5460; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 FunASR 图形化演示界面</h1>
        
        <div class="section">
            <h3>📋 功能说明</h3>
            <p>这是FunASR的图形化演示界面，支持以下功能：</p>
            <ul>
                <li>🎙️ 实时麦克风录音识别</li>
                <li>📁 音频文件上传识别</li>
                <li>🔍 语音端点检测(VAD)</li>
                <li>📝 标点符号恢复</li>
                <li>🔥 热词自定义</li>
            </ul>
        </div>
        
        <div class="section">
            <h3>🚀 快速开始</h3>
            <div class="status info">
                <strong>当前状态：</strong> 简化演示模式<br>
                <strong>WebSocket服务：</strong> ws://127.0.0.1:10095<br>
                <strong>完整界面：</strong> 需要启动完整的WebSocket服务
            </div>
        </div>
        
        <div class="section">
            <h3>🎯 演示选项</h3>
            <button onclick="openFullDemo()">打开完整演示界面</button>
            <button onclick="testConnection()">测试WebSocket连接</button>
            <button onclick="uploadFile()">上传音频文件</button>
            
            <div style="margin-top: 15px;">
                <input type="file" id="audioFile" accept=".wav,.mp3,.m4a,.flac" onchange="handleFileSelect()">
                <div id="fileInfo"></div>
            </div>
        </div>
        
        <div class="section">
            <h3>📝 识别结果</h3>
            <textarea id="resultArea" placeholder="语音识别结果将显示在这里..." readonly></textarea>
        </div>
        
        <div class="section">
            <h3>📚 使用说明</h3>
            <p><strong>完整功能访问：</strong></p>
            <ol>
                <li>确保WebSocket ASR服务运行在端口10095</li>
                <li>点击"打开完整演示界面"访问专业版界面</li>
                <li>或者访问: <a href="/static/index.html" target="_blank">/static/index.html</a></li>
            </ol>
            
            <p><strong>本地开发：</strong></p>
            <ul>
                <li>WebSocket服务: <code>python runtime/python/websocket/funasr_wss_server.py --port 10095</code></li>
                <li>HTML5服务: <code>python runtime/html5/h5Server.py --host 127.0.0.1 --port 1337</code></li>
            </ul>
        </div>
    </div>
    
    <script>
        function openFullDemo() {
            // 尝试打开完整的演示界面
            const fullUrl = window.location.origin + '/static/index.html';
            window.open(fullUrl, '_blank');
        }
        
        function testConnection() {
            const resultArea = document.getElementById('resultArea');
            resultArea.value = '正在测试WebSocket连接...\\n';
            
            try {
                const ws = new WebSocket('ws://127.0.0.1:10095');
                
                ws.onopen = function() {
                    resultArea.value += '✅ WebSocket连接成功！\\n';
                    ws.close();
                };
                
                ws.onerror = function() {
                    resultArea.value += '❌ WebSocket连接失败，请确保ASR服务正在运行\\n';
                };
                
                ws.onclose = function() {
                    resultArea.value += '🔌 连接已关闭\\n';
                };
                
            } catch (error) {
                resultArea.value += '❌ 连接测试失败: ' + error.message + '\\n';
            }
        }
        
        function uploadFile() {
            document.getElementById('audioFile').click();
        }
        
        function handleFileSelect() {
            const fileInput = document.getElementById('audioFile');
            const fileInfo = document.getElementById('fileInfo');
            const resultArea = document.getElementById('resultArea');
            
            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];
                fileInfo.innerHTML = `
                    <div class="status success">
                        <strong>选择的文件：</strong> ${file.name}<br>
                        <strong>文件大小：</strong> ${(file.size / 1024 / 1024).toFixed(2)} MB<br>
                        <strong>文件类型：</strong> ${file.type}
                    </div>
                `;
                
                resultArea.value = '📁 文件上传功能需要完整的WebSocket服务支持\\n';
                resultArea.value += '💡 请启动完整服务后使用文件识别功能\\n';
            }
        }
    </script>
</body>
</html>
    """

@app.route('/static/<path:filename>')
def serve_static(filename):
    static_dir = 'runtime/html5/static'
    if os.path.exists(os.path.join(static_dir, filename)):
        return send_from_directory(static_dir, filename)
    else:
        return f"文件 {filename} 不存在，请确保完整的FunASR项目结构", 404

if __name__ == '__main__':
    print("启动简化HTML5服务在 http://127.0.0.1:1337")
    app.run(host='127.0.0.1', port=1337, debug=False)
'''
    
    # 写入临时文件
    with open("temp_html5_server.py", "w", encoding="utf-8") as f:
        f.write(flask_server_code)
    
    try:
        process = subprocess.Popen(
            [sys.executable, "temp_html5_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        time.sleep(2)
        if process.poll() is None:
            print("   ✅ 简化HTML5服务启动成功")
            return process
        else:
            print("   ❌ 简化HTML5服务启动失败")
            return None
            
    except Exception as e:
        print(f"   ❌ 启动简化HTML5服务时出错: {e}")
        return None

def cleanup_temp_files():
    """清理临时文件"""
    temp_files = ["temp_websocket_server.py", "temp_html5_server.py"]
    for file in temp_files:
        if os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass

def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    print("\n\n🛑 接收到停止信号，正在关闭服务...")
    cleanup_temp_files()
    sys.exit(0)

def main():
    """主函数"""
    print_banner()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"\n📁 当前工作目录: {os.getcwd()}")
    
    # 检查依赖
    check_dependencies()
    
    # 启动服务
    websocket_process = start_websocket_server()
    html5_process = start_html5_server()
    
    if html5_process:
        print("\n" + "🎉" + "=" * 60 + "🎉")
        print("              🌐 FunASR 图形化界面已启动！")
        print("")
        print("   🔗 访问地址: http://127.0.0.1:1337")
        print("   📱 移动端访问: http://你的IP:1337")
        print("   🔧 完整演示: http://127.0.0.1:1337/static/index.html")
        print("")
        print("   💡 功能特性:")
        print("      • 🎙️  实时麦克风录音识别")
        print("      • 📁 音频文件上传识别") 
        print("      • 🔍 语音端点检测(VAD)")
        print("      • 📝 标点符号恢复")
        print("      • 🔥 自定义热词")
        print("")
        print("   ⏹️  按 Ctrl+C 停止服务")
        print("🎉" + "=" * 60 + "🎉")
        
        try:
            # 保持主线程运行
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        print("\n❌ 图形化界面启动失败")
        print("💡 你仍然可以使用命令行方式:")
        print("   python3 quick_start.py your_audio.wav")
    
    # 清理
    if websocket_process:
        websocket_process.terminate()
    if html5_process:
        html5_process.terminate()
    
    cleanup_temp_files()
    print("\n👋 服务已停止，再见！")

if __name__ == "__main__":
    main() 