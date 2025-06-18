# 🎤 FunASR 语音识别工具使用指南

> 🎉 **恭喜！FunASR已经成功安装并运行！**

## 📋 项目简介

**FunASR** 是阿里巴巴达摩院开发的工业级语音识别工具包，支持：
- 🗣️ 中文/英文语音识别
- 🎯 实时流式识别
- 🔍 语音端点检测(VAD)
- 📝 标点符号恢复
- 👥 说话人识别
- 🎭 情感识别

## 🚀 快速开始

### 最简单的使用方法

```python
from funasr import AutoModel

# 加载中文语音识别模型
model = AutoModel(model="paraformer-zh", device="cpu")

# 识别音频文件
result = model.generate(input="your_audio.wav")
print(result[0]['text'])
```

### 命令行使用

```bash
# 基础识别
python3 quick_start.py your_audio.wav

# 完整功能识别 (包含VAD和标点)
funasr ++model=paraformer-zh ++vad_model="fsmn-vad" ++punc_model="ct-punc" ++input=your_audio.wav
```

## 🛠️ 完整功能演示

我们已经为你准备了完整的演示脚本：

```bash
# 运行完整功能演示
python3 funasr_demo.py

# 快速测试
python3 test_funasr.py

# 简单使用
python3 quick_start.py test_chinese.wav
```

## 🎯 常用功能示例

### 1. 基础语音识别
```python
from funasr import AutoModel

model = AutoModel(model="paraformer-zh", device="cpu")
result = model.generate(input="audio.wav")
```

### 2. 完整功能识别（VAD + ASR + 标点）
```python
model = AutoModel(
    model="paraformer-zh",      # 语音识别
    vad_model="fsmn-vad",       # 语音端点检测
    punc_model="ct-punc",       # 标点恢复
    device="cpu"
)

result = model.generate(
    input="audio.wav",
    hotword="人工智能,语音识别"  # 支持热词
)
```

### 3. 实时流式识别
```python
import soundfile
from funasr import AutoModel

# 加载流式模型
model = AutoModel(model="paraformer-zh-streaming")

# 读取音频
speech, sr = soundfile.read("audio.wav")
chunk_size = [0, 10, 5]  # 600ms延迟
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
    print(result[0]['text'])
```

### 4. 语音端点检测
```python
vad_model = AutoModel(model="fsmn-vad")
result = vad_model.generate(input="audio.wav")

# 输出格式：[[开始时间ms, 结束时间ms], ...]
for start, end in result[0]:
    print(f"语音片段: {start}ms - {end}ms")
```

## 🔧 支持的模型

| 模型 | 功能 | 语言 | 设备 |
|------|------|------|------|
| `paraformer-zh` | 中文语音识别 | 中文 | CPU/GPU |
| `paraformer-zh-streaming` | 中文实时识别 | 中文 | CPU/GPU |
| `paraformer-en` | 英文语音识别 | 英文 | CPU/GPU |
| `fsmn-vad` | 语音端点检测 | 通用 | CPU/GPU |
| `ct-punc` | 标点符号恢复 | 中英文 | CPU/GPU |
| `iic/SenseVoiceSmall` | 多语言识别 | 多语言 | CPU/GPU |

## ⚙️ 硬件要求

### CPU版本（推荐入门）
- **CPU**: 4核以上
- **内存**: 8GB以上
- **存储**: 10GB可用空间

### GPU版本（推荐生产）
- **GPU**: NVIDIA GTX 1060 6GB以上
- **显存**: 6GB以上
- **CUDA**: 11.0以上
- **性能**: RTF < 0.01 (比CPU快30倍以上)

## 📁 项目文件说明

```
FunASR/
├── test_funasr.py          # 测试脚本 - 验证安装
├── funasr_demo.py          # 完整演示 - 展示所有功能  
├── quick_start.py          # 快速开始 - 最简单使用
├── test_chinese.wav        # 中文测试音频
├── test_english.wav        # 英文测试音频
└── 我的FunASR使用指南.md   # 本文档
```

## 🎪 支持的音频格式

- **WAV** (推荐)
- **MP3** 
- **FLAC**
- **M4A**
- 其他常见音频格式

## 📊 性能参考

| 配置 | RTF | 处理速度 | 适用场景 |
|------|-----|----------|----------|
| CPU | 0.3+ | 1倍实时 | 开发测试 |
| GPU | 0.01 | 100倍实时 | 生产环境 |

> RTF (Real Time Factor): 处理1秒音频需要的时间

## 🛡️ 故障排除

### 常见问题

1. **模型下载慢**
   ```python
   # 设置国内镜像
   model = AutoModel(model="paraformer-zh", hub="ms")
   ```

2. **内存不足**
   ```python
   # 使用批处理
   result = model.generate(input="audio.wav", batch_size_s=60)
   ```

3. **GPU不可用**
   ```python
   # 强制使用CPU
   model = AutoModel(model="paraformer-zh", device="cpu")
   ```

### 获取帮助

- 📚 [官方文档](https://github.com/alibaba-damo-academy/FunASR)
- 🐛 [问题反馈](https://github.com/alibaba-damo-academy/FunASR/issues)
- 💬 [讨论区](https://github.com/alibaba-damo-academy/FunASR/discussions)

## 🎯 下一步计划

现在你可以：

1. **🎤 基础使用**: 用现有的音频文件测试识别效果
2. **🔄 实时应用**: 开发实时语音识别应用
3. **🛠️ 项目集成**: 将FunASR集成到你的项目中
4. **📈 性能优化**: 如果需要更好性能，考虑GPU部署

## 💡 使用技巧

- **选择合适的模型**: 实时用streaming，离线用标准版
- **合理配置参数**: 根据音频长度调整batch_size_s
- **使用热词功能**: 提高专业词汇识别准确率
- **组合多个模型**: VAD+ASR+标点获得最佳效果

---

### 🎉 恭喜完成FunASR配置！

**你现在拥有了一个完整的工业级语音识别系统！**

📞 如有任何问题，随时联系获取技术支持！

---
*最后更新: 2025年6月* 