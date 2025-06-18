
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
            resultArea.value = '正在测试WebSocket连接...\n';
            
            try {
                const ws = new WebSocket('ws://127.0.0.1:10095');
                
                ws.onopen = function() {
                    resultArea.value += '✅ WebSocket连接成功！\n';
                    ws.close();
                };
                
                ws.onerror = function() {
                    resultArea.value += '❌ WebSocket连接失败，请确保ASR服务正在运行\n';
                };
                
                ws.onclose = function() {
                    resultArea.value += '🔌 连接已关闭\n';
                };
                
            } catch (error) {
                resultArea.value += '❌ 连接测试失败: ' + error.message + '\n';
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
                
                resultArea.value = '📁 文件上传功能需要完整的WebSocket服务支持\n';
                resultArea.value += '💡 请启动完整服务后使用文件识别功能\n';
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
