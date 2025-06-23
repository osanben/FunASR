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
import os

# 新增：支持多种ASR模型的WebSocket服务器

parser = argparse.ArgumentParser()
parser.add_argument(
    "--host", type=str, default="0.0.0.0", required=False, help="host ip, localhost, 0.0.0.0"
)
parser.add_argument("--port", type=int, default=10095, required=False, help="grpc server port")

# 模型选择参数
parser.add_argument(
    "--model_type", 
    type=str, 
    default="paraformer", 
    choices=["paraformer", "whisper", "sensevoice"],
    help="选择ASR模型类型: paraformer, whisper, sensevoice"
)

# Paraformer模型参数
parser.add_argument(
    "--asr_model",
    type=str,
    default="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    help="Paraformer model from modelscope",
)
parser.add_argument("--asr_model_revision", type=str, default="v2.0.4", help="")

# Whisper模型参数
parser.add_argument(
    "--whisper_model",
    type=str,
    default="large-v3",
    choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
    help="Whisper model size"
)

# VAD和标点模型（通用）
parser.add_argument(
    "--vad_model",
    type=str,
    default="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    help="VAD model from modelscope",
)
parser.add_argument(
    "--punc_model",
    type=str,
    default="iic/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727",
    help="Punctuation model from modelscope",
)

# 说话人识别模型
parser.add_argument(
    "--spk_model",
    type=str,
    default="iic/speech_campplus_sv_zh-cn_16k-common",
    help="Speaker model from modelscope",
)

parser.add_argument("--ngpu", type=int, default=1, help="0 for cpu, 1 for gpu")
parser.add_argument("--device", type=str, default="cuda", help="cuda, cpu")
parser.add_argument("--ncpu", type=int, default=4, help="cpu cores")

args = parser.parse_args()

websocket_users = set()

print(f"正在加载 {args.model_type} 模型...")

# 根据模型类型加载不同的ASR模型
if args.model_type == "whisper":
    try:
        import whisper
        from faster_whisper import WhisperModel
        
        # 使用faster-whisper以获得更好的性能
        model_asr = WhisperModel(
            args.whisper_model, 
            device=args.device,
            compute_type="float16" if args.device == "cuda" else "int8"
        )
        print(f"Whisper {args.whisper_model} 模型加载成功!")
        
        # Whisper的ASR处理函数
        def whisper_transcribe(audio_data, language="zh"):
            # 转换音频数据格式
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # 使用Whisper进行转录
            segments, info = model_asr.transcribe(
                audio_np, 
                language=language,
                word_timestamps=True,
                vad_filter=True
            )
            
            # 组合结果
            text = ""
            timestamps = []
            for segment in segments:
                text += segment.text
                timestamps.append([segment.start * 1000, segment.end * 1000])  # 转换为毫秒
            
            return {
                "text": text.strip(),
                "timestamps": timestamps,
                "language": info.language,
                "language_probability": info.language_probability
            }
            
    except ImportError:
        print("Whisper未安装，请运行: pip install openai-whisper faster-whisper")
        exit(1)

elif args.model_type == "paraformer":
    from funasr import AutoModel
    
    # 加载Paraformer模型
    model_asr = AutoModel(
        model=args.asr_model,
        model_revision=args.asr_model_revision,
        ngpu=args.ngpu,
        ncpu=args.ncpu,
        device=args.device,
        disable_pbar=True,
        disable_log=True,
    )
    print("Paraformer 模型加载成功!")

elif args.model_type == "sensevoice":
    from funasr import AutoModel
    
    # 加载SenseVoice模型
    model_asr = AutoModel(
        model="iic/SenseVoiceSmall",
        ngpu=args.ngpu,
        ncpu=args.ncpu,
        device=args.device,
        disable_pbar=True,
        disable_log=True,
    )
    print("SenseVoice 模型加载成功!")

# 加载VAD模型
try:
    from funasr import AutoModel
    model_vad = AutoModel(
        model=args.vad_model,
        ngpu=args.ngpu,
        ncpu=args.ncpu,
        device=args.device,
        disable_pbar=True,
        disable_log=True,
    )
    print("VAD 模型加载成功!")
except:
    model_vad = None
    print("VAD 模型加载失败，将跳过语音活动检测")

# 加载标点模型
try:
    if args.punc_model != "":
        model_punc = AutoModel(
            model=args.punc_model,
            ngpu=args.ngpu,
            ncpu=args.ncpu,
            device=args.device,
            disable_pbar=True,
            disable_log=True,
        )
        print("标点模型加载成功!")
    else:
        model_punc = None
except:
    model_punc = None
    print("标点模型加载失败，将跳过标点恢复")

# 加载说话人识别模型
try:
    if args.spk_model != "":
        model_spk = AutoModel(
            model=args.spk_model,
            ngpu=args.ngpu,
            ncpu=args.ncpu,
            device=args.device,
            disable_pbar=True,
            disable_log=True,
        )
        print("说话人识别模型加载成功!")
    else:
        model_spk = None
