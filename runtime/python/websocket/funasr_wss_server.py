import asyncio
import json
import websockets
import time
import logging
import tracemalloc
import numpy as np
import argparse
import ssl


parser = argparse.ArgumentParser()
parser.add_argument(
    "--host", type=str, default="0.0.0.0", required=False, help="host ip, localhost, 0.0.0.0"
)
parser.add_argument("--port", type=int, default=10095, required=False, help="grpc server port")
parser.add_argument(
    "--asr_model",
    type=str,
    default="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    help="model from modelscope",
)
parser.add_argument("--asr_model_revision", type=str, default="v2.0.4", help="")
parser.add_argument(
    "--asr_model_online",
    type=str,
    default="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online",
    help="model from modelscope",
)
parser.add_argument("--asr_model_online_revision", type=str, default="v2.0.4", help="")
parser.add_argument(
    "--vad_model",
    type=str,
    default="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    help="model from modelscope",
)
parser.add_argument("--vad_model_revision", type=str, default="v2.0.4", help="")
parser.add_argument(
    "--punc_model",
    type=str,
    default="iic/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727",
    help="model from modelscope",
)
parser.add_argument("--punc_model_revision", type=str, default="v2.0.4", help="")
parser.add_argument("--ngpu", type=int, default=1, help="0 for cpu, 1 for gpu")
parser.add_argument("--device", type=str, default="cuda", help="cuda, cpu")
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

print("model loading")
from funasr import AutoModel

# asr
model_asr = AutoModel(
    model=args.asr_model,
    model_revision=args.asr_model_revision,
    ngpu=args.ngpu,
    ncpu=args.ncpu,
    device=args.device,
    disable_pbar=True,
    disable_log=True,
)
# asr
model_asr_streaming = AutoModel(
    model=args.asr_model_online,
    model_revision=args.asr_model_online_revision,
    ngpu=args.ngpu,
    ncpu=args.ncpu,
    device=args.device,
    disable_pbar=True,
    disable_log=True,
)
# vad - 降低敏感度，更容易检测语音
model_vad = AutoModel(
    model=args.vad_model,
    model_revision=args.vad_model_revision,
    ngpu=args.ngpu,
    ncpu=args.ncpu,
    device=args.device,
    disable_pbar=True,
    disable_log=True,
    # chunk_size=60,
    # 降低VAD敏感度的参数
    vad_onset=0.1,  # 降低语音开始检测阈值 (默认0.5)
    vad_offset=0.1,  # 降低语音结束检测阈值 (默认0.5)
    min_silence_duration=100,  # 最小静音时长(ms) (默认600)
    min_speech_duration=100,   # 最小语音时长(ms) (默认200)
)

if args.punc_model != "":
    model_punc = AutoModel(
        model=args.punc_model,
        model_revision=args.punc_model_revision,
        ngpu=args.ngpu,
        ncpu=args.ncpu,
        device=args.device,
        disable_pbar=True,
        disable_log=True,
    )
else:
    model_punc = None


print("model loaded! only support one client at the same time now!!!!")


async def ws_reset(websocket):
    print("ws reset now, total num is ", len(websocket_users))

    websocket.status_dict_asr_online["cache"] = {}
    websocket.status_dict_asr_online["is_final"] = True
    websocket.status_dict_vad["cache"] = {}
    websocket.status_dict_vad["is_final"] = True
    websocket.status_dict_punc["cache"] = {}

    await websocket.close()


async def clear_websocket():
    for websocket in websocket_users:
        await ws_reset(websocket)
    websocket_users.clear()


