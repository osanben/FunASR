#!/usr/bin/env python3
import asyncio
import json
import websockets
import time
import logging
import tracemalloc
import numpy as np
import argparse
import ssl
import io
import warnings
warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser()
parser.add_argument(
    "--host", type=str, default="0.0.0.0", required=False, help="host ip, localhost, 0.0.0.0"
)
parser.add_argument("--port", type=int, default=10095, required=False, help="grpc server port")

# 模型类型选择
parser.add_argument(
    "--model_type", 
    type=str, 
    default="paraformer", 
    choices=["paraformer", "whisper", "sensevoice", "hybrid"],
    help="选择ASR模型类型: paraformer, whisper, sensevoice, hybrid(同时使用多个模型)"
)

# Whisper模型参数
parser.add_argument(
    "--whisper_model",
    type=str,
    default="large-v3",
    choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
    help="Whisper模型大小"
)
parser.add_argument(
    "--whisper_language",
    type=str,
    default="zh",
    help="Whisper识别语言 (zh, en, auto等)"
)

# Paraformer模型参数 (保持兼容)
parser.add_argument(
    "--asr_model",
    type=str,
    default="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    help="Paraformer model from modelscope",
)
parser.add_argument("--asr_model_revision", type=str, default="v2.0.4", help="")
parser.add_argument(
    "--vad_model",
    type=str,
    default="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    help="VAD model from modelscope",
)
parser.add_argument("--vad_model_revision", type=str, default="v2.0.4", help="")
parser.add_argument(
    "--punc_model",
    type=str,
    default="iic/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727",
    help="标点模型",
)
parser.add_argument("--punc_model_revision", type=str, default="v2.0.4", help="")
parser.add_argument(
    "--spk_model",
    type=str,
    default="iic/speech_campplus_sv_zh-cn_16k-common",
    help="说话人识别模型",
)
parser.add_argument("--spk_model_revision", type=str, default="v2.0.2", help="")

# 通用参数
parser.add_argument("--ngpu", type=int, default=1, help="0 for cpu, 1 for gpu")
parser.add_argument("--device", type=str, default="cuda", help="cuda, cpu, mps")
parser.add_argument("--ncpu", type=int, default=4, help="cpu cores")
parser.add_argument(
    "--certfile",
    type=str,
    default="../../ssl_key/server.crt",
    required=False,
    help="certfile for ssl",
)
parser.add_argument(
    "--keyfile",
    type=str,
    default="../../ssl_key/server.key",
    required=False,
    help="keyfile for ssl",
)

args = parser.parse_args()

websocket_users = set()

print(f"🚀 开始加载模型，类型: {args.model_type}")

# 全局模型变量
model_asr = None
model_whisper = None
model_vad = None
model_punc = None
model_spk = None

# 加载模型
if args.model_type in ["paraformer", "hybrid"]:
    print("📦 加载 Paraformer 模型...")
    from funasr import AutoModel
    
    # 对于MPS设备，FunASR使用CPU避免float64问题
    funasr_device = "cpu" if args.device == "mps" else args.device
    funasr_ngpu = 0 if args.device == "mps" else args.ngpu
    
    print(f"🔧 FunASR设备设置: {funasr_device} (原始: {args.device})")
    
    model_asr = AutoModel(
        model=args.asr_model,
        model_revision=args.asr_model_revision,
        vad_model=args.vad_model,
        vad_model_revision=args.vad_model_revision,
        punc_model=args.punc_model,
        punc_model_revision=args.punc_model_revision,
        spk_model=args.spk_model,
        spk_model_revision=args.spk_model_revision,
        ngpu=funasr_ngpu,
        ncpu=args.ncpu,
        device=funasr_device,
        disable_pbar=True,
        disable_log=True,
    )
    print("✅ Paraformer 模型加载成功!")

