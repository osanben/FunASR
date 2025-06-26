#!/usr/bin/env python3
"""
FunASR 并发性能测试脚本
用于测试服务器的最大并发处理能力，帮助优化配置
"""

import asyncio
import aiohttp
import time
import os
import json
from pathlib import Path
import argparse

class ConcurrencyTester:
    def __init__(self, server_url="http://localhost:8080"):
        self.server_url = server_url
        self.results = []
        
    async def upload_audio_file(self, session, file_path, test_id):
        """上传单个音频文件"""
        start_time = time.time()
        
        try:
            with open(file_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('audio', f, filename=os.path.basename(file_path))
                
                async with session.post(f"{self.server_url}/upload", data=data) as resp:
                    upload_time = time.time() - start_time
                    
                    if resp.status == 200:
                        result = await resp.json()
                        task_id = result.get('task_id')
                        
                        # 等待处理完成
                        processing_time = await self.wait_for_completion(session, task_id)
                        
                        total_time = time.time() - start_time
                        
                        return {
                            "test_id": test_id,
                            "task_id": task_id,
                            "upload_time": upload_time,
                            "processing_time": processing_time,
                            "total_time": total_time,
                            "status": "success",
                            "file_size": os.path.getsize(file_path)
                        }
                    elif resp.status == 503:
                        # 服务器负载过高
                        return {
                            "test_id": test_id,
                            "status": "server_overload",
                            "upload_time": upload_time,
                            "total_time": time.time() - start_time
                        }
                    else:
                        error_text = await resp.text()
                        return {
                            "test_id": test_id,
                            "status": "upload_failed",
                            "error": error_text,
                            "total_time": time.time() - start_time
                        }
                        
        except Exception as e:
            return {
                "test_id": test_id,
                "status": "error",
                "error": str(e),
                "total_time": time.time() - start_time
            }
    
    async def wait_for_completion(self, session, task_id, timeout=300):
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                async with session.get(f"{self.server_url}/status/{task_id}") as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        status = result.get('status')
                        
                        if status == 'completed':
                            return time.time() - start_time
                        elif status == 'error':
                            return time.time() - start_time
                        
                        # 等待1秒后再次检查
                        await asyncio.sleep(1)
                    else:
                        await asyncio.sleep(1)
                        
            except Exception as e:
                print(f"检查任务状态失败: {e}")
                await asyncio.sleep(1)
        
        return timeout  # 超时
    
    async def test_concurrent_uploads(self, audio_file, concurrent_count, test_name=""):
        """测试并发上传"""
        print(f"\n🚀 开始测试: {test_name}")
        print(f"📁 音频文件: {audio_file}")
        print(f"🔢 并发数: {concurrent_count}")
        
        start_time = time.time()
        
        # 检查服务器状态
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/api/system_load_current") as resp:
                    if resp.status == 200:
                        system_info = await resp.json()
                        print(f"📊 测试前系统状态: CPU {system_info.get('cpu_usage', 0):.1f}%, 内存 {system_info.get('memory_usage', 0):.1f}%")
        except:
            pass
        
        # 创建并发任务
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600)) as session:
            tasks = []
            for i in range(concurrent_count):
                task = self.upload_audio_file(session, audio_file, f"{test_name}_{i+1}")
                tasks.append(task)
            
            # 执行并发测试
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # 分析结果
        successful = [r for r in results if isinstance(r, dict) and r.get('status') == 'success']
        overloaded = [r for r in results if isinstance(r, dict) and r.get('status') == 'server_overload']
        failed = [r for r in results if isinstance(r, dict) and r.get('status') not in ['success', 'server_overload']]
        errors = [r for r in results if isinstance(r, Exception)]
        
        print(f"\n📊 测试结果 ({test_name}):")
        print(f"⏱️  总耗时: {total_time:.2f}秒")
        print(f"✅ 成功: {len(successful)}")
        print(f"⚠️  服务器过载: {len(overloaded)}")
        print(f"❌ 失败: {len(failed)}")
        print(f"💥 异常: {len(errors)}")
        
        if successful:
            avg_processing = sum(r['processing_time'] for r in successful) / len(successful)
            avg_total = sum(r['total_time'] for r in successful) / len(successful)
            print(f"📈 平均处理时间: {avg_processing:.2f}秒")
            print(f"📈 平均总时间: {avg_total:.2f}秒")
        
        # 检查测试后系统状态
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/api/system_load_current") as resp:
                    if resp.status == 200:
                        system_info = await resp.json()
                        print(f"📊 测试后系统状态: CPU {system_info.get('cpu_usage', 0):.1f}%, 内存 {system_info.get('memory_usage', 0):.1f}%")
        except:
            pass
        
        return {
            'test_name': test_name,
            'concurrent_count': concurrent_count,
            'total_time': total_time,
            'successful': len(successful),
            'overloaded': len(overloaded),
            'failed': len(failed),
            'errors': len(errors),
            'avg_processing_time': avg_processing if successful else 0,
            'avg_total_time': avg_total if successful else 0,
            'results': results
        }
    
    async def run_stress_test(self, audio_file):
        """运行压力测试"""
        print("🎯 开始FunASR并发性能压力测试")
        print(f"🎵 测试音频: {audio_file}")
        
        if not os.path.exists(audio_file):
            print(f"❌ 音频文件不存在: {audio_file}")
            return
        
        # 测试不同并发级别
        test_levels = [1, 2, 4, 6, 8, 10, 12, 16, 20]
        all_results = []
        
        for concurrent_count in test_levels:
            try:
                result = await self.test_concurrent_uploads(
                    audio_file, 
                    concurrent_count, 
                    f"并发测试_{concurrent_count}"
                )
                all_results.append(result)
                
                # 如果服务器过载超过50%，停止增加并发
                if result['overloaded'] > concurrent_count * 0.5:
                    print(f"⚠️ 服务器过载率过高，停止增加并发数")
                    break
                    
                # 等待5秒让服务器恢复
                print("⏳ 等待5秒让服务器恢复...")
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"❌ 测试失败: {e}")
                break
        
        # 生成报告
        self.generate_report(all_results)
    
    def generate_report(self, results):
        """生成测试报告"""
        print("\n" + "="*60)
        print("📊 FunASR 并发性能测试报告")
        print("="*60)
        
        print(f"{'并发数':<8} {'成功率':<8} {'平均处理时间':<12} {'服务器过载':<10} {'推荐':<6}")
        print("-" * 60)
        
        best_concurrent = 1
        best_efficiency = 0
        
        for result in results:
            concurrent = result['concurrent_count']
            success_rate = result['successful'] / concurrent * 100 if concurrent > 0 else 0
            avg_processing = result['avg_processing_time']
            overload_rate = result['overloaded'] / concurrent * 100 if concurrent > 0 else 0
            
            # 计算效率分数 (成功率 * 并发数 / 平均处理时间)
            efficiency = (success_rate * concurrent / max(avg_processing, 1)) if avg_processing > 0 else 0
            
            recommend = ""
            if efficiency > best_efficiency and success_rate > 80 and overload_rate < 20:
                best_efficiency = efficiency
                best_concurrent = concurrent
                recommend = "✅"
            
            print(f"{concurrent:<8} {success_rate:<7.1f}% {avg_processing:<11.2f}s {overload_rate:<9.1f}% {recommend:<6}")
        
        print("-" * 60)
        print(f"🎯 推荐最佳并发数: {best_concurrent}")
        
        # 保存详细结果到文件
        with open('concurrent_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"📄 详细结果已保存到: concurrent_test_results.json")

async def main():
    parser = argparse.ArgumentParser(description='FunASR 并发性能测试')
    parser.add_argument('--server', default='http://localhost:8080', help='服务器地址')
    parser.add_argument('--audio', required=True, help='测试音频文件路径')
    parser.add_argument('--concurrent', type=int, help='指定并发数进行单次测试')
    
    args = parser.parse_args()
    
    tester = ConcurrencyTester(args.server)
    
    if args.concurrent:
        # 单次测试
        await tester.test_concurrent_uploads(args.audio, args.concurrent, f"单次测试_{args.concurrent}")
    else:
        # 完整压力测试
        await tester.run_stress_test(args.audio)

if __name__ == "__main__":
    asyncio.run(main()) 