async def ws_serve(websocket):
    frames = []
    frames_asr = []
    frames_asr_online = []
    global websocket_users
    # await clear_websocket()
    websocket_users.add(websocket)
    websocket.status_dict_asr = {}
    websocket.status_dict_asr_online = {"cache": {}, "is_final": False}
    websocket.status_dict_vad = {"cache": {}, "is_final": False}
    websocket.status_dict_punc = {"cache": {}}
    websocket.chunk_interval = 10
    websocket.vad_pre_idx = 0
    speech_start = False
    speech_end_i = -1
    websocket.wav_name = "microphone"
    websocket.mode = "2pass"
    print(f"[CONN] 🔗 New user connected from {websocket.remote_address}", flush=True)
    print(f"[CONN] 🎯 Initial mode: {websocket.mode}, wav_name: {websocket.wav_name}", flush=True)

    try:
        async for message in websocket:
            print(f"[DEBUG] Received message type: {type(message)}, size: {len(message) if isinstance(message, (str, bytes)) else 'unknown'}", flush=True)
            if isinstance(message, str):
                print(f"[DEBUG] JSON message received: {message[:200]}...", flush=True)
                messagejson = json.loads(message)
                
                # 检查音频格式相关配置
                if "wav_format" in messagejson:
                    print(f"[DEBUG] Audio format specified: {messagejson['wav_format']}", flush=True)
                if "audio_fs" in messagejson:
                    print(f"[DEBUG] Audio sample rate: {messagejson['audio_fs']}", flush=True)

                if "is_speaking" in messagejson:
                    websocket.is_speaking = messagejson["is_speaking"]
                    websocket.status_dict_asr_online["is_final"] = not websocket.is_speaking
                if "chunk_interval" in messagejson:
                    websocket.chunk_interval = messagejson["chunk_interval"]
                if "wav_name" in messagejson:
                    websocket.wav_name = messagejson.get("wav_name")
                if "chunk_size" in messagejson:
                    chunk_size = messagejson["chunk_size"]
                    if isinstance(chunk_size, str):
                        chunk_size = chunk_size.split(",")
                    websocket.status_dict_asr_online["chunk_size"] = [int(x) for x in chunk_size]
                if "encoder_chunk_look_back" in messagejson:
                    websocket.status_dict_asr_online["encoder_chunk_look_back"] = messagejson[
                        "encoder_chunk_look_back"
                    ]
                if "decoder_chunk_look_back" in messagejson:
                    websocket.status_dict_asr_online["decoder_chunk_look_back"] = messagejson[
                        "decoder_chunk_look_back"
                    ]
                if "hotwords" in messagejson:
                    websocket.status_dict_asr["hotword"] = messagejson["hotwords"]
                if "mode" in messagejson:
                    websocket.mode = messagejson["mode"]
                    print(f"[DEBUG] ASR mode set to: {websocket.mode}", flush=True)

            websocket.status_dict_vad["chunk_size"] = int(
                websocket.status_dict_asr_online["chunk_size"][1] * 60 / websocket.chunk_interval
            )
            if len(frames_asr_online) > 0 or len(frames_asr) >= 0 or not isinstance(message, str):
                if not isinstance(message, str):
                    # 🎯 验证音频数据格式和大小
                    if len(message) < 32:  # 至少需要32字节（1ms的16kHz 16bit音频）
                        print(f"[AUDIO] ⚠️ Audio chunk too small: {len(message)} bytes, skipping", flush=True)
                        continue
                    
                    # 只在第一次接收音频数据时打印详细信息
                    if len(frames) == 0:
                        print(f"[AUDIO] 🎵 First audio data received: {len(message)} bytes, type: {type(message)}", flush=True)
                        # 检查音频数据的前几个字节来判断格式
                        if len(message) >= 4:
                            header = message[:4]
                            if header.startswith(b'ID3') or header[1:4] == b'ID3':
                                print(f"[AUDIO] 🎶 Detected MP3 format (ID3 header)", flush=True)
                            elif header.startswith(b'RIFF'):
                                print(f"[AUDIO] 🎶 Detected WAV format (RIFF header)", flush=True)
                            elif header.startswith(b'fLaC'):
                                print(f"[AUDIO] 🎶 Detected FLAC format", flush=True)
                            else:
                                print(f"[AUDIO] 🎶 Raw PCM audio format, header bytes: {header.hex()}", flush=True)
                    
                    frames.append(message)
                    duration_ms = len(message) // 32  # 16kHz, 16bit = 32 bytes/ms
                    websocket.vad_pre_idx += duration_ms
                    # 每隔50帧打印一次统计信息
                    if len(frames) % 50 == 0:
                        print(f"[AUDIO] 📊 Frames: {len(frames)}, Duration: {websocket.vad_pre_idx}ms", flush=True)

                    # asr online - 实时流式识别，不依赖VAD
                    frames_asr_online.append(message)
                    websocket.status_dict_asr_online["is_final"] = speech_end_i != -1
                    
                    # 🎯 每隔chunk_interval帧就进行一次在线识别，实现实时返回
                    if len(frames_asr_online) % websocket.chunk_interval == 0:
                        if websocket.mode == "2pass" or websocket.mode == "online":
                            audio_in = b"".join(frames_asr_online)
                            try:
                                print(f"[DEBUG] 🔄 Processing online ASR chunk: {len(frames_asr_online)} frames, {len(audio_in)} bytes", flush=True)
                                await async_asr_online(websocket, audio_in)
                            except Exception as e:
                                print(f"[ERROR] Online ASR error: {e}", flush=True)
                        frames_asr_online = []
                    if speech_start:
                        frames_asr.append(message)
                        print(f"[DEBUG] Added audio frame to ASR buffer (speech_start=True), total frames: {len(frames_asr)}", flush=True)
                    else:
                        print(f"[DEBUG] Audio frame NOT added to ASR buffer (speech_start=False)", flush=True)
                    # vad online
                    try:
                        speech_start_i, speech_end_i = await async_vad(websocket, message)
                        print(f"[DEBUG] VAD result: start={speech_start_i}, end={speech_end_i}", flush=True)
                    except Exception as e:
                        print(f"[ERROR] VAD error: {e}", flush=True)
                    
                    # 🎯 强制语音检测：如果连续收到音频数据但VAD没有检测到语音，强制开始语音识别
                    if speech_start_i == -1 and len(frames) > 50:  # 收到50帧以上音频但VAD没检测到
                        total_audio_ms = websocket.vad_pre_idx
                        print(f"[DEBUG] 🚨 Force speech detection: {len(frames)} frames, {total_audio_ms}ms audio, but no VAD detection", flush=True)
                        if total_audio_ms > 500:  # 累积音频超过500ms才强制检测
                            speech_start_i = 0  # 强制设置语音开始
                            speech_start = True
                            print(f"[DEBUG] 🔧 Forced speech start enabled", flush=True)
                    
                    if speech_start_i != -1:
                        print(f"[DEBUG] Speech start detected at {speech_start_i}ms", flush=True)
                        speech_start = True
                        beg_bias = (websocket.vad_pre_idx - speech_start_i) // duration_ms
                        frames_pre = frames[-beg_bias:] if beg_bias > 0 else frames[-10:]  # 至少取最后10帧
                        frames_asr = []
                        frames_asr.extend(frames_pre)
                        print(f"[DEBUG] Added {len(frames_pre)} pre-frames to ASR buffer", flush=True)
                # asr punc offline - 改进触发条件，确保音频数据足够长
                should_process_offline = (
                    speech_end_i != -1 or  # VAD检测到语音结束
                    not websocket.is_speaking or  # 前端标记不在说话
                    len(frames_asr) > 100  # 累积音频帧过多，强制处理
                )
                
                if should_process_offline and len(frames_asr) > 0:
                    audio_in = b"".join(frames_asr)
                    audio_duration_ms = len(audio_in) // 32  # 16kHz, 16bit = 32 bytes/ms
                    
                    print(f"[DEBUG] Speech end detected (end_i={speech_end_i}, is_speaking={websocket.is_speaking}, frames_asr={len(frames_asr)})", flush=True)
                    print(f"[DEBUG] Audio data: {len(audio_in)} bytes, ~{audio_duration_ms}ms duration", flush=True)
                    
                    # 🎯 确保音频数据足够长（至少100ms）才进行ASR处理
                    if audio_duration_ms >= 100:
                        if websocket.mode == "2pass" or websocket.mode == "offline":
                            try:
                                print(f"[DEBUG] Starting offline ASR with {len(audio_in)} bytes audio from {len(frames_asr)} frames", flush=True)
                                await async_asr(websocket, audio_in)
                            except Exception as e:
                                print(f"[ERROR] ASR offline error: {e}", flush=True)
                    else:
                        print(f"[DEBUG] 🚫 Audio too short ({audio_duration_ms}ms < 100ms), skipping offline ASR", flush=True)
                    frames_asr = []
                    speech_start = False
                    frames_asr_online = []
                    websocket.status_dict_asr_online["cache"] = {}
                    if not websocket.is_speaking:
                        websocket.vad_pre_idx = 0
                        frames = []
                        websocket.status_dict_vad["cache"] = {}
                    else:
                        frames = frames[-20:]

    except websockets.ConnectionClosed:
        print(f"[CONN] 🔌 Connection closed for {websocket.remote_address}, remaining users: {len(websocket_users)-1}", flush=True)
        await ws_reset(websocket)
        websocket_users.remove(websocket)
    except websockets.InvalidState:
        print(f"[ERROR] ⚠️ WebSocket InvalidState for {websocket.remote_address}", flush=True)
    except Exception as e:
        print(f"[ERROR] 💥 WebSocket Exception for {websocket.remote_address}: {e}", flush=True)


