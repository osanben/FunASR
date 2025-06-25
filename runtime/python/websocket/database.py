#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path
import threading

class FunASRDatabase:
    """FunASR数据库管理器"""
    
    def __init__(self, db_path="funasr_data.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 转录历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transcription_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    file_size INTEGER,
                    duration REAL,
                    model_type TEXT,
                    status TEXT DEFAULT 'pending',
                    transcription_text TEXT,
                    segments_data TEXT,  -- JSON格式存储分段数据
                    speaker_results TEXT,  -- JSON格式存储说话人识别结果
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    processing_time REAL,
                    error_message TEXT
                )
            ''')
            
            # 说话人信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS speakers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    speaker_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    audio_file_path TEXT,
                    embedding_data TEXT,  -- JSON格式存储嵌入向量
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0
                )
            ''')
            
            # 音频片段表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audio_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    segment_index INTEGER NOT NULL,
                    start_time REAL,
                    end_time REAL,
                    text TEXT,
                    speaker_id TEXT,
                    speaker_name TEXT,
                    confidence REAL,
                    similarity_score REAL,
                    audio_file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES transcription_history (task_id)
                )
            ''')
            
            # 批处理任务表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS batch_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT UNIQUE NOT NULL,
                    name TEXT,
                    total_files INTEGER DEFAULT 0,
                    completed_files INTEGER DEFAULT 0,
                    failed_files INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            ''')
            
            # 系统统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    total_transcriptions INTEGER DEFAULT 0,
                    total_duration REAL DEFAULT 0,
                    total_speakers INTEGER DEFAULT 0,
                    avg_processing_time REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def add_transcription_task(self, task_id, filename, file_size=None, model_type=None):
        """添加转录任务"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO transcription_history 
                    (task_id, filename, file_size, model_type, status, created_at)
                    VALUES (?, ?, ?, ?, 'pending', ?)
                ''', (task_id, filename, file_size, model_type, datetime.now()))
                conn.commit()
    
    def update_transcription_result(self, task_id, transcription_text, segments_data=None, 
                                  speaker_results=None, duration=None, processing_time=None, 
                                  status='completed', error_message=None):
        """更新转录结果"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE transcription_history 
                    SET transcription_text = ?, segments_data = ?, speaker_results = ?,
                        duration = ?, processing_time = ?, status = ?, completed_at = ?,
                        error_message = ?
                    WHERE task_id = ?
                ''', (
                    transcription_text,
                    json.dumps(segments_data) if segments_data else None,
                    json.dumps(speaker_results) if speaker_results else None,
                    duration, processing_time, status, datetime.now(), error_message, task_id
                ))
                conn.commit()
    
    def get_transcription_history(self, limit=100, offset=0, status=None):
        """获取转录历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            where_clause = ""
            params = []
            if status:
                where_clause = "WHERE status = ?"
                params.append(status)
            
            cursor.execute(f'''
                SELECT * FROM transcription_history 
                {where_clause}
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', params + [limit, offset])
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                # 解析JSON字段
                if result['segments_data']:
                    result['segments_data'] = json.loads(result['segments_data'])
                if result['speaker_results']:
                    result['speaker_results'] = json.loads(result['speaker_results'])
                results.append(result)
            
            return results
    
    def get_transcription_by_id(self, task_id):
        """根据ID获取转录记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM transcription_history WHERE task_id = ?', (task_id,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                result = dict(zip(columns, row))
                # 解析JSON字段
                if result['segments_data']:
                    result['segments_data'] = json.loads(result['segments_data'])
                if result['speaker_results']:
                    result['speaker_results'] = json.loads(result['speaker_results'])
                return result
            return None
    
    def add_speaker(self, speaker_id, name, audio_file_path=None, embedding_data=None):
        """添加说话人"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO speakers 
                    (speaker_id, name, audio_file_path, embedding_data, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    speaker_id, name, audio_file_path,
                    json.dumps(embedding_data.tolist()) if embedding_data is not None else None,
                    datetime.now()
                ))
                conn.commit()
    
    def get_speakers(self):
        """获取所有说话人"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM speakers ORDER BY created_at DESC')
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                # 解析嵌入向量
                if result['embedding_data']:
                    result['embedding_data'] = json.loads(result['embedding_data'])
                results.append(result)
            return results
    
    def delete_speaker(self, speaker_id):
        """删除说话人"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM speakers WHERE speaker_id = ?', (speaker_id,))
                conn.commit()
                return cursor.rowcount > 0
    
    def add_audio_segment(self, task_id, segment_index, start_time, end_time, text, 
                         speaker_id=None, speaker_name=None, confidence=None, 
                         similarity_score=None, audio_file_path=None):
        """添加音频片段"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO audio_segments 
                    (task_id, segment_index, start_time, end_time, text, speaker_id, 
                     speaker_name, confidence, similarity_score, audio_file_path, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_id, segment_index, start_time, end_time, text, speaker_id,
                    speaker_name, confidence, similarity_score, audio_file_path, datetime.now()
                ))
                conn.commit()
    
    def get_segments_by_task(self, task_id):
        """获取任务的所有音频片段"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM audio_segments 
                WHERE task_id = ? 
                ORDER BY segment_index
            ''', (task_id,))
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def create_batch_task(self, batch_id, name, total_files):
        """创建批处理任务"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO batch_tasks (batch_id, name, total_files, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (batch_id, name, total_files, datetime.now()))
                conn.commit()
    
    def update_batch_progress(self, batch_id, completed_files=None, failed_files=None, status=None):
        """更新批处理进度"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                if completed_files is not None:
                    updates.append("completed_files = ?")
                    params.append(completed_files)
                if failed_files is not None:
                    updates.append("failed_files = ?")
                    params.append(failed_files)
                if status is not None:
                    updates.append("status = ?")
                    params.append(status)
                    if status == 'completed':
                        updates.append("completed_at = ?")
                        params.append(datetime.now())
                
                if updates:
                    params.append(batch_id)
                    cursor.execute(f'''
                        UPDATE batch_tasks 
                        SET {", ".join(updates)}
                        WHERE batch_id = ?
                    ''', params)
                    conn.commit()
    
    def get_batch_tasks(self, limit=50):
        """获取批处理任务列表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM batch_tasks 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_statistics(self):
        """获取系统统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 总转录次数
            cursor.execute("SELECT COUNT(*) FROM transcription_history WHERE status = 'completed'")
            total_transcriptions = cursor.fetchone()[0]
            
            # 总时长
            cursor.execute("SELECT SUM(duration) FROM transcription_history WHERE status = 'completed'")
            total_duration = cursor.fetchone()[0] or 0
            
            # 说话人数量
            cursor.execute("SELECT COUNT(*) FROM speakers")
            total_speakers = cursor.fetchone()[0]
            
            # 平均处理时间
            cursor.execute("SELECT AVG(processing_time) FROM transcription_history WHERE status = 'completed'")
            avg_processing_time = cursor.fetchone()[0] or 0
            
            # 今日转录次数
            cursor.execute('''
                SELECT COUNT(*) FROM transcription_history 
                WHERE DATE(created_at) = DATE('now') AND status = 'completed'
            ''')
            today_transcriptions = cursor.fetchone()[0]
            
            return {
                'total_transcriptions': total_transcriptions,
                'total_duration': total_duration,
                'total_speakers': total_speakers,
                'avg_processing_time': avg_processing_time,
                'today_transcriptions': today_transcriptions
            }
    
    def cleanup_old_data(self, days=30):
        """清理旧数据"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM transcription_history 
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days))
                cursor.execute('''
                    DELETE FROM audio_segments 
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days))
                conn.commit() 