if args.model_type in ["whisper", "hybrid"]:
    print("📦 加载 Whisper 模型...")
    try:
        import whisper
        import torch
        
        # 检测设备并设置正确的数据类型
        if args.device == "mps" and torch.backends.mps.is_available():
            device = "mps"
            print("🍎 使用 Apple Silicon MPS 设备")
        elif args.device == "cuda" and torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
            
        model_whisper = whisper.load_model(args.whisper_model, device=device)
        
        # 确保模型使用float32精度（MPS兼容）
        if hasattr(model_whisper, 'half'):
            model_whisper = model_whisper.float()  # 使用float32而不是half
            
        print(f"✅ Whisper {args.whisper_model} 模型加载成功! 设备: {device}")
    except ImportError:
        print("❌ Whisper 未安装，请运行: pip install openai-whisper")
        if args.model_type == "whisper":
            exit(1)
    except Exception as e:
        print(f"❌ Whisper 模型加载失败: {e}")
        if args.model_type == "whisper":
            exit(1)

if args.model_type == "sensevoice":
    print("📦 加载 SenseVoice 模型...")
    from funasr import AutoModel
    
    # 对于MPS设备，使用CPU避免float64问题
    sensevoice_device = "cpu" if args.device == "mps" else args.device
    sensevoice_ngpu = 0 if args.device == "mps" else args.ngpu
    
    print(f"🔧 SenseVoice设备设置: {sensevoice_device} (原始: {args.device})")
    
    model_asr = AutoModel(
        model="iic/SenseVoiceSmall",
        ngpu=sensevoice_ngpu,
        ncpu=args.ncpu,
        device=sensevoice_device,
        disable_pbar=True,
        disable_log=True,
    )
    print("✅ SenseVoice 模型加载成功!")

print("🎉 所有模型加载完成! 服务器已就绪!")

def whisper_transcribe(audio_data, sample_rate=16000):
    """使用Whisper进行语音识别"""
    try:
        # 将音频数据转换为float32格式
        if isinstance(audio_data, bytes):
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        elif isinstance(audio_data, np.ndarray):
            if audio_data.dtype == np.int16:
                audio_np = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype == np.float32:
                # 如果已经是float32，检查是否需要归一化
                if audio_data.max() > 1.0 or audio_data.min() < -1.0:
                    # 假设是int16范围的数据，需要归一化
                    audio_np = audio_data / 32768.0
                else:
                    # 已经是归一化的数据
                    audio_np = audio_data
            elif audio_data.dtype == np.float64:
                audio_np = audio_data.astype(np.float32)
                if audio_np.max() > 1.0 or audio_np.min() < -1.0:
                    audio_np = audio_np / 32768.0
            else:
                audio_np = audio_data.astype(np.float32)
                if audio_np.max() > 1.0 or audio_np.min() < -1.0:
                    audio_np = audio_np / 32768.0
        else:
            print(f"❌ 不支持的音频数据类型: {type(audio_data)}")
            return {"text": "", "timestamp": "", "language": "unknown", "segments": []}
        
        # 确保数据类型为float32，范围在[-1, 1]
        audio_np = audio_np.astype(np.float32)
        if audio_np.max() > 1.0 or audio_np.min() < -1.0:
            audio_np = np.clip(audio_np, -1.0, 1.0)
        
        # 确保采样率为16kHz (Whisper的要求)
        if sample_rate != 16000:
            import librosa
            # 确保librosa使用float32，避免MPS设备的float64问题
            audio_np = audio_np.astype(np.float32)
            audio_np = librosa.resample(audio_np, orig_sr=sample_rate, target_sr=16000, dtype=np.float32)
        
        print(f"🎵 音频长度: {len(audio_np)/16000:.2f}秒, 数据类型: {audio_np.dtype}, 范围: [{audio_np.min():.3f}, {audio_np.max():.3f}]")
        
        # 最终确保数据兼容性
        audio_np = np.ascontiguousarray(audio_np, dtype=np.float32)
        
        # 使用Whisper进行识别
        language = None if args.whisper_language == "auto" else args.whisper_language
        
        # 设置Whisper的推理选项，确保MPS兼容
        options = {
            "language": language,
            "word_timestamps": True,
            "verbose": False,
            "fp16": False,  # 禁用半精度，使用float32
        }
        
        result = model_whisper.transcribe(audio_np, **options)
        
        text = result.get("text", "").strip()
        segments = result.get("segments", [])
        
        # 构建带时间戳的结果
        timestamp_text = ""
        for segment in segments:
            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            segment_text = segment.get("text", "").strip()
            if segment_text:
                timestamp_text += f"[{start_time:.2f}->{end_time:.2f}] {segment_text} "
        
        return {
            "text": text,
            "timestamp": timestamp_text.strip(),
            "language": result.get("language", "unknown"),
            "segments": segments
        }
        
    except Exception as e:
        print(f"❌ Whisper识别错误: {e}")
        return {"text": "", "timestamp": "", "language": "unknown", "segments": []}

