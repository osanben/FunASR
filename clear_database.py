#!/usr/bin/env python3
"""
FunASR 数据库清理工具
支持选择性清理不同类型的测试数据
"""
import os
import sys
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

class FunASRDataCleaner:
    """FunASR数据清理器"""
    
    def __init__(self, db_path="funasr_data.db"):
        self.db_path = db_path
        self.backup_dir = Path("./database_backups")
        self.backup_dir.mkdir(exist_ok=True)
    
    def backup_database(self):
        """备份数据库"""
        if not os.path.exists(self.db_path):
            print(f"⚠️ 数据库文件不存在: {self.db_path}")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"funasr_backup_{timestamp}.db"
        
        try:
            shutil.copy2(self.db_path, backup_file)
            print(f"✅ 数据库已备份至: {backup_file}")
            return backup_file
        except Exception as e:
            print(f"❌ 备份失败: {e}")
            return None
    
    def get_database_stats(self):
        """获取数据库统计信息"""
        if not os.path.exists(self.db_path):
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # 转录历史
                cursor.execute("SELECT COUNT(*) FROM transcription_history")
                stats['transcription_history'] = cursor.fetchone()[0]
                
                # 说话人
                cursor.execute("SELECT COUNT(*) FROM speakers")
                stats['speakers'] = cursor.fetchone()[0]
                
                # 音频片段
                cursor.execute("SELECT COUNT(*) FROM audio_segments")
                stats['audio_segments'] = cursor.fetchone()[0]
                
                # 批处理任务
                cursor.execute("SELECT COUNT(*) FROM batch_tasks")
                stats['batch_tasks'] = cursor.fetchone()[0]
                
                # 性能报告
                cursor.execute("SELECT COUNT(*) FROM performance_reports")
                stats['performance_reports'] = cursor.fetchone()[0]
                
                # 系统负载监控
                cursor.execute("SELECT COUNT(*) FROM system_load_monitor")
                stats['system_load_monitor'] = cursor.fetchone()[0]
                
                # 系统统计
                cursor.execute("SELECT COUNT(*) FROM system_stats")
                stats['system_stats'] = cursor.fetchone()[0]
                
                return stats
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
            return None
    
    def clear_transcription_data(self):
        """清空转录相关数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 清空转录历史
                cursor.execute("DELETE FROM transcription_history")
                deleted_transcriptions = cursor.rowcount
                
                # 清空音频片段
                cursor.execute("DELETE FROM audio_segments")
                deleted_segments = cursor.rowcount
                
                # 清空批处理任务
                cursor.execute("DELETE FROM batch_tasks")
                deleted_batches = cursor.rowcount
                
                conn.commit()
                
                print(f"✅ 已清空转录数据:")
                print(f"   - 转录记录: {deleted_transcriptions} 条")
                print(f"   - 音频片段: {deleted_segments} 条")
                print(f"   - 批处理任务: {deleted_batches} 条")
                
                return True
        except Exception as e:
            print(f"❌ 清空转录数据失败: {e}")
            return False
    
    def clear_speaker_data(self):
        """清空说话人数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 清空说话人表
                cursor.execute("DELETE FROM speakers")
                deleted_speakers = cursor.rowcount
                
                conn.commit()
                
                print(f"✅ 已清空说话人数据: {deleted_speakers} 条")
                
                # 清空说话人数据库文件
                speaker_db_dir = Path("./speaker_database")
                if speaker_db_dir.exists():
                    shutil.rmtree(speaker_db_dir)
                    print("✅ 已清空说话人声纹数据库")
                
                return True
        except Exception as e:
            print(f"❌ 清空说话人数据失败: {e}")
            return False
    
    def clear_performance_data(self):
        """清空性能监控数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 清空性能报告
                cursor.execute("DELETE FROM performance_reports")
                deleted_reports = cursor.rowcount
                
                # 清空系统负载监控
                cursor.execute("DELETE FROM system_load_monitor")
                deleted_loads = cursor.rowcount
                
                # 清空系统统计
                cursor.execute("DELETE FROM system_stats")
                deleted_stats = cursor.rowcount
                
                conn.commit()
                
                print(f"✅ 已清空性能数据:")
                print(f"   - 性能报告: {deleted_reports} 条")
                print(f"   - 系统负载: {deleted_loads} 条")
                print(f"   - 系统统计: {deleted_stats} 条")
                
                return True
        except Exception as e:
            print(f"❌ 清空性能数据失败: {e}")
            return False
    
    def clear_audio_files(self):
        """清空音频文件"""
        try:
            deleted_count = 0
            
            # 清空上传目录
            uploads_dir = Path("./uploads")
            if uploads_dir.exists():
                for file in uploads_dir.iterdir():
                    if file.is_file():
                        file.unlink()
                        deleted_count += 1
                print(f"✅ 已清空上传文件: {deleted_count} 个")
            
            # 清空音频片段目录
            segments_dir = Path("./audio_segments")
            if segments_dir.exists():
                shutil.rmtree(segments_dir)
                print("✅ 已清空音频片段文件")
            
            return True
        except Exception as e:
            print(f"❌ 清空音频文件失败: {e}")
            return False
    
    def clear_all_data(self):
        """清空所有数据"""
        print("🗑️ 开始清空所有数据...")
        
        success = True
        success &= self.clear_transcription_data()
        success &= self.clear_speaker_data()
        success &= self.clear_performance_data()
        success &= self.clear_audio_files()
        
        if success:
            print("🎉 所有数据清空完成!")
        else:
            print("⚠️ 部分数据清空失败")
        
        return success
    
    def reset_database(self):
        """重置数据库（删除并重新创建）"""
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                print(f"✅ 已删除数据库文件: {self.db_path}")
            
            # 重新初始化数据库
            from runtime.python.websocket.database import FunASRDatabase
            db = FunASRDatabase(self.db_path)
            print("✅ 数据库已重新初始化")
            
            return True
        except Exception as e:
            print(f"❌ 重置数据库失败: {e}")
            return False

def show_menu():
    """显示菜单"""
    print("\n" + "="*50)
    print("🗄️  FunASR 数据库清理工具")
    print("="*50)
    print("1. 查看数据库统计")
    print("2. 清空转录数据 (转录记录、音频片段、批处理)")
    print("3. 清空说话人数据 (说话人信息、声纹数据)")
    print("4. 清空性能数据 (性能报告、系统监控)")
    print("5. 清空音频文件 (上传文件、片段文件)")
    print("6. 清空所有数据")
    print("7. 重置数据库 (删除并重新创建)")
    print("8. 备份数据库")
    print("0. 退出")
    print("="*50)

def main():
    """主函数"""
    cleaner = FunASRDataCleaner()
    
    while True:
        show_menu()
        
        try:
            choice = input("请选择操作 (0-8): ").strip()
            
            if choice == "0":
                print("👋 再见!")
                break
            
            elif choice == "1":
                print("\n📊 数据库统计信息:")
                stats = cleaner.get_database_stats()
                if stats:
                    for table, count in stats.items():
                        print(f"   {table}: {count} 条记录")
                else:
                    print("❌ 无法获取统计信息")
            
            elif choice == "2":
                confirm = input("⚠️ 确认清空转录数据? (y/N): ").strip().lower()
                if confirm == 'y':
                    cleaner.clear_transcription_data()
            
            elif choice == "3":
                confirm = input("⚠️ 确认清空说话人数据? (y/N): ").strip().lower()
                if confirm == 'y':
                    cleaner.clear_speaker_data()
            
            elif choice == "4":
                confirm = input("⚠️ 确认清空性能数据? (y/N): ").strip().lower()
                if confirm == 'y':
                    cleaner.clear_performance_data()
            
            elif choice == "5":
                confirm = input("⚠️ 确认清空音频文件? (y/N): ").strip().lower()
                if confirm == 'y':
                    cleaner.clear_audio_files()
            
            elif choice == "6":
                confirm = input("⚠️ 确认清空所有数据? 这将删除所有测试数据! (y/N): ").strip().lower()
                if confirm == 'y':
                    # 先备份
                    backup_file = cleaner.backup_database()
                    if backup_file:
                        cleaner.clear_all_data()
            
            elif choice == "7":
                confirm = input("⚠️ 确认重置数据库? 这将完全删除数据库! (y/N): ").strip().lower()
                if confirm == 'y':
                    # 先备份
                    backup_file = cleaner.backup_database()
                    if backup_file:
                        cleaner.reset_database()
            
            elif choice == "8":
                cleaner.backup_database()
            
            else:
                print("❌ 无效选择，请重新输入")
        
        except KeyboardInterrupt:
            print("\n👋 用户取消操作")
            break
        except Exception as e:
            print(f"❌ 操作失败: {e}")

if __name__ == "__main__":
    main() 