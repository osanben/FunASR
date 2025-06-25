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
from speaker_manager import SpeakerManager
from audio_segment_manager import AudioSegmentManager
try:
    from opencc import OpenCC  # 繁简转换
    cc = OpenCC('t2s')  # 繁体转简体
    OPENCC_AVAILABLE = True
except ImportError:
    print("📋 提示: 安装 opencc-python-reimplemented 可启用繁简转换功能")
    OPENCC_AVAILABLE = False

try:
    from pyannote.audio import Pipeline
    import torch
    import soundfile as sf
    PYANNOTE_AVAILABLE = True
    print("✅ pyannote.audio 可用，将使用专业说话人分离模型")
except ImportError:
    print("📋 提示: 安装 pyannote.audio 和 soundfile 可启用专业说话人分离功能")
    print("📋 安装命令: pip install pyannote.audio soundfile")
    PYANNOTE_AVAILABLE = False

# 存储WebSocket连接和任务状态
websocket_connections = {}
task_results = {}
task_lock = threading.Lock()

# 线程池用于音频处理
executor = ThreadPoolExecutor(max_workers=4)

# 说话人管理器
speaker_manager = None

# 音频片段管理器
audio_segment_manager = None

# 说话人识别模型缓存
speaker_recognition_model = None

# 解析命令行参数
parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="0.0.0.0", help="WebSocket服务器地址")
parser.add_argument("--port", type=int, default=10095, help="WebSocket端口")
parser.add_argument("--http_port", type=int, default=8080, help="HTTP上传服务端口")
parser.add_argument("--model_type", type=str, default="whisper", choices=["whisper", "paraformer", "sensevoice", "hybrid"], help="模型类型")
parser.add_argument("--whisper_model", type=str, default="base", help="Whisper模型大小")
parser.add_argument("--whisper_language", type=str, default="auto", help="Whisper识别语言")
parser.add_argument("--device", type=str, default="cpu", help="设备类型")
parser.add_argument("--ngpu", type=int, default=1, help="GPU数量")
parser.add_argument("--ncpu", type=int, default=4, help="CPU数量")
parser.add_argument("--upload_dir", type=str, default="./uploads", help="文件上传目录")
parser.add_argument("--env", type=str, default="local", choices=["local", "test"], help="运行环境：local或test")

args = parser.parse_args()

# 根据环境设置服务器地址
if args.env == "local":
    HTTP_BASE_URL = f"http://127.0.0.1:{args.http_port}"
    WS_BASE_URL = f"ws://127.0.0.1:{args.port}"
else:  # test环境
    HTTP_BASE_URL = "https://gpu-pod6859164ddd21426e6e55774b-8080.node.inscode.run"
    WS_BASE_URL = "wss://gpu-pod6859164ddd21426e6e55774b-10095.node.inscode.run"

print(f"🌍 运行环境: {args.env}")
print(f"🌐 HTTP地址: {HTTP_BASE_URL}")
print(f"🌐 WebSocket地址: {WS_BASE_URL}")

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
        
        # 临时重定向标准输出来隐藏requirements安装信息
        import sys
        from io import StringIO
        original_stdout = sys.stdout
        sys.stdout = StringIO()  # 捕获输出
        
        device = "cpu" if args.device == "mps" else args.device
        ngpu = 0 if args.device == "mps" else args.ngpu
        
        if args.model_type in ["paraformer", "hybrid"]:
            print("📦 加载 Paraformer 模型（支持时间戳和说话人分离）...")
            print("🚫 禁用模型更新检查，使用本地缓存...")
            
            model_asr = AutoModel(
                model="iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
                punc_model="iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
                spk_model="iic/speech_campplus_sv_zh-cn_16k-common",
                ngpu=ngpu,
                ncpu=args.ncpu,
                device=device,
                disable_pbar=True,
                disable_log=True,
                disable_update=True,  # 禁用自动更新检查
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
                disable_update=True,  # 禁用自动更新检查
            )
        # 恢复标准输出
        sys.stdout = original_stdout
        print("✅ FunASR 模型加载成功!")
    except Exception as e:
        # 恢复标准输出
        sys.stdout = original_stdout
        print(f"❌ FunASR 模型加载失败: {e}")

print("🎉 所有模型加载完成!")

# 初始化说话人识别模型（一次性加载）
print("🎯 初始化说话人识别模型...")
try:
    from funasr import AutoModel
    speaker_recognition_model = AutoModel(
        model="iic/speech_campplus_sv_zh-cn_16k-common",
        ngpu=0 if args.device == "mps" else args.ngpu,
        ncpu=args.ncpu,
        device="cpu" if args.device == "mps" else args.device,
        disable_pbar=True,
        disable_log=True,
        disable_update=True,  # 🎯 禁用模型更新
        # trust_remote_code=True,  # 移除这个参数避免警告
        cache_dir=None,  # 使用默认缓存目录
    )
    print("✅ 说话人识别模型加载完成!")
except Exception as e:
    print(f"⚠️ 说话人识别模型加载失败: {e}")
    speaker_recognition_model = None

# 初始化说话人管理器
print("🎯 初始化说话人管理器...")
speaker_manager = SpeakerManager()
print("✅ 说话人管理器初始化完成!")