async def ws_reset(websocket):
    print("🔄 WebSocket 重置, 总连接数:", len(websocket_users))
    
    if hasattr(websocket, 'status_dict_asr_online'):
        websocket.status_dict_asr_online["cache"] = {}
        websocket.status_dict_asr_online["is_final"] = True
        websocket.status_dict_asr_online["pre_text"] = []
    if hasattr(websocket, 'status_dict_vad'):
        websocket.status_dict_vad["cache"] = {}
        websocket.status_dict_vad["is_final"] = True
        websocket.status_dict_vad["pre_text"] = []
    if hasattr(websocket, 'status_dict_punc'):
        websocket.status_dict_punc["cache"] = {}
        websocket.status_dict_punc["pre_text"] = []
    
    await websocket.close()

async def clear_websocket():
    for websocket in websocket_users:
        await ws_reset(websocket)
    websocket_users.clear()

async def process_audio_with_model(websocket, audio_data):
    """根据选择的模型类型处理音频"""
    try:
        results = {}
        
        # 确保音频数据格式正确
        print(f"🔍 输入音频数据类型: {audio_data.dtype}, 形状: {audio_data.shape}")
        
        # Whisper处理
        if args.model_type in ["whisper", "hybrid"] and model_whisper:
            print("🎯 开始Whisper处理...")
            whisper_result = whisper_transcribe(audio_data)
            results["whisper"] = whisper_result
            print("✅ Whisper处理完成")
        
        # Paraformer处理  
        if args.model_type in ["paraformer", "hybrid"] and model_asr:
            print("🎯 开始Paraformer处理...")
            # 确保数据类型兼容FunASR
            if audio_data.dtype != np.float32:
                audio_data_asr = audio_data.astype(np.float32)
            else:
                audio_data_asr = audio_data.copy()
                
            # 如果数据范围不在[-1,1]，进行归一化
            if audio_data_asr.max() > 1.0 or audio_data_asr.min() < -1.0:
                audio_data_asr = audio_data_asr / 32768.0
                
            print(f"🔧 ASR音频数据: 类型={audio_data_asr.dtype}, 范围=[{audio_data_asr.min():.3f}, {audio_data_asr.max():.3f}]")
            
            # 使用FunASR处理 - 初始化完整的缓存状态
            cache_state = {
                "pre_text": [],
                "cache": {},
                "is_final": False
            }
            
            paraformer_result = model_asr.generate(
                input=audio_data_asr,
                cache=cache_state,
                language="auto",
                use_itn=True,
                batch_size_s=60,
                return_spk_res=True,
                sentence_timestamp=True,
            )
            results["paraformer"] = paraformer_result
            print("✅ Paraformer处理完成")
        
        # SenseVoice处理
        if args.model_type == "sensevoice" and model_asr:
            print("🎯 开始SenseVoice处理...")
            # 确保数据类型兼容
            if audio_data.dtype != np.float32:
                audio_data_sv = audio_data.astype(np.float32)
            else:
                audio_data_sv = audio_data.copy()
                
            if audio_data_sv.max() > 1.0 or audio_data_sv.min() < -1.0:
                audio_data_sv = audio_data_sv / 32768.0
                
            # 初始化SenseVoice缓存状态
            sv_cache_state = {
                "pre_text": [],
                "cache": {},
                "is_final": False
            }
            
            sensevoice_result = model_asr.generate(
                input=audio_data_sv,
                cache=sv_cache_state,
                language="auto", 
                use_itn=True,
                batch_size_s=60,
            )
            results["sensevoice"] = sensevoice_result
            print("✅ SenseVoice处理完成")
        
        return results
        
    except Exception as e:
        print(f"❌ 音频处理错误: {e}")
        import traceback
        traceback.print_exc()
        return {}

