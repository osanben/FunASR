#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的FunASR HTTP服务器
提供静态文件和诊断工具
"""

import os
import sys
import http.server
import socketserver
import webbrowser
import threading
import time
from urllib.parse import unquote

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # URL解码
        path = unquote(self.path)
        
        print(f"请求路径: {path}")
        
        # 处理根路径和dashboard
        if path == '/' or path == '/dashboard':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html_content = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>FunASR 服务中心</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .card { background: #f8f9fa; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #007bff; }
        .card h3 { margin-top: 0; color: #007bff; }
        .button { display: inline-block; padding: 12px 24px; margin: 8px; background: #007bff; color: white; text-decoration: none; border-radius: 6px; transition: background 0.3s; }
        .button:hover { background: #0056b3; }
        .button.success { background: #28a745; }
        .button.warning { background: #ffc107; color: #212529; }
        .button.info { background: #17a2b8; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .status.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status.warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .status.info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎤 FunASR 服务中心</h1>
            <p>语音识别图形化界面和诊断工具</p>
        </div>
        
        <div class="status success">
            <strong>✅ 服务状态：</strong> HTTP服务正常运行在端口1337
        </div>
        
        <div class="card">
            <h3>🚀 快速开始</h3>
            <p>选择你需要的功能：</p>
            <a href="/dashboard.html" class="button success">🎯 FunASR Dashboard</a>
            <a href="/static/index.html" class="button">🎤 完整演示界面</a>
            <a href="/诊断安全问题.html" class="button warning">🔍 安全诊断工具</a>
        </div>
        
        <div class="card">
            <h3>📋 服务信息</h3>
            <ul>
                <li><strong>HTTP服务：</strong> http://127.0.0.1:1337</li>
                <li><strong>WebSocket服务：</strong> ws://127.0.0.1:10095</li>
                <li><strong>当前目录：</strong> ''' + os.getcwd() + '''</li>
            </ul>
        </div>
        
        <div class="card">
            <h3>🛠️ 常用链接</h3>
            <ul>
                <li><a href="/test_funasr.py" target="_blank">查看测试脚本</a></li>
                <li><a href="/quick_start.py" target="_blank">查看快速开始脚本</a></li>
                <li><a href="/我的FunASR使用指南.md" target="_blank">查看使用指南</a></li>
            </ul>
        </div>
        
        <div class="card">
            <h3>🎯 下一步操作</h3>
            <ol>
                <li>点击"安全诊断工具"检查WebSocket连接状态</li>
                <li>确认麦克风权限已授予</li>
                <li>使用"完整演示界面"进行语音识别</li>
            </ol>
        </div>
    </div>
    
    <script>
        // 自动检查WebSocket连接
        function checkWebSocketConnection() {
            try {
                const ws = new WebSocket('ws://127.0.0.1:10095');
                ws.onopen = function() {
                    console.log('WebSocket连接成功');
                    ws.close();
                };
                ws.onerror = function() {
                    console.log('WebSocket连接失败');
                };
            } catch (error) {
                console.log('WebSocket测试失败:', error);
            }
        }
        
        // 页面加载后检查连接
        window.onload = function() {
            setTimeout(checkWebSocketConnection, 1000);
        };
    </script>
</body>
</html>
            '''
            
            self.wfile.write(html_content.encode('utf-8'))
            return
        
        # 处理static路径 - 映射到runtime/html5/static
        if path.startswith('/static/'):
            static_file = path[8:]  # 移除 '/static/' 前缀
            static_path = os.path.join('runtime', 'html5', 'static', static_file)
            
            if os.path.exists(static_path):
                self.send_response(200)
                
                # 根据文件扩展名设置Content-Type
                if static_file.endswith('.html'):
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                elif static_file.endswith('.js'):
                    self.send_header('Content-type', 'application/javascript; charset=utf-8')
                elif static_file.endswith('.css'):
                    self.send_header('Content-type', 'text/css; charset=utf-8')
                else:
                    self.send_header('Content-type', 'application/octet-stream')
                
                self.end_headers()
                
                with open(static_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(f"文件 {static_file} 不存在".encode('utf-8'))
                return
            
        # 处理静态文件
        return super().do_GET()
    
    def log_message(self, format, *args):
        # 自定义日志格式
        print(f"[{time.strftime('%H:%M:%S')}] {format % args}")

def start_server():
    """启动HTTP服务器"""
    PORT = 1337
    
    print("🌐" + "=" * 50 + "🌐")
    print("      🎤 FunASR 简单服务器启动中...")
    print("🌐" + "=" * 50 + "🌐")
    
    try:
        with socketserver.TCPServer(("127.0.0.1", PORT), CustomHTTPRequestHandler) as httpd:
            print(f"\n✅ 服务器启动成功！")
            print(f"📱 访问地址: http://127.0.0.1:{PORT}")
            print(f"🔍 诊断工具: http://127.0.0.1:{PORT}/诊断安全问题.html")
            print(f"🎤 完整界面: http://127.0.0.1:{PORT}/static/index.html")
            print(f"\n⏹️  按 Ctrl+C 停止服务")
            print("🌐" + "=" * 50 + "🌐")
            
            # 自动打开浏览器
            def open_browser():
                time.sleep(2)
                try:
                    webbrowser.open(f'http://127.0.0.1:{PORT}')
                except:
                    pass
            
            threading.Thread(target=open_browser, daemon=True).start()
            
            # 启动服务器
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n\n🛑 服务器已停止")
    except Exception as e:
        print(f"\n❌ 服务器启动失败: {e}")
        print("💡 可能端口1337已被占用，请尝试关闭其他服务")

if __name__ == "__main__":
    # 确保在正确的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print(f"📁 当前工作目录: {os.getcwd()}")
    print(f"📄 可用文件: {[f for f in os.listdir('.') if f.endswith(('.html', '.py', '.md'))][:10]}")
    
    start_server() 