# 初始化音频片段管理器
print("🎵 初始化音频片段管理器...")
audio_segment_manager = AudioSegmentManager()
print("✅ 音频片段管理器初始化完成!")

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
        
        # 保存音频片段
        send_progress_update(task_id, "processing", 90, "保存音频片段...")
        segment_files = {}
        
        # 从FunASR结果中提取片段进行保存
        if "funasr" in results and results["funasr"].get("speaker_segments"):
            try:
                segments_to_save = results["funasr"]["speaker_segments"]
                segment_files = audio_segment_manager.save_audio_segments(
                    task_id, audio_data, segments_to_save, sample_rate
                )
                print(f"🎵 保存了 {len(segment_files)} 个音频片段")
            except Exception as e:
                print(f"⚠️ 保存音频片段失败: {e}")
        
        # 更新最终结果
        with task_lock:
            task_results[task_id] = {
                "status": "completed",
                "progress": 100,
                "results": results,
                "segment_files": segment_files,
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
        
        # 专业的说话人分离（基于音色识别）
        speaker_segments = detect_speakers_with_voice_print(audio_data, segments, sample_rate)
        
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

def detect_speakers_with_voice_print(audio_data, segments, sample_rate=16000):
    """使用专业音色模型进行说话人分离"""
    try:
        if not segments:
            return []
        
        print("🎯 使用专业音色模型进行说话人分离...")
        
        # 方法1: 使用FunASR的CAM++说话人模型
        try:
            print("🔧 调用FunASR CAM++说话人识别模型...")
            
            # 使用专门的说话人分离参数
            res = model_asr.generate(
                input=audio_data,
                cache={},
                language="zh",
                use_itn=True,
                batch_size_s=30,  # 缩短批处理时间
                merge_vad=False,  # 关闭VAD合并，保持原始分段
                merge_length_s=3,  # 短合并长度
                return_spk_res=True,
                return_spk_embedding=True,
                spk_mode="vad_segment",  # VAD分段模式
                # 说话人相关参数
                spk_embedding_type="cam++",  # 使用CAM++模型
                cluster_backend="sklearn",  # 使用sklearn聚类
                cluster_threshold=0.7,  # 聚类阈值
            )
            
            if res and len(res) > 0:
                result = res[0]
                
                # 打印调试信息
                print(f"🔍 CAM++结果键: {list(result.keys())}")
                
                # 检查是否有说话人嵌入向量
                if "spk_embedding" in result:
                    print(f"✅ 检测到说话人嵌入向量")
                    
                if "sentence_info" in result:
                    sentence_info = result["sentence_info"]
                    print(f"🔍 句子信息: {len(sentence_info)} 个片段")
                    
                    # 收集所有说话人ID
                    speaker_ids = [sentence.get("spk", 0) for sentence in sentence_info]
                    unique_spk_ids = list(set(speaker_ids))
                    print(f"🔍 检测到的说话人ID: {unique_spk_ids}")
                    
                    if len(unique_spk_ids) > 1:
                        # 多说话人情况
                        enhanced_segments = []
                        speaker_mapping = {spk_id: i+1 for i, spk_id in enumerate(unique_spk_ids)}
                        
                        for sentence in sentence_info:
                            speaker_id = sentence.get("spk", 0)
                            start_time = sentence.get("start", 0) / 1000.0
                            end_time = sentence.get("end", 0) / 1000.0
                            sentence_text = sentence.get("text", "").strip()
                            
                            mapped_speaker_id = speaker_mapping.get(speaker_id, 1)
                            
                            if sentence_text:
                                # 繁体转简体
                                if OPENCC_AVAILABLE:
                                    try:
                                        sentence_text = cc.convert(sentence_text)
                                    except Exception as e:
                                        print(f"⚠️ 繁简转换失败: {e}")
                                
                                enhanced_segments.append({
                                    "start": start_time,
                                    "end": end_time,
                                    "text": sentence_text,
                                    "speaker": f"说话人{mapped_speaker_id}",
                                    "confidence": 0.95,  # CAM++置信度
                                    "duration": end_time - start_time
                                })
                        
                        print(f"✅ CAM++模型检测到{len(unique_spk_ids)}个说话人")
                        return enhanced_segments
                    else:
                        print(f"⚠️ CAM++模型只检测到1个说话人")
            
        except Exception as e:
            print(f"⚠️ CAM++模型调用失败: {e}")
        
        # 方法2: 尝试使用其他专业音色模型
        try:
            print("🔧 尝试使用独立的说话人识别模型...")
            
            # 直接调用说话人模型进行嵌入向量提取
            from funasr import AutoModel
            
            # 加载专门的说话人识别模型
            spk_model = AutoModel(
                model="iic/speech_campplus_sv_zh-cn_16k-common",
                device="cpu",
                disable_pbar=True,
                disable_log=True,
                disable_update=True  # 禁用自动更新检查
            )
            
            # 为每个语音段提取说话人嵌入向量
            embeddings = []
            valid_segments = []
            
            for segment in segments:
                start_time = segment.get("start", 0)
                end_time = segment.get("end", 0)
                text = segment.get("text", "").strip()
                
                if text:  # 只处理有文本的片段
                    # 提取音频片段
                    start_sample = int(start_time * sample_rate)
                    end_sample = int(end_time * sample_rate)
                    segment_audio = audio_data[start_sample:end_sample]
                    
                    if len(segment_audio) > 1600:  # 至少100ms的音频
                        try:
                            # 提取说话人嵌入向量
                            spk_res = spk_model.generate(
                                input=segment_audio,
                                cache={}
                            )
                            
                            if spk_res and len(spk_res) > 0:
                                embedding = spk_res[0].get("spk_embedding", None)
                                if embedding is not None:
                                    embeddings.append(embedding)
                                    valid_segments.append(segment)
                        except Exception as e:
                            print(f"⚠️ 片段嵌入提取失败: {e}")
                            continue
            
            if len(embeddings) >= 2:
                # 使用聚类对嵌入向量进行分组
                import numpy as np
                from sklearn.cluster import AgglomerativeClustering
                from sklearn.metrics.pairwise import cosine_similarity
                
                # 处理嵌入向量的维度问题
                processed_embeddings = []
                for emb in embeddings:
                    try:
                        # 处理torch.Tensor
                        if hasattr(emb, 'detach'):  # PyTorch tensor
                            emb = emb.detach().cpu().numpy()
                        
                        if isinstance(emb, np.ndarray):
                            # 如果是多维数组，取平均值或展平
                            if emb.ndim > 1:
                                emb = emb.flatten()
                            processed_embeddings.append(emb)
                        elif isinstance(emb, list):
                            processed_embeddings.append(np.array(emb).flatten())
                        else:
                            print(f"⚠️ 未知的嵌入向量格式: {type(emb)}")
                            continue
                    except Exception as e:
                        print(f"⚠️ 嵌入向量处理失败: {e}")
                        continue
                
                if len(processed_embeddings) < 2:
                    print("⚠️ 有效嵌入向量不足")
                    return detect_speakers_fallback(segments)
                
                # 确保所有嵌入向量长度一致
                min_length = min(len(emb) for emb in processed_embeddings)
                normalized_embeddings = []
                for emb in processed_embeddings:
                    if len(emb) >= min_length:
                        normalized_embeddings.append(emb[:min_length])
                    else:
                        # 如果长度不足，用零填充
                        padded = np.zeros(min_length)
                        padded[:len(emb)] = emb
                        normalized_embeddings.append(padded)
                
                embeddings_array = np.array(normalized_embeddings)
                print(f"🔍 嵌入向量形状: {embeddings_array.shape}")
                
                # 计算余弦相似度
                try:
                    similarity_matrix = cosine_similarity(embeddings_array)
                    distance_matrix = 1 - similarity_matrix
                except Exception as e:
                    print(f"⚠️ 相似度计算失败: {e}")
                    return detect_speakers_fallback(segments)
                
                # 使用层次聚类
                for n_clusters in range(2, min(5, len(embeddings) + 1)):
                    clustering = AgglomerativeClustering(
                        n_clusters=n_clusters,
                        metric='precomputed',
                        linkage='average'
                    )
                    labels = clustering.fit_predict(distance_matrix)
                    
                    # 检查聚类质量
                    unique_labels = len(set(labels))
                    if unique_labels > 1:
                        enhanced_segments = []
                        
                        for i, segment in enumerate(valid_segments):
                            start_time = segment.get("start", 0)
                            end_time = segment.get("end", 0)
                            text = segment.get("text", "").strip()
                            
                            speaker_id = labels[i] + 1
                            
                            # 繁体转简体
                            if OPENCC_AVAILABLE and text:
                                try:
                                    text = cc.convert(text)
                                except Exception as e:
                                    print(f"⚠️ 繁简转换失败: {e}")
                            
                            enhanced_segments.append({
                                "start": start_time,
                                "end": end_time,
                                "text": text,
                                "speaker": f"说话人{speaker_id}",
                                "confidence": 0.85,
                                "duration": end_time - start_time
                            })
                        
                        print(f"✅ 独立音色模型检测到{unique_labels}个说话人")
                        return enhanced_segments
                        
        except Exception as e:
            print(f"⚠️ 独立音色模型失败: {e}")
        
        # 回退到默认模式
        print("⚠️ 音色模型无法分离说话人，回退到单人模式")
        return detect_speakers_fallback(segments)
        
    except Exception as e:
        print(f"⚠️ 说话人分离失败，回退到简单模式: {e}")
        return detect_speakers_fallback(segments)

def detect_speakers_advanced_algorithm(audio_data, segments, sample_rate=16000):
    """使用高级音频分析进行说话人分离"""
    try:
        print("🔧 使用高级音频分析算法进行说话人分离...")
        
        import librosa
        import numpy as np
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        
        speaker_segments = []
        features_list = []
        
        # 为每个片段提取音频特征
        for i, segment in enumerate(segments):
            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            text = segment.get("text", "").strip()
            
            # 提取音频片段
            start_sample = int(start_time * sample_rate)
            end_sample = int(end_time * sample_rate)
            segment_audio = audio_data[start_sample:end_sample]
            
            if len(segment_audio) > 0:
                # 提取多维音频特征
                features = []
                
                # 1. 音频能量
                energy = np.mean(segment_audio ** 2)
                features.append(energy)
                
                # 2. 过零率
                zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(segment_audio))
                features.append(zero_crossing_rate)
                
                # 3. 频谱重心
                try:
                    spectral_centroids = librosa.feature.spectral_centroid(y=segment_audio, sr=sample_rate)
                    spectral_centroid = np.mean(spectral_centroids)
                except:
                    spectral_centroid = 1000
                features.append(spectral_centroid)
                
                # 4. 频谱滚降
                try:
                    spectral_rolloff = librosa.feature.spectral_rolloff(y=segment_audio, sr=sample_rate)
                    rolloff = np.mean(spectral_rolloff)
                except:
                    rolloff = 2000
                features.append(rolloff)
                
                # 5. MFCC前5个系数
                try:
                    mfccs = librosa.feature.mfcc(y=segment_audio, sr=sample_rate, n_mfcc=5)
                    mfcc_means = np.mean(mfccs, axis=1)
                    features.extend(mfcc_means)
                except:
                    features.extend([0] * 5)
                
                # 6. 基频特征
                try:
                    f0 = librosa.yin(segment_audio, fmin=50, fmax=400)
                    f0_mean = np.mean(f0[~np.isnan(f0)]) if len(f0[~np.isnan(f0)]) > 0 else 150
                    features.append(f0_mean)
                except:
                    features.append(150)
                
                features_list.append(features)
            else:
                # 空片段，使用默认特征
                features_list.append([0] * 11)
        
        # 如果片段太少，无法聚类
        if len(features_list) < 2:
            print("⚠️ 音频片段太少，无法进行说话人分离")
            return detect_speakers_fallback(segments)
        
        # 特征标准化
        scaler = StandardScaler()
        features_array = np.array(features_list)
        features_scaled = scaler.fit_transform(features_array)
        
        # 尝试2-4个说话人的聚类
        best_n_speakers = 2
        best_score = -1
        best_labels = None
        
        for n_speakers in range(2, min(5, len(segments) + 1)):
            try:
                kmeans = KMeans(n_clusters=n_speakers, random_state=42, n_init=10)
                labels = kmeans.fit_predict(features_scaled)
                
                # 计算轮廓系数评估聚类质量
                from sklearn.metrics import silhouette_score
                score = silhouette_score(features_scaled, labels)
                
                if score > best_score:
                    best_score = score
                    best_n_speakers = n_speakers
                    best_labels = labels
            except:
                continue
        
        # 如果聚类效果不好，回退到基于频谱特征的简单分离
        if best_labels is None or best_score < 0.3:
            print("⚠️ 聚类效果不佳，使用基于频谱特征的分离...")
            
            for i, segment in enumerate(segments):
                start_time = segment.get("start", 0)
                end_time = segment.get("end", 0)
                text = segment.get("text", "").strip()
                
                # 基于频谱重心的简单分离
                if i < len(features_list):
                    spectral_centroid = features_list[i][2]  # 频谱重心特征
                    speaker_id = 2 if spectral_centroid > 1200 else 1  # 阈值分离
                else:
                    speaker_id = 1
                
                # 繁体转简体
                if OPENCC_AVAILABLE and text:
                    try:
                        text = cc.convert(text)
                    except Exception as e:
                        print(f"⚠️ 繁简转换失败: {e}")
                
                speaker_segments.append({
                    "start": start_time,
                    "end": end_time,
                    "text": text,
                    "speaker": f"说话人{speaker_id}",
                    "duration": end_time - start_time,
                    "confidence": 0.6
                })
        else:
            # 使用聚类结果
            print(f"✅ 聚类分析完成，检测到{best_n_speakers}个说话人 (置信度: {best_score:.3f})")
            
            for i, segment in enumerate(segments):
                start_time = segment.get("start", 0)
                end_time = segment.get("end", 0)
                text = segment.get("text", "").strip()
                
                speaker_id = best_labels[i] + 1  # 说话人ID从1开始
                
                # 繁体转简体
                if OPENCC_AVAILABLE and text:
                    try:
                        text = cc.convert(text)
                    except Exception as e:
                        print(f"⚠️ 繁简转换失败: {e}")
                
                speaker_segments.append({
                    "start": start_time,
                    "end": end_time,
                    "text": text,
                    "speaker": f"说话人{speaker_id}",
                    "duration": end_time - start_time,
                    "confidence": best_score
                })
        
        # 统计说话人数量
        unique_speakers = len(set(seg["speaker"] for seg in speaker_segments))
        print(f"🎯 高级算法检测到{unique_speakers}个说话人")
        
        return speaker_segments
        
    except Exception as e:
        print(f"⚠️ 高级算法失败: {e}")
        return detect_speakers_fallback(segments)

