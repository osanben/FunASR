#!/usr/bin/env python3
"""
测试FunASR模型缓存和disable_update功能
"""

import os
import sys
import time

def test_model_cache():
    """测试模型缓存状态"""
    print("🔍 检查FunASR模型缓存状态...")
    
    cache_dir = os.path.expanduser("~/.cache/modelscope/hub/models/iic")
    
    required_models = [
        "speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        "speech_fsmn_vad_zh-cn-16k-common-pytorch", 
        "punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        "speech_campplus_sv_zh-cn_16k-common"
    ]
    
    for model in required_models:
        model_path = os.path.join(cache_dir, model)
        if os.path.exists(model_path):
            files = os.listdir(model_path)
            model_files = [f for f in files if f.endswith(('.bin', '.pt', '.pth', '.onnx'))]
            print(f"✅ {model}: {len(files)} 文件, {len(model_files)} 模型文件")
        else:
            print(f"❌ {model}: 不存在")

def test_disable_update():
    """测试disable_update功能"""
    print("\n🧪 测试disable_update功能...")
    
    try:
        from funasr import AutoModel
        
        print("测试1: 使用disable_update=True")
        start_time = time.time()
        
        # 测试单个模型加载
        model = AutoModel(
            model="iic/speech_campplus_sv_zh-cn_16k-common",
            device="cpu",
            disable_update=True,
            disable_pbar=True,
            disable_log=True
        )
        
        end_time = time.time()
        print(f"✅ 单模型加载用时: {end_time - start_time:.2f}秒")
        
        # 清理
        del model
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_model_cache()
    test_disable_update() 