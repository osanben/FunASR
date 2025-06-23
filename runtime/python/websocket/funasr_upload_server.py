#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import json
import ssl
import uuid
import os
import time
from pathlib import Path
import numpy as np
import websockets
from concurrent.futures import ThreadPoolExecutor
import threading
from aiohttp import web, web_request
import aiohttp_cors
import tempfile
import shutil
try:
    from opencc import OpenCC  # 繁简转换
    cc = OpenCC('t2s')  # 繁体转简体
    OPENCC_AVAILABLE = True
except ImportError:
    print("📋 提示: 安装 opencc-python-reimplemented 可启用繁简转换功能")
    OPENCC_AVAILABLE = False

try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    print("📋 提示: 安装 pyannote.audio 可启用说话人分离功能")
    PYANNOTE_AVAILABLE = False

# 存储WebSocket连接和任务状态
websocket_connections = {}
task_results = {}
task_lock = threading.Lock()

# 线程池用于音频处理
executor = ThreadPoolExecutor(max_workers=4)

# 解析命令行参数
parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="127.0.0.1", help="WebSocket服务器地址")
parser.add_argument("--port", type=int, default=10095, help="WebSocket端口")
parser.add_argument("--http_port", type=int, default=8080, help="HTTP上传服务端口")
parser.add_argument("--model_type", type=str, default="whisper", choices=["whisper", "paraformer", "sensevoice", "hybrid"], help="模型类型")
parser.add_argument("--whisper_model", type=str, default="base", help="Whisper模型大小")
parser.add_argument("--whisper_language", type=str, default="auto", help="Whisper识别语言")
parser.add_argument("--device", type=str, default="cpu", help="设备类型")
parser.add_argument("--ngpu", type=int, default=1, help="GPU数量")
parser.add_argument("--ncpu", type=int, default=4, help="CPU数量")
parser.add_argument("--upload_dir", type=str, default="./uploads", help="文件上传目录")

args = parser.parse_args()

# 创建上传目录
os.makedirs(args.upload_dir, exist_ok=True)

# 加载模型
model_whisper = None
model_asr = None

print("🚀 正在加载模型...")

# 加载Whisper模型
if args.model_type in ["whisper", "hybrid"]:
    try:
        import whisper
        device = "cpu" if args.device == "mps" else args.device
        print(f"📦 加载 Whisper {args.whisper_model} 模型... (设备: {device})")
        model_whisper = whisper.load_model(args.whisper_model, device=device)
        if hasattr(model_whisper, 'half'):
            model_whisper = model_whisper.float()
        print(f"✅ Whisper {args.whisper_model} 模型加载成功!")
    except Exception as e:
        print(f"❌ Whisper 模型加载失败: {e}")

# 加载FunASR模型
if args.model_type in ["paraformer", "sensevoice", "hybrid"]:
    try:
        from funasr import AutoModel
        
        device = "cpu" if args.device == "mps" else args.device
        ngpu = 0 if args.device == "mps" else args.ngpu
        
        if args.model_type in ["paraformer", "hybrid"]:
            print("📦 加载 Paraformer 模型...")
            model_asr = AutoModel(
                model="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
                punc_model="iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
                spk_model="iic/speech_campplus_sv_zh-cn_16k-common",
                ngpu=ngpu,
                ncpu=args.ncpu,
                device=device,
                disable_pbar=True,
                disable_log=True,
            )
        elif args.model_type == "sensevoice":
            print("📦 加载 SenseVoice 模型...")
            model_asr = AutoModel(
                model="iic/SenseVoiceSmall",
                ngpu=ngpu,
                ncpu=args.ncpu,
                device=device,
                disable_pbar=True,
                disable_log=True,
            )
        print("✅ FunASR 模型加载成功!")
    except Exception as e:
        print(f"❌ FunASR 模型加载失败: {e}")

print("🎉 所有模型加载完成!")

