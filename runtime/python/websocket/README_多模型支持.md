# FunASR 多模型支持 WebSocket 服务器

这是一个支持多种ASR模型的WebSocket服务器，包括：
- **Whisper** (OpenAI开源，第一梯队)
- **Paraformer** (FunASR原生，中文优化)  
- **SenseVoice** (最新多任务模型)

## 🚀 快速开始

### 1. 安装依赖

```bash
# 基础依赖
pip install funasr websockets numpy

# Whisper支持 (可选，如果要使用Whisper)
pip install openai-whisper faster-whisper

# 或者安装所有依赖
pip install funasr websockets numpy openai-whisper faster-whisper
```

### 2. 启动不同模型的服务器

#### 🥇 使用Whisper (第一梯队，完全免费开源)
```bash
# Whisper Large V3 (最高准确率)
python funasr_wss_server_multi_model.py \
  --model_type whisper \
  --whisper_model large-v3 \
  --device cuda \
  --port 10095

# Whisper Medium (平衡性能和速度)
python funasr_wss_server_multi_model.py \
  --model_type whisper \
  --whisper_model medium \
  --device cuda \
  --port 10095

# CPU版本 (如果没有GPU)
python funasr_wss_server_multi_model.py \
  --model_type whisper \
  --whisper_model base \
  --device cpu \
  --port 10095
```

#### 🇨🇳 使用Paraformer (中文优化)
```bash
python funasr_wss_server_multi_model.py \
  --model_type paraformer \
  --device cuda \
  --port 10095
```

#### 🆕 使用SenseVoice (最新模型)
```bash
python funasr_wss_server_multi_model.py \
  --model_type sensevoice \
  --device cuda \
  --port 10095
```

## 📊 模型对比

| 模型 | 开源 | 免费 | 中文准确率 | 英文准确率 | 多语言 | 模型大小 |
|------|------|------|------------|------------|--------|----------|
| **Whisper Large V3** | ✅ | ✅ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | 1.55GB |
| **Whisper Medium** | ✅ | ✅ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | 769MB |
| **Paraformer** | ✅ | ✅ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | 870MB |
| **SenseVoice** | ✅ | ✅ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | 234MB |

## 🎯 推荐使用场景

### 🏆 追求最高准确率
```bash
# 使用Whisper Large V3
python funasr_wss_server_multi_model.py --model_type whisper --whisper_model large-v3
```

### 🇨🇳 中文语音为主
```bash
# 使用Paraformer (专门为中文优化)
python funasr_wss_server_multi_model.py --model_type paraformer
```

### ⚡ 平衡性能和速度
```bash
# 使用SenseVoice (最新，多任务)
python funasr_wss_server_multi_model.py --model_type sensevoice
```

### 💻 资源受限环境
```bash
# 使用Whisper Base (CPU友好)
python funasr_wss_server_multi_model.py --model_type whisper --whisper_model base --device cpu
```

## 🔧 高级配置

### 完整参数示例
```bash
python funasr_wss_server_multi_model.py \
  --model_type whisper \
  --whisper_model large-v3 \
  --vad_model "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch" \
  --punc_model "iic/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727" \
  --spk_model "iic/speech_campplus_sv_zh-cn_16k-common" \
  --device cuda \
  --host 0.0.0.0 \
  --port 10095
```

### 参数说明
- `--model_type`: 选择ASR模型 (whisper/paraformer/sensevoice)
- `--whisper_model`: Whisper模型大小 (tiny/base/small/medium/large/large-v3)
- `--device`: 计算设备 (cuda/cpu)
- `--vad_model`: 语音活动检测模型
- `--punc_model`: 标点符号恢复模型
- `--spk_model`: 说话人识别模型

## 🌐 前端集成

前端代码不需要修改，服务器会自动处理不同模型的输出格式。

WebSocket地址保持不变：`ws://127.0.0.1:10095/`

## 📈 性能对比测试

你可以同时启动多个服务器进行对比测试：

```bash
# 终端1: Whisper服务器
python funasr_wss_server_multi_model.py --model_type whisper --port 10095

# 终端2: Paraformer服务器  
python funasr_wss_server_multi_model.py --model_type paraformer --port 10096

# 终端3: SenseVoice服务器
python funasr_wss_server_multi_model.py --model_type sensevoice --port 10097
```

然后修改前端WebSocket地址进行对比测试。

## 💡 优化建议

### 1. 硬件优化
- **GPU**: 推荐使用NVIDIA GPU，显存至少8GB
- **CPU**: 如果使用CPU，推荐至少8核心
- **内存**: 推荐至少16GB RAM

### 2. 模型选择建议
- **追求准确率**: Whisper Large V3
- **中文专用**: Paraformer  
- **多语言**: SenseVoice
- **资源受限**: Whisper Base

### 3. 性能调优
```bash
# GPU内存优化
export CUDA_VISIBLE_DEVICES=0

# 并发处理优化
--ncpu 8  # 根据CPU核心数调整
```

## 🐛 故障排除

### 常见问题

1. **Whisper安装失败**
```bash
# 使用清华源安装
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple openai-whisper faster-whisper
```

2. **GPU内存不足**
```bash
# 使用较小的模型
--whisper_model medium  # 或 small, base
```

3. **模型下载慢**
```bash
# 设置ModelScope镜像
export MODELSCOPE_CACHE=~/.cache/modelscope
```

## 📞 技术支持

如果遇到问题，请检查：
1. 依赖是否正确安装
2. GPU驱动是否正常
3. 网络连接是否稳定
4. 模型文件是否完整下载

## 🎉 总结

现在你有了一个支持多种ASR模型的强大系统：

- ✅ **Whisper**: 第一梯队，完全免费开源
- ✅ **Paraformer**: 中文优化，工业级部署
- ✅ **SenseVoice**: 最新技术，多任务能力

根据你的具体需求选择最适合的模型！ 