#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复CAM++说话人识别模型线程开销问题
直接修补funasr_upload_server.py中的相关代码
"""

import os
import re
import shutil
from datetime import datetime

def backup_file(file_path):
    """备份原文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ 已备份原文件到: {backup_path}")
    return backup_path

def fix_cam_plus_threading():
    """修复CAM++说话人识别模型的线程问题"""
    
    server_file = "runtime/python/websocket/funasr_upload_server.py"
    
    if not os.path.exists(server_file):
        print(f"❌ 文件不存在: {server_file}")
        return False
    
    # 备份原文件
    backup_file(server_file)
    
    # 读取文件内容
    with open(server_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复1: 在CAM++模型调用前设置线程限制
    cam_plus_fix = '''            print("🔧 调用FunASR CAM++说话人识别模型...")
            
            # 🔧 强制限制CAM++模型的线程数
            import os
            import torch
            
            # 保存原始设置
            original_omp_threads = os.environ.get('OMP_NUM_THREADS', '1')
            original_mkl_threads = os.environ.get('MKL_NUM_THREADS', '1')
            original_torch_threads = torch.get_num_threads()
            
            # 强制设置为单线程
            os.environ['OMP_NUM_THREADS'] = '1'
            os.environ['MKL_NUM_THREADS'] = '1'
            os.environ['OPENBLAS_NUM_THREADS'] = '1'
            os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
            os.environ['NUMEXPR_NUM_THREADS'] = '1'
            torch.set_num_threads(1)
            
            try:'''
    
    # 查找并替换CAM++模型调用
    pattern = r'(\s+)print\("🔧 调用FunASR CAM\+\+说话人识别模型\.\.\."\)'
    if re.search(pattern, content):
        content = re.sub(pattern, cam_plus_fix, content)
        print("✅ 已添加CAM++模型线程限制")
    else:
        print("⚠️ 未找到CAM++模型调用位置")
    
    # 修复2: 在CAM++模型调用后恢复线程设置
    restore_threads_code = '''                        print(f"✅ CAM++模型检测到{len(unique_spk_ids)}个说话人")
                        return enhanced_segments
                    else:
                        print(f"⚠️ CAM++模型只检测到1个说话人")
            
            finally:
                # 🔧 恢复原始线程设置
                os.environ['OMP_NUM_THREADS'] = original_omp_threads
                os.environ['MKL_NUM_THREADS'] = original_mkl_threads
                torch.set_num_threads(original_torch_threads)
                print("🔧 已恢复原始线程设置")'''
    
    # 查找并替换返回语句
    pattern2 = r'(\s+)print\(f"✅ CAM\+\+模型检测到\{len\(unique_spk_ids\)\}个说话人"\)\s+return enhanced_segments\s+else:\s+print\(f"⚠️ CAM\+\+模型只检测到1个说话人"\)'
    if re.search(pattern2, content):
        content = re.sub(pattern2, restore_threads_code, content)
        print("✅ 已添加线程设置恢复代码")
    else:
        print("⚠️ 未找到CAM++模型返回位置")
    
    # 修复3: 在独立说话人模型调用前也添加线程限制
    independent_model_fix = '''            print("🔧 尝试使用独立的说话人识别模型...")
            
            # 🔧 强制限制独立模型的线程数
            import os
            import torch
            
            # 保存原始设置
            original_omp_threads2 = os.environ.get('OMP_NUM_THREADS', '1')
            original_mkl_threads2 = os.environ.get('MKL_NUM_THREADS', '1')
            original_torch_threads2 = torch.get_num_threads()
            
            # 强制设置为单线程
            os.environ['OMP_NUM_THREADS'] = '1'
            os.environ['MKL_NUM_THREADS'] = '1'
            os.environ['OPENBLAS_NUM_THREADS'] = '1'
            os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
            os.environ['NUMEXPR_NUM_THREADS'] = '1'
            torch.set_num_threads(1)
            
            try:'''
    
    pattern3 = r'(\s+)print\("🔧 尝试使用独立的说话人识别模型\.\.\."\)'
    if re.search(pattern3, content):
        content = re.sub(pattern3, independent_model_fix, content)
        print("✅ 已添加独立模型线程限制")
    
    # 修复4: 在独立模型的AutoModel调用中添加线程参数
    automodel_fix = '''            # 加载专门的说话人识别模型
            spk_model = AutoModel(
                model="iic/speech_campplus_sv_zh-cn_16k-common",
                device="cpu",
                disable_pbar=True,
                disable_log=True,
                disable_update=True,  # 禁用自动更新检查
                # 🔧 强制单线程模式
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True
            )
            
            # 🔧 再次确保模型使用单线程
            torch.set_num_threads(1)'''
    
    pattern4 = r'(\s+)# 加载专门的说话人识别模型\s+spk_model = AutoModel\(\s+model="iic/speech_campplus_sv_zh-cn_16k-common",\s+device="cpu",\s+disable_pbar=True,\s+disable_log=True,\s+disable_update=True\s+# 禁用自动更新检查\s+\)'
    if re.search(pattern4, content):
        content = re.sub(pattern4, automodel_fix, content)
        print("✅ 已修复AutoModel调用")
    
    # 修复5: 在独立模型结束时恢复线程设置
    independent_restore = '''                        print(f"✅ 独立音色模型检测到{unique_labels}个说话人")
                        return enhanced_segments
                        
            finally:
                # 🔧 恢复原始线程设置
                os.environ['OMP_NUM_THREADS'] = original_omp_threads2
                os.environ['MKL_NUM_THREADS'] = original_mkl_threads2
                torch.set_num_threads(original_torch_threads2)
                print("🔧 已恢复独立模型线程设置")'''
    
    pattern5 = r'(\s+)print\(f"✅ 独立音色模型检测到\{unique_labels\}个说话人"\)\s+return enhanced_segments'
    if re.search(pattern5, content):
        content = re.sub(pattern5, independent_restore, content)
        print("✅ 已添加独立模型线程恢复")
    
    # 修复6: 在函数开始处设置全局线程限制
    function_start_fix = '''def detect_speakers_with_voice_print(audio_data, segments, sample_rate=16000):
    """使用专业音色模型进行说话人分离"""
    
    # 🔧 在函数开始就限制线程数
    import os
    import torch
    
    # 保存全局原始设置
    global_original_omp = os.environ.get('OMP_NUM_THREADS', '1')
    global_original_mkl = os.environ.get('MKL_NUM_THREADS', '1')
    global_original_torch = torch.get_num_threads()
    
    # 设置严格的单线程模式
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['MKL_NUM_THREADS'] = '1'
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
    os.environ['NUMEXPR_NUM_THREADS'] = '1'
    os.environ['BLIS_NUM_THREADS'] = '1'
    torch.set_num_threads(1)
    
    print("🔧 已设置说话人识别单线程模式")
    
    try:'''
    
    pattern6 = r'def detect_speakers_with_voice_print\(audio_data, segments, sample_rate=16000\):\s+"""使用专业音色模型进行说话人分离"""\s+try:'
    if re.search(pattern6, content):
        content = re.sub(pattern6, function_start_fix, content)
        print("✅ 已添加函数级别线程限制")
    
    # 修复7: 在函数结束时恢复全局设置
    function_end_fix = '''        # 回退到默认模式
        print("⚠️ 音色模型无法分离说话人，回退到单人模式")
        return detect_speakers_fallback(segments)
        
    finally:
        # 🔧 恢复全局线程设置
        os.environ['OMP_NUM_THREADS'] = global_original_omp
        os.environ['MKL_NUM_THREADS'] = global_original_mkl
        torch.set_num_threads(global_original_torch)
        print("🔧 已恢复全局线程设置")
        
    except Exception as e:
        # 🔧 异常情况下也要恢复线程设置
        try:
            os.environ['OMP_NUM_THREADS'] = global_original_omp
            os.environ['MKL_NUM_THREADS'] = global_original_mkl
            torch.set_num_threads(global_original_torch)
        except:
            pass
        print(f"⚠️ 说话人分离失败，回退到简单模式: {e}")
        return detect_speakers_fallback(segments)'''
    
    pattern7 = r'(\s+)# 回退到默认模式\s+print\("⚠️ 音色模型无法分离说话人，回退到单人模式"\)\s+return detect_speakers_fallback\(segments\)\s+except Exception as e:\s+print\(f"⚠️ 说话人分离失败，回退到简单模式: \{e\}"\)\s+return detect_speakers_fallback\(segments\)'
    if re.search(pattern7, content):
        content = re.sub(pattern7, function_end_fix, content)
        print("✅ 已添加函数结束线程恢复")
    
    # 写入修改后的内容
    with open(server_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 已修复CAM++说话人识别模型线程问题")
    return True

def add_startup_thread_control():
    """在服务器启动时添加线程控制"""
    
    server_file = "runtime/python/websocket/funasr_upload_server.py"
    
    with open(server_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在main函数开始处添加线程控制
    startup_fix = '''async def main():
    """主函数"""
    
    # 🔧 启动时设置严格的线程控制
    import os
    import torch
    
    print("🔧 设置启动线程控制...")
    
    # 设置环境变量
    thread_env = {
        'OMP_NUM_THREADS': '1',
        'MKL_NUM_THREADS': '1', 
        'OPENBLAS_NUM_THREADS': '1',
        'VECLIB_MAXIMUM_THREADS': '1',
        'NUMEXPR_NUM_THREADS': '1',
        'BLIS_NUM_THREADS': '1',
        'KMP_DUPLICATE_LIB_OK': 'TRUE'
    }
    
    for key, value in thread_env.items():
        os.environ[key] = value
        print(f"  {key} = {value}")
    
    # 设置PyTorch线程
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    
    print("✅ 启动线程控制设置完成")'''
    
    pattern = r'async def main\(\):\s+"""主函数"""'
    if re.search(pattern, content):
        content = re.sub(pattern, startup_fix, content)
        print("✅ 已添加启动线程控制")
        
        with open(server_file, 'w', encoding='utf-8') as f:
            f.write(content)

def main():
    """主函数"""
    print("🔧 开始修复CAM++说话人识别模型线程问题...")
    print("=" * 60)
    
    if fix_cam_plus_threading():
        add_startup_thread_control()
        print("=" * 60)
        print("✅ 修复完成！")
        print()
        print("📝 修复内容:")
        print("  1. 在CAM++模型调用前设置单线程模式")
        print("  2. 在模型调用后恢复线程设置")
        print("  3. 在独立说话人模型中也添加线程控制")
        print("  4. 在函数级别设置严格的线程限制")
        print("  5. 在服务器启动时设置全局线程控制")
        print()
        print("🚀 现在可以重启FunASR服务器，CAM++模型的线程问题应该已解决")
        print()
        print("⚠️  如果问题仍然存在，可以考虑:")
        print("  - 完全禁用说话人识别功能")
        print("  - 使用更轻量级的说话人识别算法")
        print("  - 增加系统内存和CPU资源")
    else:
        print("❌ 修复失败")

if __name__ == "__main__":
    main() 