async def async_vad(websocket, audio_in):
    print(f"[DEBUG] VAD processing {len(audio_in)} bytes audio", flush=True)
    print(f"[DEBUG] VAD status_dict: {websocket.status_dict_vad}", flush=True)
    
    segments_result = model_vad.generate(input=audio_in, **websocket.status_dict_vad)[0]["value"]
    print(f"[DEBUG] VAD raw result: {segments_result}", flush=True)

    speech_start = -1
    speech_end = -1

    if len(segments_result) == 0:
        print(f"[DEBUG] VAD: No segments detected (empty result)", flush=True)
        return speech_start, speech_end
    elif len(segments_result) > 1:
        print(f"[DEBUG] VAD: Multiple segments detected ({len(segments_result)} segments)", flush=True)
        return speech_start, speech_end
    
    if segments_result[0][0] != -1:
        speech_start = segments_result[0][0]
        print(f"[DEBUG] VAD: Speech start found at {speech_start}ms", flush=True)
    if segments_result[0][1] != -1:
        speech_end = segments_result[0][1]
        print(f"[DEBUG] VAD: Speech end found at {speech_end}ms", flush=True)
    
    return speech_start, speech_end


async def async_asr(websocket, audio_in):
    print(f"[DEBUG] async_asr called with {len(audio_in)} bytes", flush=True)
    if len(audio_in) > 0:
        # print(len(audio_in))
        print(f"[DEBUG] Calling model_asr.generate with status_dict: {websocket.status_dict_asr}", flush=True)
        rec_result = model_asr.generate(input=audio_in, **websocket.status_dict_asr)[0]
        print(f"[DEBUG] ASR result: {rec_result}", flush=True)
        if model_punc is not None and len(rec_result["text"]) > 0:
            # print("offline, before punc", rec_result, "cache", websocket.status_dict_punc)
            rec_result = model_punc.generate(
                input=rec_result["text"], **websocket.status_dict_punc
            )[0]
            # print("offline, after punc", rec_result)
        if len(rec_result["text"]) > 0:
            # print("offline", rec_result)
            mode = "2pass-offline" if "2pass" in websocket.mode else websocket.mode
            message = json.dumps(
                {
                    "mode": mode,
                    "text": rec_result["text"],
                    "wav_name": websocket.wav_name,
                    "is_final": True,  # 离线识别结果是最终结果
                }
            )
            print(f"[SEND] 🚀 Sending offline ASR result to client: {message}", flush=True)
            await websocket.send(message)
            print(f"[SEND] ✅ Offline message sent successfully", flush=True)

    else:
        mode = "2pass-offline" if "2pass" in websocket.mode else websocket.mode
        message = json.dumps(
            {
                "mode": mode,
                "text": "",
                "wav_name": websocket.wav_name,
                "is_final": websocket.is_speaking,
            }
        )
        print(f"[SEND] 📤 Sending empty offline ASR result: {message}", flush=True)
        await websocket.send(message)
        print(f"[SEND] ✅ Empty message sent successfully", flush=True)    