def process_audio_file(file_path, task_id, model_type):
    """处理音频文件的主函数"""
    try:
        print(f"🎵 开始处理任务 {task_id}: {file_path}")
        
        # 更新任务状态
        with task_lock:
            task_results[task_id] = {"status": "processing", "progress": 0}
        
        # 发送处理开始通知
        send_progress_update(task_id, "processing", 10, "开始音频处理...")
        
        # 加载音频文件
        import librosa
        audio_data, sample_rate = librosa.load(file_path, sr=16000, dtype=np.float32)
        
        send_progress_update(task_id, "processing", 30, "音频文件加载完成...")
        
        print(f"📊 音频信息: 长度={len(audio_data)/16000:.2f}秒, 采样率={sample_rate}Hz")
        
        results = {}
        
        # Whisper处理
        if model_type in ["whisper", "hybrid"] and model_whisper:
            send_progress_update(task_id, "processing", 50, "Whisper识别中...")
            print("🎯 开始Whisper处理...")
            
            start_time = time.time()
            whisper_result = whisper_transcribe(audio_data, sample_rate)
            end_time = time.time()
            
            results["whisper"] = whisper_result
            print(f"✅ Whisper处理完成，耗时: {end_time - start_time:.2f}秒")
        
        # FunASR处理
        if model_type in ["paraformer", "sensevoice", "hybrid"] and model_asr:
            send_progress_update(task_id, "processing", 70, "FunASR识别中...")
            print("🎯 开始FunASR处理...")
            
            start_time = time.time()
            funasr_result = funasr_transcribe(audio_data, sample_rate)
            end_time = time.time()
            
            results["funasr"] = funasr_result
            print(f"✅ FunASR处理完成，耗时: {end_time - start_time:.2f}秒")
        
        # 更新最终结果
        with task_lock:
            task_results[task_id] = {
                "status": "completed",
                "progress": 100,
                "results": results,
                "file_info": {
                    "duration": len(audio_data) / 16000,
                    "sample_rate": sample_rate,
                    "samples": len(audio_data)
                }
            }
        
        # 发送完成通知
        send_progress_update(task_id, "completed", 100, "处理完成!", results)
        
        # 清理临时文件
        try:
            os.remove(file_path)
            print(f"🗑️ 清理临时文件: {file_path}")
        except:
            pass
            
    except Exception as e:
        print(f"❌ 处理任务 {task_id} 失败: {e}")
        import traceback
        traceback.print_exc()
        
        with task_lock:
            task_results[task_id] = {
                "status": "error",
                "progress": 0,
                "error": str(e)
            }
        
        send_progress_update(task_id, "error", 0, f"处理失败: {str(e)}")

def whisper_transcribe(audio_data, sample_rate=16000):
    """使用Whisper进行语音识别"""
    try:
        # 确保数据格式正确
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # 确保数据范围在[-1, 1]
        if audio_data.max() > 1.0 or audio_data.min() < -1.0:
            audio_data = np.clip(audio_data, -1.0, 1.0)
        
        # Whisper识别
        language = None if args.whisper_language == "auto" else args.whisper_language
        
        options = {
            "language": language,
            "word_timestamps": True,
            "verbose": False,
            "fp16": False,
        }
        
        result = model_whisper.transcribe(audio_data, **options)
        
        text = result.get("text", "").strip()
        
        # 繁体转简体
        if OPENCC_AVAILABLE and text:
            try:
                text = cc.convert(text)
            except Exception as e:
                print(f"⚠️ 繁简转换失败: {e}")
        
        segments = result.get("segments", [])
        
        # 构建带时间戳的结果
        timestamp_text = ""
        for segment in segments:
            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            segment_text = segment.get("text", "").strip()
            if segment_text:
                # 繁体转简体
                if OPENCC_AVAILABLE:
                    try:
                        segment_text = cc.convert(segment_text)
                    except Exception as e:
                        print(f"⚠️ 片段繁简转换失败: {e}")
                timestamp_text += f"[{start_time:.2f}->{end_time:.2f}] {segment_text} "
        
        # 简单的说话人分离（基于音频能量变化）
        speaker_segments = detect_speakers_simple(audio_data, segments, sample_rate)
        
        return {
            "text": text,
            "timestamp": timestamp_text.strip(),
            "language": result.get("language", "unknown"),
            "segments": segments,
            "speaker_segments": speaker_segments
        }
        
    except Exception as e:
        print(f"❌ Whisper识别错误: {e}")
        return {"text": "", "timestamp": "", "language": "unknown", "segments": [], "speaker_segments": []}

