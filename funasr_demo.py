#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunASR 完整功能演示脚本
展示语音识别、VAD、标点恢复等功能
"""

import os
import sys
import time
import urllib.request
from funasr import AutoModel

def print_banner():
    """打印欢迎横幅"""
    print("🎤" + "=" * 60 + "🎤")
    print("              🚀 FunASR 功能演示 🚀")
    print("         阿里巴巴达摩院语音识别工具包")
    print("🎤" + "=" * 60 + "🎤")

def download_demo_files():
    """下载演示音频文件"""
    print("\n📥 准备演示音频文件...")
    
    files = {
        "中文演示": {
            "url": "https://isv-data.oss-cn-hangzhou.aliyuncs.com/ics/MaaS/ASR/test_audio/vad_example.wav",
            "file": "demo_chinese.wav"
        },
        "英文演示": {
            "url": "https://isv-data.oss-cn-hangzhou.aliyuncs.com/ics/MaaS/ASR/test_audio/asr_example_en.wav", 
            "file": "demo_english.wav"
        }
    }
    
    downloaded_files = {}
    for name, info in files.items():
        if not os.path.exists(info["file"]):
            try:
                print(f"   正在下载 {name}: {info['file']}")
                urllib.request.urlretrieve(info["url"], info["file"])
                print(f"   ✅ {name} 下载完成")
            except Exception as e:
                print(f"   ❌ {name} 下载失败: {e}")
                continue
        else:
            print(f"   ✅ {name} 文件已存在")
        
        downloaded_files[name] = info["file"]
    
    return downloaded_files

def demo_basic_asr():
    """演示基础语音识别"""
    print("\n🎯 演示1: 基础中文语音识别")
    print("-" * 40)
    
    try:
        print("   加载Paraformer中文模型...")
        model = AutoModel(
            model="paraformer-zh",
            device="cpu"
        )
        
        files = download_demo_files()
        if "中文演示" in files:
            print(f"   正在识别音频文件: {files['中文演示']}")
            start_time = time.time()
            
            result = model.generate(input=files["中文演示"])
            
            end_time = time.time()
            
            print(f"   ⏱️  处理时间: {end_time - start_time:.2f} 秒")
            print(f"   📝 识别结果:")
            print(f"      文本: {result[0]['text'][:100]}...")
            print(f"      时间戳: 包含{len(result[0]['timestamp'])}个时间段")
            
    except Exception as e:
        print(f"   ❌ 演示失败: {e}")

def demo_vad_asr():
    """演示VAD + ASR组合功能"""
    print("\n🎯 演示2: VAD语音端点检测 + 语音识别")
    print("-" * 40)
    
    try:
        print("   加载组合模型 (VAD + ASR + 标点)...")
        model = AutoModel(
            model="paraformer-zh",      # 语音识别模型
            vad_model="fsmn-vad",       # 语音端点检测
            punc_model="ct-punc",       # 标点恢复
            device="cpu"
        )
        
        files = download_demo_files()
        if "中文演示" in files:
            print(f"   正在处理音频: {files['中文演示']}")
            start_time = time.time()
            
            result = model.generate(
                input=files["中文演示"],
                batch_size_s=300,           # 批处理大小
                hotword='语音识别,人工智能'   # 热词
            )
            
            end_time = time.time()
            
            print(f"   ⏱️  处理时间: {end_time - start_time:.2f} 秒")
            print(f"   📝 完整识别结果:")
            for i, res in enumerate(result):
                text = res['text']
                # 格式化输出，每60字符换行
                formatted_text = ""
                for j in range(0, len(text), 60):
                    formatted_text += "      " + text[j:j+60] + "\n"
                print(f"   结果 {i+1}:")
                print(formatted_text)
                
    except Exception as e:
        print(f"   ❌ 演示失败: {e}")

def demo_streaming_asr():
    """演示流式语音识别"""
    print("\n🎯 演示3: 流式实时语音识别")
    print("-" * 40)
    
    try:
        print("   加载流式识别模型...")
        model = AutoModel(model="paraformer-zh-streaming", device="cpu")
        
        files = download_demo_files()
        if "中文演示" in files:
            print(f"   模拟流式处理: {files['中文演示']}")
            
            import soundfile
            
            # 读取音频文件
            speech, sample_rate = soundfile.read(files["中文演示"])
            
            # 流式参数配置
            chunk_size = [0, 10, 5]  # 600ms 实时显示
            chunk_stride = chunk_size[1] * 960  # 采样点数
            
            cache = {}
            total_chunk_num = int(len(speech) / chunk_stride) + 1
            
            print(f"   音频总长度: {len(speech)/sample_rate:.2f} 秒")
            print(f"   分割成 {total_chunk_num} 个块进行流式处理")
            print("   🔄 开始流式识别:")
            
            for i in range(min(5, total_chunk_num)):  # 只演示前5个块
                speech_chunk = speech[i*chunk_stride:(i+1)*chunk_stride]
                is_final = i == total_chunk_num - 1
                
                result = model.generate(
                    input=speech_chunk, 
                    cache=cache, 
                    is_final=is_final,
                    chunk_size=chunk_size
                )
                
                if result and result[0]['text'].strip():
                    print(f"      块 {i+1}: {result[0]['text']}")
                
                time.sleep(0.1)  # 模拟实时延迟
            
            print("   ✅ 流式识别演示完成")
            
    except Exception as e:
        print(f"   ❌ 演示失败: {e}")

def demo_vad_only():
    """演示纯VAD功能"""
    print("\n🎯 演示4: 纯语音端点检测 (VAD)")
    print("-" * 40)
    
    try:
        print("   加载VAD模型...")
        vad_model = AutoModel(model="fsmn-vad", device="cpu")
        
        files = download_demo_files()
        if "中文演示" in files:
            print(f"   检测语音端点: {files['中文演示']}")
            
            result = vad_model.generate(input=files["中文演示"])
            
            print("   🎵 检测到的语音片段 (毫秒):")
            for i, (start, end) in enumerate(result[0]):
                duration = (end - start) / 1000
                print(f"      片段 {i+1}: {start}ms - {end}ms (时长: {duration:.2f}秒)")
                
                if i >= 10:  # 只显示前10个片段
                    print(f"      ... 还有 {len(result[0]) - i - 1} 个片段")
                    break
                    
    except Exception as e:
        print(f"   ❌ 演示失败: {e}")

def demo_command_line():
    """演示命令行使用方法"""
    print("\n🎯 演示5: 命令行使用方法")
    print("-" * 40)
    
    files = download_demo_files()
    if "中文演示" in files:
        cmd = f'funasr ++model=paraformer-zh ++vad_model="fsmn-vad" ++punc_model="ct-punc" ++input={files["中文演示"]}'
        print("   💻 命令行使用示例:")
        print(f"      {cmd}")
        print("\n   ⚡ 你可以直接在终端运行上面的命令！")

def show_usage_examples():
    """显示使用示例代码"""
    print("\n🎯 演示6: 常用代码示例")
    print("-" * 40)
    
    examples = [
        {
            "标题": "🔤 基础语音识别",
            "代码": '''from funasr import AutoModel

# 加载模型
model = AutoModel(model="paraformer-zh", device="cpu")

# 识别音频
result = model.generate(input="audio.wav")
print(result[0]['text'])'''
        },
        {
            "标题": "🎛️ 完整功能识别",
            "代码": '''from funasr import AutoModel

# 加载完整功能模型
model = AutoModel(
    model="paraformer-zh",      # 语音识别
    vad_model="fsmn-vad",       # 语音端点检测  
    punc_model="ct-punc",       # 标点恢复
    device="cpu"
)

# 识别音频 (支持热词)
result = model.generate(
    input="audio.wav",
    hotword="人工智能,语音识别"
)'''
        },
        {
            "标题": "🔄 流式识别",
            "代码": '''from funasr import AutoModel
import soundfile

# 加载流式模型
model = AutoModel(model="paraformer-zh-streaming")

# 读取音频
speech, sr = soundfile.read("audio.wav")
chunk_size = [0, 10, 5]  # 600ms
chunk_stride = chunk_size[1] * 960

cache = {}
for i in range(0, len(speech), chunk_stride):
    chunk = speech[i:i+chunk_stride]
    is_final = i + chunk_stride >= len(speech)
    
    result = model.generate(
        input=chunk, 
        cache=cache, 
        is_final=is_final,
        chunk_size=chunk_size
    )
    print(result[0]['text'])'''
        }
    ]
    
    for example in examples:
        print(f"\n   {example['标题']}:")
        for line in example['代码'].split('\n'):
            print(f"      {line}")

def main():
    """主演示函数"""
    print_banner()
    
    print(f"\n🖥️  系统信息:")
    print(f"      Python版本: {sys.version.split()[0]}")
    print(f"      工作目录: {os.getcwd()}")
    
    # 演示列表
    demos = [
        ("基础语音识别", demo_basic_asr),
        ("VAD + ASR + 标点", demo_vad_asr),
        ("流式识别", demo_streaming_asr),
        ("语音端点检测", demo_vad_only),
        ("命令行使用", demo_command_line),
        ("代码示例", show_usage_examples),
    ]
    
    print(f"\n🎪 开始功能演示 (共{len(demos)}个演示):")
    
    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
            print(f"\n   ✅ 演示 {i}/{len(demos)} 完成")
        except KeyboardInterrupt:
            print(f"\n   ⏹️  用户中断演示")
            break
        except Exception as e:
            print(f"\n   ❌ 演示 {i}/{len(demos)} 出错: {e}")
        
        if i < len(demos):
            print("\n" + "⋅" * 40)
    
    print("\n🎯 所有演示完成！")
    print("\n🎉 FunASR 已经完全配置好，你现在可以:")
    print("   1. 🎤 使用语音识别功能")
    print("   2. 🔄 开发实时语音应用")
    print("   3. 🛠️  集成到你的项目中")
    print("   4. 📚 查看更多文档：https://github.com/alibaba-damo-academy/FunASR")
    
    print(f"\n💝 感谢使用 FunASR! Happy Coding! 🚀")

if __name__ == "__main__":
    main() 