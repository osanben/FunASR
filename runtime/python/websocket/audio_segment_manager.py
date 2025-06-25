import os
import json
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
import hashlib
import time
from typing import List, Dict, Optional

class AudioSegmentManager:
    """音频片段管理器 - 负责保存、管理分离的音频片段"""
    
    def __init__(self, segments_dir="./audio_segments"):
        self.segments_dir = Path(segments_dir)
        self.segments_dir.mkdir(exist_ok=True)
        
        # 元数据文件
        self.metadata_file = self.segments_dir / "segments_metadata.json"
        
        # 加载现有元数据
        self.segments_metadata = self._load_metadata()
        
    def _load_metadata(self):
        """加载音频片段元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 加载音频片段元数据失败: {e}")
        return {}
    
    def _save_metadata(self):
        """保存元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.segments_metadata, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存音频片段元数据失败: {e}")
            return False
    
    def save_audio_segments(self, task_id: str, audio_data: np.ndarray, 
                           segments: List[Dict], sample_rate: int = 16000) -> Dict[str, str]:
        """
        保存音频片段到本地文件
        
        Args:
            task_id: 任务ID
            audio_data: 原始音频数据
            segments: 分离的片段信息
            sample_rate: 采样率
            
        Returns:
            Dict[segment_id, file_path]: 片段ID到文件路径的映射
        """
        try:
            print(f"🎵 开始保存音频片段，任务ID: {task_id}")
            
            # 创建任务目录
            task_dir = self.segments_dir / task_id
            task_dir.mkdir(exist_ok=True)
            
            segment_files = {}
            task_metadata = {
                "task_id": task_id,
                "created_time": time.time(),
                "total_segments": len(segments),
                "sample_rate": sample_rate,
                "segments": {}
            }
            
            for i, segment in enumerate(segments):
                try:
                    # 提取时间信息 (已经是秒为单位)
                    start_time = segment.get("start", 0)  # 已经是秒
                    end_time = segment.get("end", 0)
                    text = segment.get("text", "").strip()
                    speaker = segment.get("speaker", f"说话人{i+1}")
                    
                    # 计算音频片段
                    start_sample = int(start_time * sample_rate)
                    end_sample = int(end_time * sample_rate)
                    
                    # 确保索引在有效范围内
                    start_sample = max(0, start_sample)
                    end_sample = min(len(audio_data), end_sample)
                    
                    if start_sample >= end_sample:
                        print(f"⚠️ 片段{i+1}时间无效，跳过")
                        continue
                    
                    segment_audio = audio_data[start_sample:end_sample]
                    
                    # 生成片段ID和文件名
                    segment_id = f"{task_id}_segment_{i+1}"
                    filename = f"segment_{i+1:03d}_{speaker.replace(' ', '_')}.wav"
                    file_path = task_dir / filename
                    
                    # 保存音频文件
                    sf.write(str(file_path), segment_audio, sample_rate)
                    
                    # 记录元数据
                    segment_info = {
                        "segment_id": segment_id,
                        "filename": filename,
                        "file_path": str(file_path),
                        "relative_path": f"{task_id}/{filename}",
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": end_time - start_time,
                        "text": text,
                        "speaker": speaker,
                        "file_size": os.path.getsize(file_path)
                    }
                    
                    task_metadata["segments"][segment_id] = segment_info
                    segment_files[segment_id] = str(file_path)
                    
                    print(f"✅ 保存片段{i+1}: {filename} ({end_time-start_time:.2f}s)")
                    
                except Exception as e:
                    print(f"❌ 保存片段{i+1}失败: {e}")
                    continue
            
            # 保存任务元数据
            self.segments_metadata[task_id] = task_metadata
            self._save_metadata()
            
            print(f"🎉 音频片段保存完成: {len(segment_files)} 个片段")
            return segment_files
            
        except Exception as e:
            print(f"❌ 保存音频片段失败: {e}")
            return {}
    
    def get_segment_info(self, task_id: str, segment_id: str = None) -> Optional[Dict]:
        """获取片段信息"""
        if task_id not in self.segments_metadata:
            return None
            
        task_data = self.segments_metadata[task_id]
        
        if segment_id:
            return task_data["segments"].get(segment_id)
        else:
            return task_data
    
    def get_segment_file_path(self, task_id: str, segment_id: str) -> Optional[str]:
        """获取片段文件路径"""
        segment_info = self.get_segment_info(task_id, segment_id)
        if segment_info:
            return segment_info.get("file_path")
        return None
    
    def list_task_segments(self, task_id: str) -> List[Dict]:
        """列出任务的所有片段"""
        task_data = self.get_segment_info(task_id)
        if task_data:
            return list(task_data["segments"].values())
        return []
    
    def cleanup_old_segments(self, max_age_hours: int = 24):
        """清理旧的音频片段"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            tasks_to_remove = []
            
            for task_id, task_data in self.segments_metadata.items():
                created_time = task_data.get("created_time", 0)
                if current_time - created_time > max_age_seconds:
                    # 删除文件
                    task_dir = self.segments_dir / task_id
                    if task_dir.exists():
                        import shutil
                        shutil.rmtree(task_dir)
                    tasks_to_remove.append(task_id)
            
            # 更新元数据
            for task_id in tasks_to_remove:
                del self.segments_metadata[task_id]
            
            if tasks_to_remove:
                self._save_metadata()
                print(f"🗑️ 清理了 {len(tasks_to_remove)} 个过期任务的音频片段")
                
        except Exception as e:
            print(f"❌ 清理音频片段失败: {e}")
    
    def get_segment_url(self, task_id: str, segment_id: str, base_url: str = "http://localhost:8080") -> Optional[str]:
        """获取片段的访问URL"""
        segment_info = self.get_segment_info(task_id, segment_id)
        if segment_info:
            relative_path = segment_info.get("relative_path")
            return f"{base_url}/audio_segments/{relative_path}"
        return None 