def detect_speakers_simple(audio_data, segments, sample_rate=16000):
    """简单的说话人分离算法（基于音频能量和频谱变化）"""
    try:
        if not segments:
            return []
        
        speaker_segments = []
        current_speaker = 1
        prev_energy = 0
        
        for i, segment in enumerate(segments):
            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            text = segment.get("text", "").strip()
            
            # 计算当前片段的音频能量
            start_sample = int(start_time * sample_rate)
            end_sample = int(end_time * sample_rate)
            
            if start_sample < len(audio_data) and end_sample <= len(audio_data) and end_sample > start_sample:
                segment_audio = audio_data[start_sample:end_sample]
                if len(segment_audio) > 0:
                    energy = float(np.mean(segment_audio ** 2))
                    # 防止NaN和无穷大值
                    if np.isnan(energy) or np.isinf(energy):
                        energy = 0.0
                else:
                    energy = 0.0
                
                # 基于能量变化判断是否换人
                if prev_energy > 0 and energy > 0:
                    energy_change = abs(energy - prev_energy) / (prev_energy + 1e-8)
                    # 如果能量变化超过阈值，可能是换了说话人
                    if energy_change > 0.5 and i > 0:
                        current_speaker = 2 if current_speaker == 1 else 1
                
                # 繁体转简体
                if OPENCC_AVAILABLE and text:
                    try:
                        text = cc.convert(text)
                    except Exception as e:
                        print(f"⚠️ 说话人片段繁简转换失败: {e}")
                
                speaker_segments.append({
                    "start": start_time,
                    "end": end_time,
                    "text": text,
                    "speaker": f"说话人{current_speaker}",
                    "energy": energy
                })
                
                prev_energy = energy
            else:
                # 如果音频范围超出，使用默认值
                if OPENCC_AVAILABLE and text:
                    try:
                        text = cc.convert(text)
                    except Exception as e:
                        print(f"⚠️ 说话人片段繁简转换失败: {e}")
                        
                speaker_segments.append({
                    "start": start_time,
                    "end": end_time,
                    "text": text,
                    "speaker": f"说话人{current_speaker}",
                    "energy": 0.0
                })
        
        return speaker_segments
        
    except Exception as e:
        print(f"❌ 说话人检测错误: {e}")
        return []

def funasr_transcribe(audio_data, sample_rate=16000):
    """使用FunASR进行语音识别"""
    try:
        # 确保数据格式正确
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # FunASR识别
        res = model_asr.generate(
            input=audio_data,
            cache={},
            language="auto",
            use_itn=True,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
        )
        
        if res and len(res) > 0:
            result = res[0]
            text = result.get("text", "")
            
            # 处理时间戳
            timestamp_text = ""
            if "timestamp" in result:
                timestamps = result["timestamp"]
                if timestamps:
                    for i, (start, end) in enumerate(timestamps):
                        timestamp_text += f"[{start/1000:.2f}->{end/1000:.2f}] "
            
            return {
                "text": text,
                "timestamp": timestamp_text.strip(),
                "language": "zh",
                "result": result
            }
        else:
            return {"text": "", "timestamp": "", "language": "zh", "result": {}}
            
    except Exception as e:
        print(f"❌ FunASR识别错误: {e}")
        return {"text": "", "timestamp": "", "language": "zh", "result": {}, "speaker_segments": []}

def send_progress_update(task_id, status, progress, message, results=None):
    """发送进度更新到WebSocket客户端"""
    if task_id in websocket_connections:
        websocket = websocket_connections[task_id]
        try:
            update = {
                "type": "progress",
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "message": message,
                "timestamp": time.time()
            }
            
            if results:
                update["results"] = results
            
            # 使用asyncio发送消息
            asyncio.create_task(websocket.send(json.dumps(update, ensure_ascii=False)))
        except:
            pass

# 状态查询处理
def clean_nan_values(obj):
    """递归清理对象中的NaN值"""
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return 0.0
        return obj
    else:
        return obj

async def status_handler(request):
    """查询任务状态和结果"""
    task_id = request.match_info['task_id']
    
    with task_lock:
        if task_id in task_results:
            result = task_results[task_id]
            # 清理NaN值
            cleaned_result = clean_nan_values(result)
            return web.json_response(cleaned_result, dumps=lambda obj: json.dumps(obj, ensure_ascii=False, indent=2))
        else:
            return web.json_response({"error": "任务不存在"}, status=404)

# HTTP文件上传处理
async def upload_handler(request):
    """处理文件上传"""
    try:
        reader = await request.multipart()
        task_id = str(uuid.uuid4())
        
        async for field in reader:
            if field.name == 'audio_file':
                # 获取文件名和扩展名
                filename = field.filename or f"audio_{task_id}"
                file_ext = Path(filename).suffix.lower()
                
                # 检查文件类型
                allowed_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg'}
                if file_ext not in allowed_extensions:
                    return web.json_response({
                        "error": f"不支持的文件格式: {file_ext}",
                        "allowed": list(allowed_extensions)
                    }, status=400)
                
                # 保存文件
                file_path = os.path.join(args.upload_dir, f"{task_id}{file_ext}")
                
                with open(file_path, 'wb') as f:
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)
                
                file_size = os.path.getsize(file_path)
                print(f"📁 文件上传完成: {filename} ({file_size} 字节) -> {file_path}")
                
                # 提交处理任务
                executor.submit(process_audio_file, file_path, task_id, args.model_type)
                
                return web.json_response({
                    "task_id": task_id,
                    "message": "文件上传成功，开始处理",
                    "filename": filename,
                    "file_size": file_size
                })
        
        return web.json_response({"error": "未找到音频文件"}, status=400)
        
    except Exception as e:
        print(f"❌ 文件上传错误: {e}")
        return web.json_response({"error": str(e)}, status=500)

