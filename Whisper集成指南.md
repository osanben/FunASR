# 🎯 FunASR + Whisper 集成指南

## 🌟 概述

我已经为你成功集成了Whisper模型到FunASR项目中！现在你可以使用：

- **Whisper** - OpenAI开源，第一梯队模型，完全免费
- **Paraformer** - FunASR原生模型，中文优化
- **SenseVoice** - 最新多任务模型
- **Hybrid模式** - 同时使用多个模型进行对比

## 🚀 快速开始

### 1. 启动Whisper服务器 (推荐)

```bash
# 使用Whisper Large-V3 (第一梯队，最高准确率)
./start_whisper_server.sh whisper large-v3 10095 cuda

# 或者使用Medium模型 (平衡性能和速度)
./start_whisper_server.sh whisper medium 10095 cuda

# CPU版本 (如果没有GPU)
./start_whisper_server.sh whisper large-v3 10095 cpu
```

### 2. 启动Paraformer服务器 (原有模型)

```bash
./start_whisper_server.sh paraformer "" 10096 cuda
```

### 3. 启动混合模式 (同时对比两个模型)

```bash
./start_whisper_server.sh hybrid large-v3 10097 cuda
```

## 📊 模型对比

| 模型 | 参数量 | 优势 | 适用场景 |
|------|--------|------|----------|
| **Whisper Large-V3** | 1550M | 🥇第一梯队，多语言，免费开源 | 高质量转录，多语言场景 |
| **Whisper Medium** | 769M | 🚀平衡性能和速度 | 日常使用，实时性要求 |
| **Paraformer** | 220M | 🇨🇳中文优化，说话人识别 | 中文专业场景 |
| **SenseVoice** | 234M | 🎯多任务，情感识别 | 智能客服，情感分析 |

## 🛠️ 详细配置

### Whisper模型大小选择

```bash
# 最快 (39M参数)
./start_whisper_server.sh whisper tiny 10095 cuda

# 平衡 (244M参数) 
./start_whisper_server.sh whisper small 10095 cuda

# 高质量 (1550M参数，推荐)
./start_whisper_server.sh whisper large-v3 10095 cuda
```

### 设备选择

```bash
# CUDA GPU (推荐)
./start_whisper_server.sh whisper large-v3 10095 cuda

# Apple Silicon MPS
./start_whisper_server.sh whisper large-v3 10095 mps

# CPU (较慢但兼容性好)
./start_whisper_server.sh whisper large-v3 10095 cpu
```

### 端口配置

```bash
# 默认端口 10095
./start_whisper_server.sh whisper large-v3

# 自定义端口
./start_whisper_server.sh whisper large-v3 8080 cuda
```

## 🔧 前端配置

### 修改前端WebSocket地址

如果你使用不同端口，需要修改前端的WebSocket地址：

1. 编辑 `runtime/html5/static/index.html`
2. 修改WebSocket地址为对应端口：
   ```html
   <input id="wssip" type="text" value="ws://127.0.0.1:10095/"/>
   ```

### 多模型对比

在混合模式下，前端会同时显示多个模型的识别结果，格式如下：

```json
{
  "model": "whisper-large-v3",
  "text": "识别的文本内容",
  "timestamp": "[0.00->2.50] 识别的文本内容",
  "language": "zh",
  "is_final": true
}
```

## 📈 性能优化建议

### 1. 模型选择建议

- **高准确率场景**: 使用 `whisper large-v3`
- **实时性要求**: 使用 `whisper medium` 或 `paraformer`
- **中文专业场景**: 使用 `paraformer` 或 `hybrid`
- **多语言场景**: 使用 `whisper` 系列

### 2. 硬件配置建议

- **GPU内存**: Whisper Large需要约6GB显存
- **CPU**: 多核心CPU可提升处理速度
- **内存**: 建议16GB以上

### 3. 网络优化

```bash
# 调整WebSocket缓冲区大小
export WEBSOCKET_MAX_SIZE=10485760  # 10MB
```

## 🔍 故障排除

### 1. Whisper模型下载失败

```bash
# 手动下载模型
python3 -c "import whisper; whisper.load_model('large-v3')"
```

### 2. CUDA内存不足

```bash
# 使用较小的模型
./start_whisper_server.sh whisper medium 10095 cuda

# 或使用CPU
./start_whisper_server.sh whisper large-v3 10095 cpu
```

### 3. 端口占用

```bash
# 检查端口占用
lsof -i :10095

# 使用其他端口
./start_whisper_server.sh whisper large-v3 10096 cuda
```

## 📝 使用示例

### 1. 启动Whisper服务器

```bash
cd /Users/csdn/github_projects/FunASR
./start_whisper_server.sh whisper large-v3 10095 cuda
```

### 2. 启动前端服务器

```bash
cd runtime/html5/static
python -m http.server 1337
```

### 3. 访问前端界面

打开浏览器访问: `http://127.0.0.1:1337`

### 4. 配置WebSocket地址

在前端界面中设置: `ws://127.0.0.1:10095/`

### 5. 上传音频文件测试

选择MP3/WAV文件，点击连接，查看识别结果！

## 🎉 优势总结

✅ **第一梯队模型**: Whisper在语音识别领域排名第一  
✅ **完全免费**: 无API调用费用，可本地部署  
✅ **多语言支持**: 支持99种语言自动识别  
✅ **高准确率**: 特别是在噪音环境下表现优异  
✅ **时间戳**: 提供详细的词级时间戳  
✅ **灵活配置**: 可根据需求选择不同大小的模型  
✅ **无缝集成**: 与现有FunASR项目完美结合

现在你拥有了一个强大的多模型语音识别系统！🎊 