async def process_audio_with_model_cpu_fallback(websocket, audio_data):
    """CPU fallback处理函数"""
    try:
        import torch
        results = {}
        
        print("🖥️ 使用CPU fallback模式处理音频...")
        
        # 强制使用CPU，避免MPS问题
        original_device = None
        if hasattr(torch, 'set_default_device'):
            original_device = torch.get_default_device() if hasattr(torch, 'get_default_device') else None
            torch.set_default_device('cpu')
        
        # 确保音频数据在CPU上且为float32
        audio_cpu = np.ascontiguousarray(audio_data, dtype=np.float32)
        
        # Whisper处理 (CPU模式)
        if args.model_type in ["whisper", "hybrid"] and model_whisper:
            print("🎯 CPU模式Whisper处理...")
            # 临时将Whisper模型移到CPU
            model_whisper_cpu = model_whisper.to('cpu') if hasattr(model_whisper, 'to') else model_whisper
            whisper_result = whisper_transcribe(audio_cpu)
            results["whisper"] = whisper_result
        
        # Paraformer处理 (跳过，因为可能有MPS问题)
        if args.model_type in ["paraformer", "hybrid"]:
            print("⚠️ 跳过Paraformer处理以避免MPS问题")
            results["paraformer"] = [{"text": "CPU模式下跳过Paraformer处理", "timestamp": ""}]
        
        # 恢复原始设备设置
        if original_device and hasattr(torch, 'set_default_device'):
            torch.set_default_device(original_device)
            
        return results
        
    except Exception as e:
        print(f"❌ CPU fallback处理错误: {e}")
        return {}

async def ws_serve(websocket):
    frames = []
    global websocket_users
    websocket_users.add(websocket)
    
    # 初始化状态 - 完整的缓存结构
    websocket.status_dict_asr_online = {
        "cache": {}, 
        "is_final": False,
        "pre_text": []
    }
    websocket.status_dict_vad = {
        "cache": {}, 
        "is_final": False,
        "pre_text": []
    }
    websocket.status_dict_punc = {
        "cache": {},
        "pre_text": []
    }
    websocket.chunk_interval = 10
    websocket.wav_name = "microphone"
    websocket.mode = "offline"  # 默认离线模式
    websocket.audio_buffer = b""  # 音频缓冲区
    
    print(f"🔗 新用户连接，当前模型: {args.model_type}")
    
    try:
        async for message in websocket:
            if isinstance(message, str):
                # 处理JSON控制消息
                try:
                    messagejson = json.loads(message)
                    print(f"📨 收到控制消息: {list(messagejson.keys())}")
                    
                    if "wav_name" in messagejson:
                        websocket.wav_name = messagejson.get("wav_name")
                    if "mode" in messagejson:
                        websocket.mode = messagejson["mode"]
                        print(f"🎯 ASR模式设置为: {websocket.mode}")
                    if "chunk_interval" in messagejson:
                        websocket.chunk_interval = messagejson["chunk_interval"]
                    if "is_speaking" in messagejson:
                        websocket.is_speaking = messagejson["is_speaking"]
                        if not websocket.is_speaking and len(websocket.audio_buffer) > 0:
                            # 说话结束，处理完整音频
                            await process_complete_audio(websocket)
                            
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析错误: {e}")
                    
            elif isinstance(message, bytes):
                # 处理音频数据
                print(f"🎵 收到音频数据: {len(message)} 字节")
                websocket.audio_buffer += message
                
                # 如果是流式模式，可以实时处理小块音频
                if websocket.mode == "online" and len(websocket.audio_buffer) >= 1600:  # 100ms at 16kHz
                    await process_streaming_audio(websocket, websocket.audio_buffer[-1600:])
                
    except websockets.exceptions.ConnectionClosed:
        print("🔌 客户端断开连接")
    except Exception as e:
        print(f"❌ WebSocket错误: {e}")
    finally:
        websocket_users.discard(websocket)
        print(f"👋 用户断开，剩余连接数: {len(websocket_users)}")