def process_pyannote_results(diarization, segments):
    """处理pyannote.audio的结果"""
    try:
        # 将diarization结果映射到segments
        speaker_segments = []
        speaker_mapping = {}
        speaker_counter = 1
        
        for i, segment in enumerate(segments):
            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            text = segment.get("text", "").strip()
            
            # 查找这个时间段内的主要说话人
            segment_duration = end_time - start_time
            speaker_durations = {}
            
            for turn, track, speaker in diarization.itertracks(yield_label=True):
                overlap_start = max(start_time, turn.start)
                overlap_end = min(end_time, turn.end)
                overlap_duration = max(0, overlap_end - overlap_start)
                
                if overlap_duration > 0:
                    if speaker not in speaker_durations:
                        speaker_durations[speaker] = 0
                    speaker_durations[speaker] += overlap_duration
            
            if speaker_durations:
                main_speaker = max(speaker_durations.keys(), key=lambda x: speaker_durations[x])
                if main_speaker not in speaker_mapping:
                    speaker_mapping[main_speaker] = speaker_counter
                    speaker_counter += 1
                speaker_id = speaker_mapping[main_speaker]
            else:
                speaker_id = 1
            
            if OPENCC_AVAILABLE and text:
                try:
                    text = cc.convert(text)
                except Exception as e:
                    print(f"⚠️ 繁简转换失败: {e}")
            
            speaker_segments.append({
                "start": start_time,
                "end": end_time,
                "text": text,
                "speaker": f"说话人{speaker_id}",
                "duration": end_time - start_time,
                "confidence": speaker_durations.get(main_speaker, 0) / segment_duration if segment_duration > 0 else 0
            })
        
        unique_speakers = len(speaker_mapping)
        print(f"✅ pyannote.audio检测到{unique_speakers}个说话人")
        return speaker_segments
        
    except Exception as e:
        print(f"⚠️ pyannote结果处理失败: {e}")
        return segments