except:
    model_spk = None
    print("说话人识别模型加载失败，将跳过说话人识别")

print(f"所有模型加载完成! 使用 {args.model_type} 作为主要ASR引擎")


async def process_audio_with_model(websocket, audio_data):
    """根据选择的模型类型处理音频"""
    
    if args.model_type == "whisper":
        # 使用Whisper处理
        try:
            result = whisper_transcribe(audio_data)
            
            # 格式化输出
            response = {
                "mode": "offline",
                "text": result["text"],
                "timestamp": result["timestamps"],
                "is_final": True,
                "language": result.get("language", "zh"),
                "model_type": "whisper",
                "confidence": result.get("language_probability", 0.0)
            }
            
            return response
            
        except Exception as e:
            print(f"Whisper处理错误: {e}")
            return {"mode": "offline", "text": "", "is_final": True, "error": str(e)}
    
    elif args.model_type == "paraformer":
        # 使用Paraformer处理（原有逻辑）
        try:
            # 这里保持原有的Paraformer处理逻辑
            # 转换音频格式
            audio_in = np.frombuffer(audio_data, dtype=np.int16)
            
            # VAD处理
            if model_vad:
                vad_res = model_vad.generate(input=audio_in, cache=websocket.status_dict_vad)
                if vad_res[0]["value"]:
                    segments = vad_res[0]["value"]
                    print(f"VAD检测到语音段: {segments}")
                else:
                    return {"mode": "offline", "text": "", "is_final": True}
            
            # ASR处理
            asr_res = model_asr.generate(
                input=audio_in,
                cache=websocket.status_dict_asr,
                is_final=True,
                return_spk_res=True if model_spk else False,
                sentence_timestamp=True
            )
            
            # 标点处理
            text = asr_res[0]["text"]
            if model_punc and text:
                punc_res = model_punc.generate(input=text, cache=websocket.status_dict_punc)
                text = punc_res[0]["text"]
            
            response = {
                "mode": "offline", 
                "text": text,
                "timestamp": asr_res[0].get("timestamp", []),
                "is_final": True,
                "model_type": "paraformer"
            }
            
            # 添加说话人信息
            if "spk_embedding" in asr_res[0]:
                response["speaker_info"] = asr_res[0]["spk_embedding"]
            
            return response
            
        except Exception as e:
            print(f"Paraformer处理错误: {e}")
            return {"mode": "offline", "text": "", "is_final": True, "error": str(e)}
    
    elif args.model_type == "sensevoice":
        # 使用SenseVoice处理
        try:
            audio_in = np.frombuffer(audio_data, dtype=np.int16)
            
            asr_res = model_asr.generate(
                input=audio_in,
                language="auto",
                use_itn=True,
                batch_size_s=60
            )
            
            response = {
                "mode": "offline",
                "text": asr_res[0]["text"],
                "is_final": True,
                "model_type": "sensevoice"
            }
            
            return response
            
        except Exception as e:
            print(f"SenseVoice处理错误: {e}")
            return {"mode": "offline", "text": "", "is_final": True, "error": str(e)}


async def ws_serve(websocket):
    """WebSocket服务主函数"""
    global websocket_users
    websocket_users.add(websocket)
    
    # 初始化状态
    websocket.status_dict_asr = {}
    websocket.status_dict_vad = {"cache": {}, "is_final": False}
    websocket.status_dict_punc = {"cache": {}}
    websocket.wav_name = "microphone"
    websocket.mode = "offline"
    
    print(f"新用户连接，当前使用 {args.model_type} 模型", flush=True)

    try:
        async for message in websocket:
            if isinstance(message, str):
                # 处理JSON配置消息
                messagejson = json.loads(message)
                print(f"收到配置: {messagejson}")
                
                if "wav_name" in messagejson:
                    websocket.wav_name = messagejson.get("wav_name")
                if "mode" in messagejson:
                    websocket.mode = messagejson["mode"]
                
            else:
                # 处理音频数据
                print(f"收到音频数据: {len(message)} 字节")
                
                # 处理音频
                result = await process_audio_with_model(websocket, message)
                
                # 发送结果
                if result["text"]:
                    await websocket.send(json.dumps(result, ensure_ascii=False))
                    print(f"识别结果 ({args.model_type}): {result['text']}")
                
    except websockets.exceptions.ConnectionClosed:
        print("WebSocket连接已关闭")
    except Exception as e:
        print(f"WebSocket错误: {e}")
    finally:
        websocket_users.discard(websocket)


async def main():
    """启动WebSocket服务器"""
    print(f"启动WebSocket服务器...")
    print(f"模型类型: {args.model_type}")
    print(f"监听地址: {args.host}:{args.port}")
    
    # 启动服务器
    async with websockets.serve(
        ws_serve, 
        args.host, 
        args.port,
        subprotocols=["binary"]
    ):
        print(f"WebSocket服务器已启动在 ws://{args.host}:{args.port}")
        print("等待客户端连接...")
        await asyncio.Future()  # 永久运行


if __name__ == "__main__":
    asyncio.run(main()) 