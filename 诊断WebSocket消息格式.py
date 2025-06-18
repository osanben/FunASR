#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunASR WebSocket消息格式诊断工具
"""

import json
import asyncio
import websockets
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FunASRMessageDiagnostics:
    def __init__(self):
        self.expected_formats = {}
        self.actual_formats = {}
        
    def analyze_frontend_expectations(self):
        """分析前端期望的消息格式"""
        print("🔍 分析FunASR前端期望的消息格式:")
        print()
        
        # 根据main.js中getJsonMessage函数分析
        expected_response = {
            "text": "识别的文字内容",
            "mode": "2pass-offline|offline|online等模式", 
            "is_final": "true|false 是否最终结果",
            "timestamp": "时间戳信息"
        }
        
        print("📥 前端期望接收的消息格式:")
        print(json.dumps(expected_response, indent=2, ensure_ascii=False))
        print()
        
        # 根据wsconnecter.js中onOpen函数分析
        expected_request = {
            "chunk_size": [5, 10, 5],
            "wav_name": "h5",
            "is_speaking": True,  # 开始时为true，结束时为false
            "chunk_interval": 10,
            "itn": "是否使用ITN",
            "mode": "识别模式",
            "wav_format": "音频格式(文件模式)",
            "audio_fs": "采样率(wav文件)",
            "hotwords": "热词(可选)"
        }
        
        print("📤 前端发送的初始消息格式:")
        print(json.dumps(expected_request, indent=2, ensure_ascii=False))
        print()
        
        return expected_response, expected_request
    
    def analyze_current_implementation(self):
        """分析当前实现的消息格式"""
        print("🔍 分析当前WebSocket服务的消息格式:")
        print()
        
        # 当前返回的格式
        current_response = {
            "type": "final_result",  # ❌ 前端不期望这个字段
            "text": "识别结果",      # ✅ 正确
            "is_final": True,        # ✅ 正确
            "confidence": 0.95,      # ❌ 前端不期望这个字段  
            "timestamp": "时间戳"     # ✅ 正确，但缺少mode字段
        }
        
        print("📥 当前服务返回的消息格式:")
        print(json.dumps(current_response, indent=2, ensure_ascii=False))
        print()
        
        return current_response
    
    def identify_compatibility_issues(self):
        """识别兼容性问题"""
        print("⚠️ 发现的兼容性问题:")
        print()
        
        issues = [
            {
                "问题": "缺少mode字段",
                "说明": "前端getJsonMessage函数需要mode字段来判断识别模式",
                "影响": "无法正确处理离线/在线模式的结果"
            },
            {
                "问题": "多余的type字段",
                "说明": "前端不处理type字段，这是我们自定义的",
                "影响": "增加消息大小，可能造成混淆"
            },
            {
                "问题": "多余的confidence字段",
                "说明": "前端不处理confidence字段",
                "影响": "增加消息大小"
            },
            {
                "问题": "初始连接消息格式不匹配",
                "说明": "前端发送特定格式的初始消息，我们需要正确解析",
                "影响": "可能导致连接建立后无法正常通信"
            }
        ]
        
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue['问题']}")
            print(f"   说明: {issue['说明']}")
            print(f"   影响: {issue['影响']}")
            print()
        
        return issues
    
    def generate_fix_recommendations(self):
        """生成修复建议"""
        print("🔧 修复建议:")
        print()
        
        recommendations = [
            {
                "修复": "调整返回消息格式",
                "代码": '''
# 修正后的消息格式
response = {
    "text": result_text,
    "mode": "2pass-offline",  # 添加mode字段
    "is_final": True,
    "timestamp": datetime.now().isoformat()
    # 移除type和confidence字段
}'''
            },
            {
                "修复": "正确处理前端初始连接消息",
                "代码": '''
# 在process_message中处理初始连接消息
if "chunk_size" in data and "wav_name" in data:
    # 这是前端的初始连接消息
    await self.handle_initial_connection(websocket, data)'''
            },
            {
                "修复": "处理二进制音频数据",
                "代码": '''
# 前端会发送PCM音频数据和JSON控制消息
async def process_message(self, websocket, message):
    if isinstance(message, bytes):
        # 处理二进制音频数据
        await self.handle_pcm_audio(websocket, message)
    else:
        # 处理JSON控制消息
        data = json.loads(message)
        await self.handle_control_message(websocket, data)'''
            }
        ]
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec['修复']}")
            print(f"   代码示例:")
            print(rec['代码'])
            print()
        
        return recommendations

def main():
    """主函数"""
    print("🎯 FunASR WebSocket消息格式诊断报告")
    print("=" * 60)
    print()
    
    diagnostics = FunASRMessageDiagnostics()
    
    # 分析期望格式
    expected_response, expected_request = diagnostics.analyze_frontend_expectations()
    
    # 分析当前实现
    current_response = diagnostics.analyze_current_implementation()
    
    # 识别问题
    issues = diagnostics.identify_compatibility_issues()
    
    # 生成修复建议
    recommendations = diagnostics.generate_fix_recommendations()
    
    print("📋 总结:")
    print(f"- 发现 {len(issues)} 个兼容性问题")
    print(f"- 提供 {len(recommendations)} 个修复建议")
    print("- 主要问题是消息格式不匹配，需要调整WebSocket服务")
    print()
    print("💡 建议立即修复WebSocket服务以匹配前端期望格式")

if __name__ == "__main__":
    main() 