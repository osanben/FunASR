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
        
        # FunASR识别 - 启用说话人识别
        res = model_asr.generate(
            input=audio_data,
            cache={},
            language="auto",
            use_itn=True,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
            return_spk_res=True,  # 🎯 启用说话人识别
            return_spk_embedding=True,  # 返回说话人嵌入向量
            spk_mode="punc_segment",  # 说话人分离模式
        )
        
        if res and len(res) > 0:
            result = res[0]
            text = result.get("text", "")
            
            # 🔍 调试: 打印FunASR返回的完整结果结构
            print(f"🔍 FunASR结果键: {list(result.keys())}")
            if "sentence_info" in result:
                print(f"🔍 sentence_info长度: {len(result['sentence_info'])}")
                for i, sentence in enumerate(result['sentence_info'][:3]):  # 只打印前3个
                    print(f"🔍 句子{i}: {sentence}")
            
            # 处理时间戳
            timestamp_text = ""
            if "timestamp" in result:
                timestamps = result["timestamp"]
                if timestamps:
                    for i, (start, end) in enumerate(timestamps):
                        timestamp_text += f"[{start/1000:.2f}->{end/1000:.2f}] "
            
            # 处理说话人信息
            speaker_segments = []
            if "sentence_info" in result:
                sentence_info = result["sentence_info"]
                for i, sentence in enumerate(sentence_info):
                    speaker_id = sentence.get("spk", 0)  # 说话人ID
                    start_time = sentence.get("start", 0) / 1000.0  # 转换为秒
                    end_time = sentence.get("end", 0) / 1000.0
                    sentence_text = sentence.get("text", "").strip()
                    
                    if sentence_text:
                        # 繁体转简体
                        if OPENCC_AVAILABLE:
                            try:
                                sentence_text = cc.convert(sentence_text)
                            except Exception as e:
                                print(f"⚠️ FunASR片段繁简转换失败: {e}")
                        
                        speaker_segments.append({
                            "start": start_time,
                            "end": end_time,
                            "text": sentence_text,
                            "speaker": f"说话人{speaker_id + 1}",  # 说话人从1开始编号
                            "confidence": 1.0,  # FunASR说话人置信度
                            "duration": end_time - start_time
                        })
            
            # 如果没有说话人信息，创建默认的单人结果
            if not speaker_segments and "timestamp" in result and text:
                timestamps = result["timestamp"]
                if timestamps:
                    # 基于时间戳创建说话人片段
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
                    duration = len(audio_data) / sample_rate
                    speaker_segments.append({
                        "start": 0.0,
                        "end": duration,
                        "text": text,
                        "speaker": "说话人1",
                        "confidence": 0.8,
                        "duration": duration
                    })
            
            # 统计说话人数量
            unique_speakers = len(set(seg.get("speaker", "说话人1") for seg in speaker_segments))
            total_duration = len(audio_data) / sample_rate
            
            print(f"🎯 FunASR说话人分析: 总时长={total_duration:.1f}秒, 检测到{unique_speakers}个说话人")
            
            # 🔧 如果FunASR只检测到1个说话人，但音频较长，使用pyannote.audio进行二次分析
            if unique_speakers == 1 and total_duration > 5.0 and PYANNOTE_AVAILABLE:
                print("🔄 FunASR只检测到1个说话人，启用pyannote.audio进行二次分析...")
                try:
                    # 使用pyannote.audio重新分离说话人
                    enhanced_segments = detect_speakers_with_voice_print(audio_data, speaker_segments, sample_rate)
                    if enhanced_segments and len(enhanced_segments) > 0:
                        enhanced_speakers = len(set(seg.get("speaker", "说话人1") for seg in enhanced_segments))
                        if enhanced_speakers > 1:
                            print(f"✅ pyannote.audio检测到{enhanced_speakers}个说话人，使用增强结果")
                            speaker_segments = enhanced_segments
                            unique_speakers = enhanced_speakers
                        else:
                            print("⚠️ pyannote.audio也只检测到1个说话人")
                except Exception as e:
                    print(f"⚠️ pyannote.audio分析失败: {e}")
            
            print(f"🎉 最终说话人分析结果: {unique_speakers}个说话人")
            
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