# FunASR 语音识别服务使用说明

## 🎯 功能概述

本FunASR服务提供两种语音识别方式：
1. **文件上传识别** - 支持多种音频格式的文件上传和批量处理
2. **实时语音识别** - 支持麦克风实时录音和语音识别

## 🚀 启动服务

### 完整服务启动（推荐）
```bash
# 启动所有服务（文件上传 + 实时录音）
python start_complete_funasr_service.py --device cuda --ngpu 1

# 可选参数
python start_complete_funasr_service.py \
    --model_type paraformer \  # 模型类型: paraformer, whisper, sensevoice, hybrid
    --device cuda \            # 设备: cuda, cpu
    --ngpu 1                   # GPU数量
```

### 单独启动文件上传服务
```bash
python runtime/python/websocket/funasr_upload_server.py \
    --host 0.0.0.0 \
    --model_type paraformer \
    --device cuda \
    --ngpu 1
```

### 单独启动实时WebSocket服务
```bash
python runtime/python/websocket/funasr_wss_server.py \
    --host 0.0.0.0 \
    --port 10095 \
    --device cuda \
    --ngpu 1
```

## 🌐 访问地址

### 文件上传服务
- **上传页面**: `https://gpu-cqao559xgb-8080.node.inscode.run/`
- **实时录音页面**: `https://gpu-cqao559xgb-8080.node.inscode.run/realtime`

### WebSocket服务
- **实时语音识别**: `wss://gpu-cqao559xgb-10095.node.inscode.run/`

## 📁 文件上传识别

### 支持的音频格式
- **压缩格式**: MP3, M4A, AAC
- **无损格式**: WAV, FLAC
- **其他格式**: OGG

### 使用步骤
1. 访问上传页面
2. 选择音频文件
3. 点击"上传并识别"
4. 等待处理完成
5. 查看识别结果

### 功能特性
- ✅ 自动音频格式转换
- ✅ 多种模型支持（Whisper + FunASR）
- ✅ 说话人分离识别
- ✅ 时间戳标注
- ✅ 实时处理进度显示

## 🎤 实时语音识别

### 使用步骤
1. 访问实时录音页面
2. 配置WebSocket服务器地址
3. 选择识别模式和参数
4. 点击"连接服务器"
5. 点击"开始录音"
6. 说话进行实时识别
7. 点击"停止录音"结束

### 识别模式
- **2pass** (推荐): 两遍识别，准确率最高
- **online**: 在线实时识别，延迟最低
- **offline**: 离线识别，处理完整音频

### 高级配置
- **热词设置**: 提升专业词汇识别准确率
- **逆文本标准化**: 数字和符号格式化
- **音频电平显示**: 实时监控录音状态

## 🔧 模型类型说明

### paraformer
- **适用**: 中文语音识别
- **特点**: 高准确率，支持时间戳和说话人分离
- **推荐**: 中文场景首选

### whisper
- **适用**: 多语言语音识别
- **特点**: 支持100+语言，自动语言检测
- **推荐**: 多语言或英文场景

### sensevoice
- **适用**: 情感和语音事件检测
- **特点**: 支持情感识别，语音事件检测
- **推荐**: 需要情感分析的场景

### hybrid
- **适用**: 最全功能支持
- **特点**: 同时使用多个模型，结果对比
- **推荐**: 对准确率要求极高的场景

## 📊 说话人分离

### 功能说明
- 自动识别不同说话人
- 为每个说话人分配标签（说话人1、说话人2...）
- 提供时间戳信息
- 支持音色特征分析

### 适用场景
- 会议记录
- 采访转录
- 多人对话
- 播客内容

## 🎯 热词配置

### 格式说明
```
词语1 权重1
词语2 权重2
```

### 示例
```
阿里巴巴 20
人工智能 30
FunASR 40
```

### 权重说明
- 权重越高，识别该词的概率越大
- 建议权重范围：10-50
- 专业术语建议使用较高权重

## 🔍 故障排除

### 常见问题

**1. 连接失败**
- 检查WebSocket地址是否正确
- 确认服务器是否正常运行
- 检查网络连接

**2. 录音无声音**
- 检查麦克风权限
- 确认麦克风设备正常
- 查看音频电平指示器

**3. 识别结果为空**
- 确认音频质量
- 检查语言设置
- 尝试调整热词配置

**4. 文件上传失败**
- 检查文件格式是否支持
- 确认文件大小限制
- 检查网络稳定性

### 日志查看
```bash
# 查看服务器日志
tail -f logs/websocket.log

# 查看浏览器控制台
F12 -> Console
```

## 📈 性能优化

### GPU加速
```bash
# 使用GPU加速
python start_complete_funasr_service.py --device cuda --ngpu 1

# 多GPU支持
python start_complete_funasr_service.py --device cuda --ngpu 2
```

### CPU优化
```bash
# CPU多线程
python start_complete_funasr_service.py --device cpu --ncpu 8
```

### 内存优化
- 使用较小的Whisper模型（base, small）
- 减少并发连接数
- 定期清理临时文件

## 🛡️ 安全说明

### 数据隐私
- 音频文件处理完成后自动删除
- 不存储用户语音数据
- 实时识别不保存音频

### 网络安全
- 支持HTTPS/WSS加密传输
- 可配置访问控制
- 支持SSL证书

## 📞 技术支持

如有问题，请检查：
1. 服务器日志输出
2. 浏览器控制台错误
3. 网络连接状态
4. 音频设备状态

## 🔄 更新日志

### v1.0.0
- ✅ 支持文件上传识别
- ✅ 支持实时语音识别
- ✅ 集成说话人分离
- ✅ 支持多种音频格式
- ✅ GPU加速支持
- ✅ 热词配置功能 