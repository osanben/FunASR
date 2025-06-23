#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
说话人分离修复脚本
用于添加高级音频分析算法来分离说话人
"""

import re

def fix_speaker_separation():
    """修复说话人分离功能"""
    
    # 要添加的高级分离算法函数
    advanced_algorithm_code = '''
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

'''
    
    # 读取原文件
    with open('funasr_upload_server.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经存在高级算法函数
    if 'detect_speakers_advanced_algorithm' not in content:
        print("🔧 添加高级说话人分离算法...")
        
        # 在 detect_speakers_fallback 函数之前插入新函数
        insert_position = content.find('def detect_speakers_fallback(segments):')
        if insert_position != -1:
            new_content = (content[:insert_position] + 
                          advanced_algorithm_code + 
                          content[insert_position:])
            
            # 写回文件
            with open('funasr_upload_server.py', 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("✅ 高级说话人分离算法添加成功！")
        else:
            print("❌ 无法找到插入位置")
    else:
        print("✅ 高级说话人分离算法已存在")
    
    # 安装必要的依赖
    print("🔧 检查并安装必要的依赖...")
    import subprocess
    import sys
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "scikit-learn"])
        print("✅ scikit-learn 安装成功")
    except:
        print("⚠️ scikit-learn 安装失败，请手动安装: pip install scikit-learn")
    
    print("🎉 说话人分离修复完成！")
    print("📝 现在可以重启服务器测试: ./start_upload_server.sh --model_type paraformer")

if __name__ == "__main__":
    fix_speaker_separation() 