def detect_speakers_fallback(segments):
    """简单的后备说话人检测"""
    try:
        if not segments:
            return []
        
        speaker_segments = []
        # 默认单人模式
        for segment in segments:
            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            text = segment.get("text", "").strip()
            
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
                "speaker": "说话人1",  # 默认单人
                "duration": end_time - start_time
            })
        
        print("🎯 后备模式: 默认标记为单人讲话")
        return speaker_segments
        
    except Exception as e:
        print(f"❌ 后备说话人检测错误: {e}")
        return []

def funasr_transcribe(audio_data, sample_rate=16000):
    """使用FunASR进行语音识别（支持说话人分离）"""
    try:
        # 确保数据格式正确
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # FunASR识别 - 只做语音识别，不做说话人分离
        res = model_asr.generate(
            input=audio_data,
            cache={},
            language="auto",
            use_itn=True,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
            return_spk_res=False,  # 🎯 关闭说话人识别，直接使用专业模型
            return_spk_embedding=False,  # 不返回说话人嵌入向量
            # spk_mode="punc_segment",  # 不使用说话人分离模式
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
            
            # 🎯 跳过FunASR的说话人分析，直接使用专业模型进行说话人分离
            total_duration = len(audio_data) / sample_rate
            print(f"🎯 音频总时长={total_duration:.1f}秒，跳过FunASR说话人分析，直接使用专业模型")
            
            # 创建基础的单人片段（用于专业模型分析）
            speaker_segments = []
            if "timestamp" in result and text:
                timestamps = result["timestamp"]
                if timestamps:
                    # 基于时间戳创建初始片段
                    words = text.split()
                    for i, (start, end) in enumerate(timestamps):
                        word_text = words[i] if i < len(words) else ""
                        if word_text:
                            speaker_segments.append({
                                "start": start / 1000.0,
                                "end": end / 1000.0,
                                "text": word_text,
                                "speaker": "说话人1",
                                "confidence": 0.8,
                                "duration": (end - start) / 1000.0
                            })
                else:
                    # 没有时间戳，创建整体片段
                    speaker_segments.append({
                        "start": 0.0,
                        "end": total_duration,
                        "text": text,
                        "speaker": "说话人1",
                        "confidence": 0.8,
                        "duration": total_duration
                    })
            
            # 🔧 直接使用专业模型进行说话人分离
            if total_duration > 3.0 and PYANNOTE_AVAILABLE:
                print("🚀 使用专业模型进行说话人分离...")
                try:
                    # 使用pyannote.audio进行说话人分离
                    enhanced_segments = detect_speakers_with_voice_print(audio_data, speaker_segments, sample_rate)
                    if enhanced_segments and len(enhanced_segments) > 0:
                        enhanced_speakers = len(set(seg.get("speaker", "说话人1") for seg in enhanced_segments))
                        print(f"✅ 专业模型检测到{enhanced_speakers}个说话人")
                        speaker_segments = enhanced_segments
                    else:
                        print("⚠️ 专业模型分析失败，使用默认单人模式")
                except Exception as e:
                    print(f"⚠️ 专业模型分析失败: {e}")
            
            unique_speakers = len(set(seg.get("speaker", "说话人1") for seg in speaker_segments))
            print(f"🎉 最终说话人分析结果: {unique_speakers}个说话人")
            
            # 🎯 说话人姓名匹配
            if speaker_manager and speaker_segments:
                print("🔍 开始说话人姓名匹配...")
                enhanced_segments = []
                
                for segment in speaker_segments:
                    # 提取音频片段
                    start_sample = int(segment["start"] * sample_rate)
                    end_sample = int(segment["end"] * sample_rate)
                    
                    # 确保索引在有效范围内
                    start_sample = max(0, start_sample)
                    end_sample = min(len(audio_data), end_sample)
                    
                    if end_sample > start_sample:
                        audio_segment = audio_data[start_sample:end_sample]
                        
                        # 匹配说话人 - 传递专业模型
                        matched_name, similarity, match_info = speaker_manager.match_speaker(
                            audio_segment, model_asr=speaker_recognition_model
                        )
                        
                        # 更新说话人信息
                        if matched_name:
                            segment["speaker"] = matched_name
                            segment["speaker_similarity"] = similarity
                            segment["match_info"] = match_info
                            print(f"✅ 匹配成功: {segment['text'][:20]}... -> {matched_name} (相似度: {similarity:.3f})")
                        else:
                            segment["speaker_similarity"] = similarity
                            segment["match_info"] = match_info
                            print(f"❓ 未匹配: {segment['text'][:20]}... -> {segment['speaker']} (相似度: {similarity:.3f})")
                    
                    enhanced_segments.append(segment)
                
                speaker_segments = enhanced_segments
                print("🎯 说话人姓名匹配完成!")
            
            return {
                "text": text,
                "timestamp": timestamp_text.strip(),
                "language": "zh",
                "result": result,
                "speaker_segments": speaker_segments
            }
        else:
            return {"text": "", "timestamp": "", "language": "zh", "result": {}, "speaker_segments": []}
            
    except Exception as e:
        print(f"❌ FunASR识别错误: {e}")
        import traceback
        traceback.print_exc()
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
    """递归清理对象中的NaN值和不可序列化的numpy类型"""
    import numpy as np
    
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    elif isinstance(obj, (float, np.floating)):
        # 处理float和numpy浮点类型
        if np.isnan(obj) or np.isinf(obj):
            return 0.0
        return float(obj)  # 转换为Python原生float
    elif isinstance(obj, (int, np.integer)):
        # 处理numpy整数类型
        return int(obj)
    elif isinstance(obj, np.ndarray):
        # 处理numpy数组
        return clean_nan_values(obj.tolist())
    elif hasattr(obj, 'item'):
        # 处理numpy标量
        return clean_nan_values(obj.item())
    else:
        return obj

async def status_handler(request):
    """查询任务状态和结果"""
    task_id = request.match_info['task_id']
    
    with task_lock:
        if task_id in task_results:
            result = task_results[task_id]
            
            # 添加音频片段URL信息
            if result.get("status") == "completed" and "results" in result:
                # 获取音频片段信息
                segments_info = audio_segment_manager.list_task_segments(task_id)
                
                # 为每个说话人分离结果添加播放URL
                for model_name, model_result in result["results"].items():
                    if "speaker_segments" in model_result:
                        for i, segment in enumerate(model_result["speaker_segments"]):
                            segment_id = f"{task_id}_segment_{i+1}"
                            
                            # 查找对应的音频文件信息
                            for seg_info in segments_info:
                                if seg_info["segment_id"] == segment_id:
                                    segment["audio_url"] = f"{HTTP_BASE_URL}/audio_segments/{seg_info['relative_path']}"
                                    segment["file_size"] = seg_info["file_size"]
                                    break
            
            # 清理NaN值
            cleaned_result = clean_nan_values(result)
            return web.json_response(cleaned_result, dumps=lambda obj: json.dumps(obj, ensure_ascii=False, indent=2))
        else:
            return web.json_response({"error": "任务不存在"}, status=404)

async def realtime_handler(request):
    """实时录音页面处理器"""
    try:
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        realtime_file = os.path.join(current_dir, 'realtime_demo.html')
        
        print(f"🔍 尝试读取实时录音页面: {realtime_file}")
        
        with open(realtime_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("✅ 实时录音页面加载成功")
        return web.Response(text=content, content_type='text/html')
    except FileNotFoundError as e:
        print(f"❌ 实时录音页面未找到: {e}")
        return web.Response(text=f"实时录音页面未找到: {realtime_file}", status=404)
    except Exception as e:
        print(f"❌ 加载实时录音页面错误: {e}")
        return web.Response(text=f"加载页面错误: {str(e)}", status=500)

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
# 说话人管理API处理函数
async def register_speaker_handler(request):
    """注册新说话人"""
    try:
        reader = await request.multipart()
        
        speaker_name = None
        audio_file_data = None
        audio_filename = None
        
        # 解析multipart数据
        async for field in reader:
            if field.name == 'speaker_name':
                speaker_name = await field.text()
            elif field.name == 'speaker_audio':
                audio_filename = field.filename
                audio_file_data = await field.read()
        
        if not speaker_name:
            return web.json_response({"error": "缺少说话人姓名"}, status=400)
        
        if not audio_file_data:
            return web.json_response({"error": "缺少语音样本文件"}, status=400)
        
        # 保存临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{audio_filename}")
        temp_file.write(audio_file_data)
        temp_file.close()
        
        try:
            # 注册说话人
            print(f"🎯 开始注册说话人: {speaker_name}, 文件: {temp_file.name}")
            success, message = speaker_manager.register_speaker(
                speaker_name, temp_file.name, model_asr=speaker_recognition_model or model_asr
            )
            print(f"📊 注册结果: success={success}, message={message}")
            
            if success:
                return web.json_response({"message": message})
            else:
                return web.json_response({"error": message}, status=400)
                
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file.name)
            except:
                pass
                
    except Exception as e:
        print(f"❌ 注册说话人错误: {e}")
        return web.json_response({"error": f"注册失败: {str(e)}"}, status=500)

async def list_speakers_handler(request):
    """获取已注册说话人列表"""
    try:
        speakers = speaker_manager.get_registered_speakers()
        return web.json_response({"speakers": speakers})
    except Exception as e:
        print(f"❌ 获取说话人列表错误: {e}")
        return web.json_response({"error": f"获取列表失败: {str(e)}"}, status=500)

async def delete_speaker_handler(request):
    """删除说话人"""
    try:
        data = await request.json()
        speaker_id = data.get("speaker_id")
        
        if not speaker_id:
            return web.json_response({"error": "缺少说话人ID"}, status=400)
        
        success, message = speaker_manager.delete_speaker(speaker_id)
        
        if success:
            return web.json_response({"message": message})
        else:
            return web.json_response({"error": message}, status=400)
            
    except Exception as e:
        print(f"❌ 删除说话人错误: {e}")
        return web.json_response({"error": f"删除失败: {str(e)}"}, status=500)

async def update_segment_speaker_handler(request):
    """更新音频片段的说话人标签"""
    try:
        data = await request.json()
        task_id = data.get("task_id")
        segment_index = data.get("segment_index")
        new_speaker_name = data.get("speaker_name", "").strip()
        audio_url = data.get("audio_url")  # 用于自动注册新说话人
        
        if not task_id or segment_index is None or not new_speaker_name:
            return web.json_response({"error": "缺少必要参数"}, status=400)
        
        # 更新任务结果中的说话人标签
        with task_lock:
            if task_id not in task_results:
                return web.json_response({"error": "任务不存在"}, status=404)
            
            task_result = task_results[task_id]
            
            # 更新FunASR结果中的说话人标签
            if "results" in task_result and "funasr" in task_result["results"]:
                funasr_result = task_result["results"]["funasr"]
                if "speaker_segments" in funasr_result and segment_index < len(funasr_result["speaker_segments"]):
                    # 获取原始说话人名称
                    old_speaker = funasr_result["speaker_segments"][segment_index].get("speaker", "")
                    
                    # 更新说话人标签
                    funasr_result["speaker_segments"][segment_index]["speaker"] = new_speaker_name
                    
                    print(f"🔄 更新片段{segment_index}说话人: {old_speaker} -> {new_speaker_name}")
                    
                    # 如果是新的说话人名称，尝试自动注册
                    if new_speaker_name not in [old_speaker] and audio_url:
                        try:
                            # 检查是否已经注册过这个说话人
                            registered_speakers = speaker_manager.get_registered_speakers()
                            speaker_exists = any(s["name"] == new_speaker_name for s in registered_speakers)
                            
                            if not speaker_exists:
                                # 下载音频片段并注册新说话人
                                success = await auto_register_speaker_from_segment(
                                    new_speaker_name, audio_url, task_id, segment_index
                                )
                                if success:
                                    print(f"✅ 自动注册新说话人: {new_speaker_name}")
                                else:
                                    print(f"⚠️ 自动注册说话人失败: {new_speaker_name}")
                        except Exception as e:
                            print(f"⚠️ 自动注册说话人出错: {e}")
                    
                    return web.json_response({
                        "message": f"说话人标签已更新为: {new_speaker_name}",
                        "updated_segment": funasr_result["speaker_segments"][segment_index]
                    })
                else:
                    return web.json_response({"error": "片段索引无效"}, status=400)
            else:
                return web.json_response({"error": "未找到说话人分离结果"}, status=400)
            
    except Exception as e:
        print(f"❌ 更新说话人标签错误: {e}")
        return web.json_response({"error": f"更新失败: {str(e)}"}, status=500)

async def auto_register_speaker_from_segment(speaker_name, audio_url, task_id, segment_index):
    """从音频片段自动注册新说话人"""
    try:
        # 构建本地音频文件路径
        import urllib.parse
        parsed_url = urllib.parse.urlparse(audio_url)
        relative_path = parsed_url.path.replace('/audio_segments/', '')
        
        audio_file_path = Path("./audio_segments") / relative_path
        
        if not audio_file_path.exists():
            print(f"❌ 音频文件不存在: {audio_file_path}")
            return False
        
        # 使用说话人管理器注册
        success, message = speaker_manager.register_speaker(
            speaker_name, str(audio_file_path), model_asr=speaker_recognition_model or model_asr
        )
        
        if success:
            print(f"🎉 从片段自动注册说话人成功: {speaker_name}")
            return True
        else:
            print(f"❌ 自动注册说话人失败: {message}")
            return False
            
    except Exception as e:
        print(f"❌ 自动注册说话人异常: {e}")
        return False

async def websocket_handler(websocket):
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
async def audio_segment_handler(request):
    """音频片段文件服务"""
    try:
        # 获取文件路径参数
        task_id = request.match_info.get('task_id')
        filename = request.match_info.get('filename')
        
        print(f"🔍 音频片段请求: task_id={task_id}, filename={filename}")
        
        if not task_id or not filename:
            print("❌ 缺少必要参数")
            return web.Response(text="参数错误", status=400)
        
        # 构建文件路径
        file_path = Path("./audio_segments") / task_id / filename
        print(f"📁 音频文件路径: {file_path}")
        print(f"📊 文件是否存在: {file_path.exists()}")
        
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            # 列出目录内容进行调试
            task_dir = Path("./audio_segments") / task_id
            if task_dir.exists():
                files = list(task_dir.glob("*"))
                print(f"📂 目录 {task_dir} 中的文件: {[f.name for f in files]}")
            else:
                print(f"❌ 任务目录不存在: {task_dir}")
            return web.Response(text=f"文件不存在: {filename}", status=404)
        
        print(f"✅ 返回音频文件: {file_path}")
        
        # 返回音频文件
        return web.FileResponse(
            path=str(file_path),
            headers={
                'Content-Type': 'audio/wav',
                'Cache-Control': 'public, max-age=3600',
                'Access-Control-Allow-Origin': '*'
            }
        )
        
    except Exception as e:
        print(f"❌ 音频片段服务错误: {e}")
        import traceback
        traceback.print_exc()
        return web.Response(text="服务器错误", status=500)

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
    
    # 添加实时录音页面路由
    app.router.add_get('/realtime', realtime_handler)
    
    # 添加说话人管理API
    app.router.add_post('/register_speaker', register_speaker_handler)
    app.router.add_get('/list_speakers', list_speakers_handler)
    app.router.add_post('/delete_speaker', delete_speaker_handler)
    app.router.add_post('/update_segment_speaker', update_segment_speaker_handler)
    
    # 添加音频片段服务路由
    app.router.add_get('/audio_segments/{task_id}/{filename}', audio_segment_handler)
    
    # 添加静态文件路由
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app.router.add_get('/recorder-core.js', lambda request: web.FileResponse(os.path.join(current_dir, 'recorder-core.js')))
    app.router.add_get('/pcm.js', lambda request: web.FileResponse(os.path.join(current_dir, 'pcm.js')))
    
    # 添加upload_demo.html页面路由（动态替换服务器地址）
    async def upload_demo_handler(request):
        try:
            html_file = os.path.join(current_dir, 'upload_demo.html')
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 替换服务器地址
            html_content = html_content.replace(
                'https://gpu-pod6859164ddd21426e6e55774b-8080.node.inscode.run', 
                HTTP_BASE_URL
            )
            html_content = html_content.replace(
                'wss://gpu-pod6859164ddd21426e6e55774b-10095.node.inscode.run/', 
                WS_BASE_URL + '/'
            )
            
            return web.Response(text=html_content, content_type='text/html')
        except Exception as e:
            return web.Response(text=f"Error loading page: {e}", status=500)
    
    app.router.add_get('/upload_demo.html', upload_demo_handler)
    app.router.add_get('/upload_demo', upload_demo_handler)
    
    # 添加静态文件服务（可选）
    async def root_handler(request):
        html_template = """
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
    
    <!-- 说话人编辑模态框 -->
    <div id="speakerModal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
        <div style="background-color: #fefefe; margin: 15% auto; padding: 20px; border-radius: 8px; width: 400px; max-width: 90%;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="margin: 0; color: #333;">编辑说话人</h3>
                <button onclick="closeSpeakerModal()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #999;">&times;</button>
            </div>
            
            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">当前说话人:</label>
                <span id="currentSpeakerName" style="color: #007bff; font-size: 16px;"></span>
            </div>
            
            <div style="margin-bottom: 15px;">
                <label for="speakerSelect" style="display: block; margin-bottom: 5px; font-weight: bold;">选择已注册的说话人:</label>
                <select id="speakerSelect" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;">
                    <option value="">-- 选择说话人 --</option>
                </select>
            </div>
            
            <div style="margin-bottom: 20px;">
                <label for="newSpeakerName" style="display: block; margin-bottom: 5px; font-weight: bold;">或输入新的说话人姓名:</label>
                <input type="text" id="newSpeakerName" placeholder="输入新说话人姓名" 
                       style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;">
                <small style="color: #666; font-size: 12px;">输入新姓名将自动注册为新说话人</small>
            </div>
            
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button onclick="closeSpeakerModal()" 
                        style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    取消
                </button>
                <button onclick="saveSpeakerChange()" 
                        style="padding: 8px 16px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    保存
                </button>
            </div>
        </div>
    </div>
    
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
            ws = new WebSocket(`{WS_BASE_URL}/`);
            
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
                            
                            for (let i = 0; i < result.speaker_segments.length; i++) {
                                const segment = result.speaker_segments[i];
                                const speakerColor = segment.speaker === '说话人1' ? '#007bff' : '#28a745';
                                const segmentId = `segment_${i}`;
                                
                                html += `<div style="margin: 8px 0; padding: 12px; border-left: 4px solid ${speakerColor}; background: white; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <div style="flex-grow: 1;">
                                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                                                <strong style="color: ${speakerColor};" id="speaker_name_${i}">${segment.speaker}</strong>
                                                <button onclick="editSpeaker(${i}, '${segment.speaker}', '${segment.audio_url || ''}', currentTaskId)" 
                                                        style="background: #17a2b8; color: white; border: none; padding: 2px 6px; border-radius: 3px; cursor: pointer; font-size: 10px;"
                                                        title="编辑说话人">
                                                    ✏️ 编辑
                                                </button>
                                            </div>
                                            <div>
                                                <span style="color: #666; font-size: 12px;">[${segment.start.toFixed(2)}s - ${segment.end.toFixed(2)}s]</span>
                                                ${segment.duration ? `<span style="color: #999; font-size: 11px;">(${segment.duration.toFixed(2)}s)</span>` : ''}
                                            </div>
                                        </div>`;
                                
                                // 添加播放按钮（如果有音频URL）
                                if (segment.audio_url) {
                                    html += `<div>
                                        <button onclick="playSegment('${segment.audio_url}', '${segmentId}')" 
                                                style="background: #28a745; color: white; border: none; padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 12px; margin-right: 5px;"
                                                title="播放此片段">
                                            🔊 播放
                                        </button>
                                        <span style="color: #999; font-size: 10px;">
                                            ${segment.file_size ? `(${(segment.file_size/1024).toFixed(1)}KB)` : ''}
                                        </span>
                                    </div>`;
                                }
                                
                                html += `</div>
                                    <div style="font-size: 14px; line-height: 1.4; color: #333;">${segment.text}</div>
                                    <audio id="audio_${segmentId}" style="width: 100%; margin-top: 8px; display: none;" controls preload="none">
                                        ${segment.audio_url ? `<source src="${segment.audio_url}" type="audio/wav">` : ''}
                                        您的浏览器不支持音频播放。
                                    </audio>
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
        
        // 播放音频片段函数
        function playSegment(audioUrl, segmentId) {
            const audioElement = document.getElementById(`audio_${segmentId}`);
            
            if (audioElement) {
                // 显示音频控件
                audioElement.style.display = 'block';
                
                // 如果还没有加载音频源，设置并加载
                if (audioElement.src !== audioUrl) {
                    audioElement.src = audioUrl;
                    audioElement.load();
                }
                
                // 播放音频
                audioElement.play().catch(error => {
                    console.error('播放音频失败:', error);
                    alert('播放音频失败，请检查音频文件是否存在');
                });
            }
        }
        
        // 全局变量存储当前编辑的信息
        let currentEditInfo = {};
        
        // 编辑说话人函数
        async function editSpeaker(segmentIndex, currentSpeaker, audioUrl, taskId) {
            try {
                // 保存当前编辑信息
                currentEditInfo = {
                    segmentIndex,
                    currentSpeaker,
                    audioUrl,
                    taskId
                };
                
                // 获取已注册的说话人列表
                const response = await fetch('/list_speakers');
                const data = await response.json();
                const registeredSpeakers = data.speakers || [];
                
                // 更新模态框内容
                document.getElementById('currentSpeakerName').textContent = currentSpeaker;
                
                // 填充下拉选择框
                const speakerSelect = document.getElementById('speakerSelect');
                speakerSelect.innerHTML = '<option value="">-- 选择已注册的说话人 --</option>';
                
                for (const speaker of registeredSpeakers) {
                    const option = document.createElement('option');
                    option.value = speaker.name;
                    option.textContent = `${speaker.name} (注册于 ${new Date(speaker.registration_time * 1000).toLocaleString()})`;
                    if (speaker.name === currentSpeaker) {
                        option.selected = true;
                    }
                    speakerSelect.appendChild(option);
                }
                
                // 清空新姓名输入框
                document.getElementById('newSpeakerName').value = '';
                
                // 显示模态框
                document.getElementById('speakerModal').style.display = 'block';
                
            } catch (error) {
                console.error('加载说话人列表失败:', error);
                alert('加载说话人列表失败，请检查网络连接');
            }
        }
        
        // 关闭模态框
        function closeSpeakerModal() {
            document.getElementById('speakerModal').style.display = 'none';
            currentEditInfo = {};
        }
        
        // 处理下拉选择变化
        document.getElementById('speakerSelect').addEventListener('change', function() {
            if (this.value) {
                document.getElementById('newSpeakerName').value = '';
            }
        });
        
        // 处理新姓名输入
        document.getElementById('newSpeakerName').addEventListener('input', function() {
            if (this.value.trim()) {
                document.getElementById('speakerSelect').value = '';
            }
        });
        
        // 保存说话人变更
        async function saveSpeakerChange() {
            try {
                const selectedSpeaker = document.getElementById('speakerSelect').value;
                const newSpeakerName = document.getElementById('newSpeakerName').value.trim();
                
                let finalSpeakerName = '';
                
                if (selectedSpeaker) {
                    finalSpeakerName = selectedSpeaker;
                } else if (newSpeakerName) {
                    finalSpeakerName = newSpeakerName;
                } else {
                    alert('请选择一个已注册的说话人或输入新的姓名');
                    return;
                }
                
                if (finalSpeakerName === currentEditInfo.currentSpeaker) {
                    closeSpeakerModal();
                    return;
                }
                
                // 发送更新请求
                const updateResponse = await fetch('/update_segment_speaker', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        task_id: currentEditInfo.taskId,
                        segment_index: currentEditInfo.segmentIndex,
                        speaker_name: finalSpeakerName,
                        audio_url: currentEditInfo.audioUrl
                    })
                });
                
                const updateResult = await updateResponse.json();
                
                if (updateResponse.ok) {
                    // 更新页面显示
                    const speakerElement = document.getElementById(`speaker_name_${currentEditInfo.segmentIndex}`);
                    if (speakerElement) {
                        speakerElement.textContent = finalSpeakerName;
                        // 根据说话人名称设置颜色
                        const colors = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8', '#6f42c1'];
                        const colorIndex = finalSpeakerName.length % colors.length;
                        speakerElement.style.color = colors[colorIndex];
                    }
                    
                    // 显示成功消息
                    showMessage(`✅ ${updateResult.message}`, 'success');
                    
                    // 关闭模态框
                    closeSpeakerModal();
                    
                    console.log('说话人更新成功:', updateResult);
                } else {
                    alert(`更新失败: ${updateResult.error}`);
                }
                
            } catch (error) {
                console.error('保存说话人变更失败:', error);
                alert('保存失败，请检查网络连接');
            }
        }
        
        // 显示消息函数
        function showMessage(message, type = 'success') {
            const messageDiv = document.createElement('div');
            const bgColor = type === 'success' ? '#d4edda' : '#f8d7da';
            const textColor = type === 'success' ? '#155724' : '#721c24';
            const borderColor = type === 'success' ? '#c3e6cb' : '#f5c6cb';
            
            messageDiv.style.cssText = `position: fixed; top: 20px; right: 20px; background: ${bgColor}; color: ${textColor}; padding: 10px 15px; border-radius: 4px; z-index: 1001; border: 1px solid ${borderColor}; box-shadow: 0 2px 4px rgba(0,0,0,0.1);`;
            messageDiv.textContent = message;
            document.body.appendChild(messageDiv);
            
            // 3秒后自动移除消息
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.parentNode.removeChild(messageDiv);
                }
            }, 3000);
        }
    </script>
</body>
</html>
        """
        
        # 替换WebSocket地址
        html_content = html_template.replace('{WS_BASE_URL}', WS_BASE_URL)
        return web.Response(text=html_content, content_type='text/html')
    
    app.router.add_get('/', root_handler)
    
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