async def async_asr_online(websocket, audio_in):
    print(f"[DEBUG] 🎤 async_asr_online called with {len(audio_in)} bytes", flush=True)
    if len(audio_in) > 0:
        audio_duration_ms = len(audio_in) // 32  # 16kHz, 16bit = 32 bytes/ms
        print(f"[DEBUG] 🎵 Online audio duration: ~{audio_duration_ms}ms", flush=True)
        
        # 🎯 确保音频数据足够长才进行在线ASR处理
        if audio_duration_ms >= 50:  # 在线ASR要求更低，50ms即可
            print(f"[DEBUG] 🔄 Calling online ASR model with status_dict: {websocket.status_dict_asr_online}", flush=True)
            try:
                rec_result = model_asr_streaming.generate(
                    input=audio_in, **websocket.status_dict_asr_online
                )[0]
                print(f"[DEBUG] 📝 Online ASR result: {rec_result}", flush=True)
            except Exception as e:
                print(f"[ERROR] 💥 Online ASR model error: {e}", flush=True)
                return
        else:
            print(f"[DEBUG] 🚫 Online audio too short ({audio_duration_ms}ms < 50ms), skipping", flush=True)
            return
        # print("online, ", rec_result)
        # 🎯 2pass模式下也要发送在线结果，实现实时流式识别
        # if websocket.mode == "2pass" and websocket.status_dict_asr_online.get("is_final", False):
        #     print(f"[DEBUG] ⏭️ Skipping online result due to 2pass final mode", flush=True)
        #     return
        if len(rec_result["text"]):
            mode = "2pass-online" if "2pass" in websocket.mode else websocket.mode
            message = json.dumps(
                {
                    "mode": mode,
                    "text": rec_result["text"],
                    "wav_name": websocket.wav_name,
                    "is_final": False,  # 在线识别结果是中间结果，不是最终结果
                }
            )
            print(f"[SEND] 🚀 Sending online ASR result to client: {message}", flush=True)
            await websocket.send(message)
            print(f"[SEND] ✅ Online message sent successfully", flush=True)
        else:
            print(f"[DEBUG] 🔇 Online ASR result is empty, not sending", flush=True)


async def main():
    if len(args.certfile) > 0:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

        # Generate with Lets Encrypt, copied to this location, chown to current user and 400 permissions
        ssl_cert = args.certfile
        ssl_key = args.keyfile

        ssl_context.load_cert_chain(ssl_cert, keyfile=ssl_key)
        start_server = websockets.serve(
            ws_serve, args.host, args.port, subprotocols=["binary"], ping_interval=None, ssl=ssl_context
        )
    else:
        start_server = websockets.serve(
            ws_serve, args.host, args.port, subprotocols=["binary"], ping_interval=None
        )
    
    await start_server
    print(f"WebSocket server started on {args.host}:{args.port}")
    
    # Keep the server running
    await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