async def process_complete_audio(websocket):
    """处理完整的音频数据"""
    if len(websocket.audio_buffer) == 0:
        return
        
    try:
        print(f"🔄 处理完整音频，大小: {len(websocket.audio_buffer)} 字节")
        
        # 转换音频格式 - 确保正确的数据类型
        audio_np = np.frombuffer(websocket.audio_buffer, dtype=np.int16)
        print(f"🎵 音频数组形状: {audio_np.shape}, 数据类型: {audio_np.dtype}")
        
        # 确保音频数据长度合理
        if len(audio_np) < 1600:  # 少于100ms的音频
            print("⚠️ 音频数据太短，跳过处理")
            return
            
        # 限制音频长度，避免内存问题
        max_samples = 16000 * 60  # 最多60秒
        if len(audio_np) > max_samples:
            print(f"⚠️ 音频太长({len(audio_np)/16000:.1f}秒)，截取前60秒")
            audio_np = audio_np[:max_samples]
        
        # 确保数据类型兼容性 - 转换为float32避免PyTorch类型错误
        print(f"🔄 转换数据类型: {audio_np.dtype} -> float32")
        audio_float = audio_np.astype(np.float32)
        print(f"✅ 转换完成: {audio_float.dtype}, 范围: [{audio_float.min():.1f}, {audio_float.max():.1f}]")
        
        # 使用选择的模型处理
        results = await process_audio_with_model(websocket, audio_float)
        
        # 发送结果
        for model_name, result in results.items():
            if result:
                await send_result(websocket, result, model_name)
        
        # 清空缓冲区
        websocket.audio_buffer = b""
        
    except Exception as e:
        print(f"❌ 音频处理错误: {e}")
        import traceback
        traceback.print_exc()
        
        # 如果是MPS float64错误，尝试强制使用CPU处理
        if "MPS" in str(e) and "float64" in str(e):
            print("🔧 检测到MPS float64错误，尝试使用CPU处理...")
            try:
                # 将数据转移到CPU并重新处理
                audio_cpu = audio_float.copy()  # 确保在CPU上
                results = await process_audio_with_model_cpu_fallback(websocket, audio_cpu)
                
                # 发送结果
                for model_name, result in results.items():
                    if result:
                        await send_result(websocket, result, model_name)
                        
                # 清空缓冲区
                websocket.audio_buffer = b""
                print("✅ CPU fallback处理成功")
                return
            except Exception as fallback_error:
                print(f"❌ CPU fallback也失败: {fallback_error}")

async def process_streaming_audio(websocket, audio_chunk):
    """处理流式音频数据"""
    try:
        # 流式处理逻辑 (简化版)
        audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
        
        # 只在流式模式下使用Paraformer在线模型
        if args.model_type in ["paraformer", "hybrid"] and model_asr:
            # 这里可以实现流式识别逻辑
            pass
            
    except Exception as e:
        print(f"❌ 流式音频处理错误: {e}")

async def send_result(websocket, result, model_name):
    """发送识别结果"""
    try:
        if args.model_type == "whisper" or model_name == "whisper":
            # Whisper结果格式
            response = {
                "mode": "offline",
                "text": result.get("text", ""),
                "timestamp": result.get("timestamp", ""),
                "language": result.get("language", "unknown"),
                "model": f"whisper-{args.whisper_model}",
                "is_final": True
            }
        else:
            # FunASR结果格式
            if isinstance(result, list) and len(result) > 0:
                result_item = result[0]
                text = result_item.get("text", "")
                timestamp = result_item.get("timestamp", "")
                
                response = {
                    "mode": websocket.mode,
                    "text": text,
                    "timestamp": timestamp,
                    "model": model_name,
                    "is_final": True
                }
            else:
                response = {
                    "mode": websocket.mode,
                    "text": "",
                    "timestamp": "",
                    "model": model_name,
                    "is_final": True
                }
        
        await websocket.send(json.dumps(response, ensure_ascii=False))
        print(f"📤 发送结果 ({model_name}): {response['text'][:50]}...")
        
    except Exception as e:
        print(f"❌ 发送结果错误: {e}")

async def main():
    print(f"🌟 FunASR + Whisper WebSocket 服务器启动")
    print(f"🎯 模型类型: {args.model_type}")
    print(f"🌐 监听地址: {args.host}:{args.port}")
    
    # SSL配置 (可选)
    ssl_context = None
    try:
        if args.certfile and args.keyfile:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(args.certfile, args.keyfile)
            print("🔒 SSL已启用")
    except Exception as e:
        print(f"⚠️ SSL配置失败，使用HTTP: {e}")
    
    # 启动WebSocket服务器
    async with websockets.serve(
        ws_serve, 
        args.host, 
        args.port, 
        ssl=ssl_context,
        subprotocols=["binary"]
    ):
        print(f"✅ 服务器运行在 {'wss' if ssl_context else 'ws'}://{args.host}:{args.port}/")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main()) 