# WebSocket处理
async def websocket_handler(websocket, path):
    """WebSocket连接处理"""
    task_id = None
    try:
        print(f"🔗 新的WebSocket连接: {websocket.remote_address}")
        
        async for message in websocket:
            try:
                data = json.loads(message)
                
                if data.get("type") == "register":
                    task_id = data.get("task_id")
                    if task_id:
                        websocket_connections[task_id] = websocket
                        print(f"📝 注册WebSocket连接: {task_id}")
                        
                        # 发送当前任务状态
                        with task_lock:
                            if task_id in task_results:
                                result = task_results[task_id]
                                await websocket.send(json.dumps({
                                    "type": "status",
                                    "task_id": task_id,
                                    **result
                                }, ensure_ascii=False))
                
            except json.JSONDecodeError:
                print("❌ WebSocket消息JSON解析失败")
                
    except websockets.exceptions.ConnectionClosed:
        print("🔌 WebSocket连接关闭")
    except Exception as e:
        print(f"❌ WebSocket错误: {e}")
    finally:
        if task_id and task_id in websocket_connections:
            del websocket_connections[task_id]
            print(f"🗑️ 清理WebSocket连接: {task_id}")

# 创建HTTP应用
async def create_http_app():
    app = web.Application()
    
    # 配置CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # 添加路由
    app.router.add_post('/upload', upload_handler)
    app.router.add_get('/status/{task_id}', status_handler)
    
    # 添加静态文件服务（可选）
    app.router.add_get('/', lambda request: web.Response(text="""
<!DOCTYPE html>
<html>
<head>
    <title>FunASR 文件上传</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>FunASR 语音识别文件上传</h1>
    <form id="uploadForm" enctype="multipart/form-data">
        <input type="file" id="audioFile" accept=".mp3,.wav,.m4a,.aac,.flac,.ogg" required>
        <button type="submit">上传并识别</button>
    </form>
    <div id="status"></div>
    <button id="getResultBtn" style="display:none; margin: 10px 0; padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">获取识别结果</button>
    <div id="results"></div>
    
    <script>
        let ws = null;
        let currentTaskId = null;
        
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('audioFile');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('请选择音频文件');
                return;
            }
            
            const formData = new FormData();
            formData.append('audio_file', file);
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    currentTaskId = result.task_id;
                    document.getElementById('status').innerHTML = `<p>上传成功！任务ID: ${currentTaskId}</p><p>正在处理中，请稍候...</p>`;
                    
                    // 显示获取结果按钮
                    document.getElementById('getResultBtn').style.display = 'block';
                    
                    // 建立WebSocket连接
                    connectWebSocket(currentTaskId);
                } else {
                    document.getElementById('status').innerHTML = `<p style="color:red">错误: ${result.error}</p>`;
                }
            } catch (error) {
                document.getElementById('status').innerHTML = `<p style="color:red">上传失败: ${error}</p>`;
            }
        });
        
        function connectWebSocket(taskId) {
            ws = new WebSocket(`ws://localhost:10095`);
            
            ws.onopen = function() {
                ws.send(JSON.stringify({
                    type: 'register',
                    task_id: taskId
                }));
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === 'progress') {
                    document.getElementById('status').innerHTML = 
                        `<p>状态: ${data.status} | 进度: ${data.progress}% | ${data.message}</p>`;
                    
                    if (data.results) {
                        let resultsHtml = '<h3>识别结果:</h3>';
                        for (const [model, result] of Object.entries(data.results)) {
                            resultsHtml += `<h4>${model}:</h4>`;
                            resultsHtml += `<p><strong>文本:</strong> ${result.text}</p>`;
                            if (result.timestamp) {
                                resultsHtml += `<p><strong>时间戳:</strong> ${result.timestamp}</p>`;
                            }
                        }
                        document.getElementById('results').innerHTML = resultsHtml;
                    }
                }
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket错误:', error);
            };
        }
        
        // 获取结果按钮点击事件
        document.getElementById('getResultBtn').addEventListener('click', async function() {
            if (!currentTaskId) {
                alert('没有任务ID');
                return;
            }
            
            try {
                const response = await fetch(`/status/${currentTaskId}`);
                const result = await response.json();
                
                if (response.ok) {
                    displayResults(result);
                } else {
                    document.getElementById('results').innerHTML = `<p style="color:red">获取结果失败: ${result.error}</p>`;
                }
            } catch (error) {
                document.getElementById('results').innerHTML = `<p style="color:red">获取结果失败: ${error}</p>`;
            }
        });
        
        // 显示结果函数
        function displayResults(data) {
            let html = '<h3>🎯 识别结果</h3>';
            
            if (data.status === 'completed') {
                html += `<div style="background: #d4edda; padding: 10px; border-radius: 4px; margin: 10px 0;">
                    <strong>✅ 状态:</strong> 识别完成 (${data.progress}%)<br>
                    <strong>📊 音频时长:</strong> ${data.file_info.duration.toFixed(2)}秒<br>
                    <strong>🔊 采样率:</strong> ${data.file_info.sample_rate}Hz
                </div>`;
                
                if (data.results) {
                    for (const [model, result] of Object.entries(data.results)) {
                        html += `<div style="border: 1px solid #dee2e6; border-radius: 4px; margin: 10px 0; padding: 15px;">`;
                        html += `<h4 style="color: #007bff; margin-top: 0;">📝 ${model.toUpperCase()} 识别结果</h4>`;
                        
                        if (result.text) {
                            html += `<div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin: 10px 0;">
                                <strong>🎯 识别文本:</strong><br>
                                <p style="font-size: 16px; line-height: 1.5; margin: 5px 0;">${result.text}</p>
                            </div>`;
                        }
                        
                        if (result.language) {
                            html += `<p><strong>🌐 检测语言:</strong> ${result.language}</p>`;
                        }
                        
                        if (result.timestamp) {
                            html += `<details style="margin: 10px 0;">
                                <summary style="cursor: pointer; font-weight: bold;">⏱️ 时间戳信息</summary>
                                <div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin: 5px 0; font-family: monospace; font-size: 14px; white-space: pre-wrap;">${result.timestamp}</div>
                            </details>`;
                        }
                        
                        if (result.speaker_segments && result.speaker_segments.length > 0) {
                            html += `<details style="margin: 10px 0;">
                                <summary style="cursor: pointer; font-weight: bold;">👥 说话人分离结果</summary>
                                <div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin: 5px 0;">`;
                            
                            for (const segment of result.speaker_segments) {
                                const speakerColor = segment.speaker === '说话人1' ? '#007bff' : '#28a745';
                                html += `<div style="margin: 8px 0; padding: 8px; border-left: 4px solid ${speakerColor}; background: white;">
                                    <strong style="color: ${speakerColor};">${segment.speaker}</strong> 
                                    <span style="color: #666; font-size: 12px;">[${segment.start.toFixed(2)}s - ${segment.end.toFixed(2)}s]</span><br>
                                    <span style="font-size: 14px; line-height: 1.4;">${segment.text}</span>
                                </div>`;
                            }
                            
                            html += `</div></details>`;
                        }
                        
                        html += `</div>`;
                    }
                }
            } else if (data.status === 'processing') {
                html += `<div style="background: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0;">
                    <strong>⏳ 状态:</strong> 正在处理中... (${data.progress}%)
                </div>`;
            } else if (data.status === 'error') {
                html += `<div style="background: #f8d7da; padding: 10px; border-radius: 4px; margin: 10px 0;">
                    <strong>❌ 状态:</strong> 处理失败<br>
                    <strong>错误:</strong> ${data.error}
                </div>`;
            }
            
            document.getElementById('results').innerHTML = html;
        }
    </script>
</body>
</html>
    """, content_type='text/html'))
    
    # 为所有路由添加CORS
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app

async def main():
    print(f"🌟 FunASR 文件上传服务器启动")
    print(f"🎯 模型类型: {args.model_type}")
    print(f"🌐 HTTP服务: http://{args.host}:{args.http_port}")
    print(f"🌐 WebSocket服务: ws://{args.host}:{args.port}")
    
    # 启动HTTP服务器
    http_app = await create_http_app()
    http_runner = web.AppRunner(http_app)
    await http_runner.setup()
    http_site = web.TCPSite(http_runner, args.host, args.http_port)
    await http_site.start()
    
    # 启动WebSocket服务器
    websocket_server = await websockets.serve(
        websocket_handler,
        args.host,
        args.port,
        subprotocols=["binary"]
    )
    
    print("✅ 服务器启动完成！")
    print(f"📝 访问 http://{args.host}:{args.http_port} 进行文件上传")
    
    # 保持运行
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main()) 