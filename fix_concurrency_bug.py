#!/usr/bin/env python3
"""
修复FunASR并发控制器BUG的脚本
"""
import os
import sys
import re

def fix_concurrency_bug():
    """
    修复process_audio_file函数中缺少finish_task()调用的问题
    """
    server_file = "runtime/python/websocket/funasr_upload_server.py"
    
    if not os.path.exists(server_file):
        print(f"❌ 找不到服务端文件: {server_file}")
        return False
    
    print("🔧 修复并发控制器BUG...")
    
    # 读取原文件
    with open(server_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 备份原文件
    backup_file = server_file + ".backup_concurrency"
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"📄 原文件备份至: {backup_file}")
    
    # 修复1: 在process_audio_file函数末尾添加finish_task调用
    pattern1 = r'(def process_audio_file\(file_path, task_id, model_type\):.*?)(    except Exception as e:.*?print\(f"❌ 处理任务.*?错误: \{e\}"\).*?)(    finally:.*?# 清理临时文件.*?pass.*?)(    # 减少并发任务计数.*?system_monitor\.decrement_concurrent_tasks\(\))'
    
    if re.search(pattern1, content, re.DOTALL):
        # 如果已经有finally块，在其中添加finish_task
        replacement1 = r'\1\2\3\4\n        # 完成并发控制器任务\n        concurrency_controller.finish_task(processing_time)'
        content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)
        print("✅ 在现有finally块中添加finish_task调用")
    else:
        # 如果没有finally块，查找函数结尾并添加
        pattern2 = r'(def process_audio_file\(file_path, task_id, model_type\):.*?)(    except Exception as e:.*?print\(f"❌ 处理任务.*?错误: \{e\}"\).*?)(    # 减少并发任务计数.*?system_monitor\.decrement_concurrent_tasks\(\))'
        
        if re.search(pattern2, content, re.DOTALL):
            replacement2 = r'\1\2\3\n    finally:\n        # 完成并发控制器任务\n        processing_time = time.time() - processing_start_time\n        concurrency_controller.finish_task(processing_time)'
            content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
            print("✅ 添加finally块和finish_task调用")
        else:
            print("❌ 未找到process_audio_file函数的适当位置")
            return False
    
    # 修复2: 确保在异常情况下也调用finish_task
    pattern3 = r'(    except Exception as e:.*?print\(f"❌ 处理任务.*?错误: \{e\}"\).*?)(    # 减少并发任务计数.*?system_monitor\.decrement_concurrent_tasks\(\))'
    
    if re.search(pattern3, content, re.DOTALL):
        replacement3 = r'\1\2\n        # 异常情况下也要完成并发控制器任务\n        concurrency_controller.finish_task()'
        content = re.sub(pattern3, replacement3, content, flags=re.DOTALL)
        print("✅ 在异常处理中添加finish_task调用")
    
    # 修复3: 强制重置并发控制器状态的函数
    reset_function = '''
def reset_concurrency_controller():
    """重置并发控制器状态"""
    global concurrency_controller
    if concurrency_controller:
        with concurrency_controller.lock:
            print(f"🔄 重置并发控制器: {concurrency_controller.current_tasks} -> 0")
            concurrency_controller.current_tasks = 0
            print("✅ 并发控制器状态已重置")

# 在服务启动时重置状态
reset_concurrency_controller()
'''
    
    # 在main函数之前插入重置函数
    pattern4 = r'(async def main\(\):)'
    if re.search(pattern4, content):
        content = re.sub(pattern4, reset_function + r'\n\1', content)
        print("✅ 添加并发控制器重置函数")
    
    # 写入修改后的文件
    with open(server_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 并发控制器BUG修复完成!")
    return True

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "fix":
        success = fix_concurrency_bug()
        if success:
            print("\n🎉 修复完成! 请重启FunASR服务。")
            print("💡 建议使用: ./emergency_fix.sh")
        else:
            print("\n❌ 修复失败!")
    else:
        print("用法: python fix_concurrency_bug.py fix")

if __name__ == "__main__":
    main() 