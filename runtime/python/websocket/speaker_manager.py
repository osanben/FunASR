import os
import json
import numpy as np
import librosa
from pathlib import Path
import hashlib
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import time

class SpeakerManager:
    """说话人管理器 - 负责声纹注册、存储和匹配"""
    
    def __init__(self, database_dir="./speaker_database"):
        self.database_dir = Path(database_dir)
        self.database_dir.mkdir(exist_ok=True)
        
        # 声纹数据库文件
        self.embeddings_file = self.database_dir / "speaker_embeddings.pkl"
        self.metadata_file = self.database_dir / "speaker_metadata.json"
        
        # 加载现有数据库
        self.speaker_embeddings = self._load_embeddings()
        self.speaker_metadata = self._load_metadata()
        
        # 相似度阈值
        self.similarity_threshold = 0.75
        
    def _load_embeddings(self):
        """加载说话人嵌入向量数据库"""
        if self.embeddings_file.exists():
            try:
                with open(self.embeddings_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"⚠️ 加载嵌入向量失败: {e}")
        return {}
    
    def _load_metadata(self):
        """加载说话人元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 加载元数据失败: {e}")
        return {}
    
    def _save_embeddings(self):
        """保存嵌入向量数据库"""
        try:
            with open(self.embeddings_file, 'wb') as f:
                pickle.dump(self.speaker_embeddings, f)
            return True
        except Exception as e:
            print(f"❌ 保存嵌入向量失败: {e}")
            return False
    
    def _save_metadata(self):
        """保存元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.speaker_metadata, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存元数据失败: {e}")
            return False
    
    def extract_speaker_embedding(self, audio_data, sample_rate=16000, model_asr=None):
        """提取说话人嵌入向量"""
        try:
            print(f"🔬 开始提取说话人嵌入向量...")
            print(f"📊 音频数据类型: {type(audio_data)}")
            print(f"📊 音频数据形状: {audio_data.shape if hasattr(audio_data, 'shape') else 'N/A'}")
            print(f"📊 音频数据长度: {len(audio_data)}")
            print(f"📊 采样率: {sample_rate}")
            print(f"📊 model_asr类型: {type(model_asr)}")
            
            # 强制使用专门的说话人识别模型，不使用ASR模型
            print("🤖 创建专门的说话人识别模型...")
            from funasr import AutoModel
            # 使用专门的说话人识别模型
            spk_model = AutoModel(
                model="iic/speech_campplus_sv_zh-cn_16k-common",
                device="cpu",
                disable_pbar=True,
                disable_log=True,
                disable_update=True
            )
            print("✅ 说话人识别模型创建成功")
            
            # 确保音频格式正确
            if audio_data.dtype != np.float32:
                print(f"🔄 转换音频数据类型: {audio_data.dtype} -> float32")
                audio_data = audio_data.astype(np.float32)
            
            print("🚀 调用说话人模型生成嵌入向量...")
            # 使用说话人模型的正确参数
            result = spk_model.generate(
                input=audio_data,
                cache={},
                batch_size_s=60,  # 批处理大小
                output_dir=None,  # 不输出文件
                param_dict=None   # 使用默认参数
            )
            
            print(f"📊 模型返回结果类型: {type(result)}")
            print(f"📊 模型返回结果长度: {len(result) if result else 0}")
            
            if result and len(result) > 0:
                print(f"🔍 检查结果内容...")
                print(f"📊 结果[0]类型: {type(result[0])}")
                print(f"📊 结果[0]键: {list(result[0].keys()) if isinstance(result[0], dict) else 'N/A'}")
                
                # 说话人模型直接返回嵌入向量
                if isinstance(result[0], dict):
                    # 检查可能的嵌入向量字段
                    possible_keys = ['embedding', 'spk_embedding', 'speaker_embedding', 'output']
                    embedding = None
                    
                    for key in possible_keys:
                        if key in result[0]:
                            embedding = result[0][key]
                            print(f"✅ 找到嵌入向量字段: {key}")
                            break
                    
                    if embedding is None:
                        # 如果没有找到标准字段，尝试直接使用结果
                        print("🔄 尝试直接使用模型输出...")
                        # 对于CAM++模型，可能直接返回嵌入向量
                        if len(result[0]) == 1:
                            embedding = list(result[0].values())[0]
                            print(f"📊 使用第一个值作为嵌入向量")
                else:
                    # 如果结果不是字典，可能直接是嵌入向量
                    embedding = result[0]
                    print(f"📊 直接使用结果作为嵌入向量")
                
                print(f"📊 嵌入向量类型: {type(embedding)}")
                
                if embedding is not None:
                    print("✅ 找到嵌入向量，开始处理...")
                    # 处理不同格式的嵌入向量
                    if hasattr(embedding, 'detach'):  # PyTorch tensor
                        print("🔄 处理PyTorch tensor...")
                        embedding = embedding.detach().cpu().numpy()
                    
                    if isinstance(embedding, np.ndarray):
                        print(f"📊 NumPy数组形状: {embedding.shape}")
                        if embedding.ndim > 1:
                            print("🔄 展平多维数组...")
                            embedding = embedding.flatten()
                        print(f"📊 最终嵌入向量长度: {len(embedding)}")
                        print(f"📊 嵌入向量范围: [{embedding.min():.6f}, {embedding.max():.6f}]")
                        return embedding
                    elif isinstance(embedding, list):
                        print("🔄 处理列表格式...")
                        embedding_array = np.array(embedding).flatten()
                        print(f"📊 最终嵌入向量长度: {len(embedding_array)}")
                        return embedding_array
                    else:
                        print(f"❌ 未知的嵌入向量格式: {type(embedding)}")
                        return None
                else:
                    print("❌ 结果中没有找到嵌入向量")
                    print(f"🔍 完整结果内容: {result[0]}")
                    return None
            else:
                print("❌ 模型返回空结果或结果为None")
                return None
            
        except Exception as e:
            print(f"❌ 提取说话人嵌入向量失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def register_speaker(self, speaker_name, audio_file_path, model_asr=None):
        """注册新的说话人"""
        try:
            print(f"🎯 注册说话人: {speaker_name}")
            print(f"📁 音频文件路径: {audio_file_path}")
            print(f"📊 文件是否存在: {os.path.exists(audio_file_path)}")
            
            if not os.path.exists(audio_file_path):
                return False, f"音频文件不存在: {audio_file_path}"
            
            # 加载音频文件
            print(f"🎵 开始加载音频文件...")
            audio_data, sample_rate = librosa.load(audio_file_path, sr=16000, dtype=np.float32)
            print(f"✅ 音频加载成功: 时长={len(audio_data)/sample_rate:.2f}秒, 采样率={sample_rate}Hz")
            
            # 检查音频长度（至少需要2秒）
            if len(audio_data) < 32000:  # 2秒 * 16000Hz
                return False, "音频长度太短，至少需要2秒"
            
            # 提取嵌入向量
            print(f"🔬 开始提取嵌入向量...")
            embedding = self.extract_speaker_embedding(audio_data, sample_rate, model_asr)
            
            if embedding is None:
                return False, "嵌入向量提取失败"
            
            print(f"✅ 嵌入向量提取成功: 维度={len(embedding)}")
            
            # 生成唯一ID
            speaker_id = hashlib.md5(f"{speaker_name}_{time.time()}".encode()).hexdigest()[:8]
            
            # 存储嵌入向量
            self.speaker_embeddings[speaker_id] = embedding
            
            # 存储元数据
            self.speaker_metadata[speaker_id] = {
                "name": speaker_name,
                "register_time": time.time(),
                "audio_file": os.path.basename(audio_file_path),
                "audio_duration": len(audio_data) / sample_rate,
                "embedding_dim": len(embedding)
            }
            
            # 保存到文件
            print(f"💾 保存数据到文件...")
            if self._save_embeddings() and self._save_metadata():
                print(f"✅ 说话人 {speaker_name} 注册成功 (ID: {speaker_id})")
                return True, f"注册成功，说话人ID: {speaker_id}"
            else:
                return False, "保存失败"
                
        except Exception as e:
            print(f"❌ 注册说话人失败: {e}")
            import traceback
            traceback.print_exc()
            return False, f"注册失败: {str(e)}"
    
    def match_speaker(self, audio_segment, model_asr=None):
        """匹配说话人"""
        try:
            if not self.speaker_embeddings:
                return None, 0.0, "数据库为空"
            
            # 提取当前音频段的嵌入向量
            embedding = self.extract_speaker_embedding(audio_segment, model_asr=model_asr)
            
            if embedding is None:
                return None, 0.0, "嵌入向量提取失败"
            
            best_match_id = None
            best_similarity = 0.0
            best_name = None
            
            # 与数据库中的每个说话人比较
            for speaker_id, ref_embedding in self.speaker_embeddings.items():
                try:
                    # 确保维度一致
                    min_dim = min(len(embedding), len(ref_embedding))
                    emb1 = embedding[:min_dim].reshape(1, -1)
                    emb2 = ref_embedding[:min_dim].reshape(1, -1)
                    
                    # 计算余弦相似度
                    similarity = cosine_similarity(emb1, emb2)[0, 0]
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match_id = speaker_id
                        best_name = self.speaker_metadata.get(speaker_id, {}).get("name", f"未知_{speaker_id}")
                        
                except Exception as e:
                    print(f"⚠️ 比较嵌入向量失败 {speaker_id}: {e}")
                    continue
            
            # 检查是否超过阈值
            if best_similarity >= self.similarity_threshold:
                return best_name, best_similarity, "匹配成功"
            else:
                return None, best_similarity, f"相似度过低 ({best_similarity:.3f} < {self.similarity_threshold})"
                
        except Exception as e:
            print(f"❌ 匹配说话人失败: {e}")
            return None, 0.0, f"匹配失败: {str(e)}"
    
    def get_registered_speakers(self):
        """获取已注册的说话人列表"""
        speakers = []
        for speaker_id, metadata in self.speaker_metadata.items():
            speakers.append({
                "id": speaker_id,
                "name": metadata.get("name", "未知"),
                "register_time": metadata.get("register_time", 0),
                "audio_duration": metadata.get("audio_duration", 0)
            })
        return speakers
    
    def delete_speaker(self, speaker_id):
        """删除说话人"""
        try:
            if speaker_id in self.speaker_embeddings:
                del self.speaker_embeddings[speaker_id]
            if speaker_id in self.speaker_metadata:
                name = self.speaker_metadata[speaker_id].get("name", "未知")
                del self.speaker_metadata[speaker_id]
                
                if self._save_embeddings() and self._save_metadata():
                    print(f"✅ 删除说话人 {name} 成功")
                    return True, f"删除成功"
                else:
                    return False, "保存失败"
            else:
                return False, "说话人不存在"
        except Exception as e:
            return False, f"删除失败: {str(e)}"
    
    def update_similarity_threshold(self, threshold):
        """更新相似度阈值"""
        if 0.0 <= threshold <= 1.0:
            self.similarity_threshold = threshold
            return True, f"阈值更新为 {threshold}"
        else:
            return False, "阈值必须在0-1之间" 