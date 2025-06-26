#!/usr/bin/env python3
"""
FunASR 快速数据清理脚本
支持命令行参数快速清理不同类型的数据
"""
import os
import sys
import argparse
from clear_database import FunASRDataCleaner

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="FunASR 快速数据清理工具")
    
    parser.add_argument("--all", action="store_true", help="清空所有数据")
    parser.add_argument("--transcription", action="store_true", help="清空转录数据")
    parser.add_argument("--speaker", action="store_true", help="清空说话人数据")
    parser.add_argument("--performance", action="store_true", help="清空性能数据")
    parser.add_argument("--audio", action="store_true", help="清空音频文件")
    parser.add_argument("--reset", action="store_true", help="重置数据库")
    parser.add_argument("--backup", action="store_true", help="备份数据库")
    parser.add_argument("--stats", action="store_true", help="显示数据库统计")
    parser.add_argument("--force", action="store_true", help="强制执行，不询问确认")
    parser.add_argument("--db", default="funasr_data.db", help="数据库文件路径")
    
    args = parser.parse_args()
    
    # 如果没有参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    cleaner = FunASRDataCleaner(args.db)
    
    # 显示统计信息
    if args.stats:
        print("📊 数据库统计信息:")
        stats = cleaner.get_database_stats()
        if stats:
            for table, count in stats.items():
                print(f"   {table}: {count} 条记录")
        else:
            print("❌ 无法获取统计信息")
        return
    
    # 备份数据库
    if args.backup:
        cleaner.backup_database()
        return
    
    # 确认操作
    if not args.force:
        operations = []
        if args.all:
            operations.append("所有数据")
        if args.transcription:
            operations.append("转录数据")
        if args.speaker:
            operations.append("说话人数据")
        if args.performance:
            operations.append("性能数据")
        if args.audio:
            operations.append("音频文件")
        if args.reset:
            operations.append("重置数据库")
        
        if operations:
            print(f"⚠️ 将要清理: {', '.join(operations)}")
            confirm = input("确认继续? (y/N): ").strip().lower()
            if confirm != 'y':
                print("❌ 操作已取消")
                return
    
    # 先备份（除非是查看统计）
    if not args.stats:
        print("🔄 自动备份数据库...")
        cleaner.backup_database()
    
    # 执行清理操作
    if args.all:
        cleaner.clear_all_data()
    else:
        if args.transcription:
            cleaner.clear_transcription_data()
        if args.speaker:
            cleaner.clear_speaker_data()
        if args.performance:
            cleaner.clear_performance_data()
        if args.audio:
            cleaner.clear_audio_files()
        if args.reset:
            cleaner.reset_database()

if __name__ == "__main__":
    main() 