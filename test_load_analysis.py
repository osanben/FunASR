#!/usr/bin/env python3
"""
测试并发负载分析功能
模拟不同并发级别下的性能数据
"""

import sqlite3
import random
import time
from datetime import datetime, timedelta
import socket

def get_machine_name():
    """获取机器名"""
    return socket.gethostname()

def generate_mock_data():
    """生成模拟数据"""
    print("🔄 生成模拟性能数据...")
    
    # 连接数据库
    conn = sqlite3.connect('funasr_data.db')
    cursor = conn.cursor()
    
    machine_name = get_machine_name()
    base_time = datetime.now() - timedelta(hours=2)
    
    # 生成不同并发级别的数据
    concurrent_levels = [1, 2, 3, 4, 5, 6, 8, 10, 12]
    
    for i in range(100):  # 生成100条记录
        # 随机选择并发级别
        concurrent = random.choice(concurrent_levels)
        
        # 根据并发数模拟CPU和内存使用率
        base_cpu = 20 + concurrent * 8 + random.uniform(-5, 5)
        base_memory = 30 + concurrent * 6 + random.uniform(-3, 3)
        
        # 确保不超过100%
        cpu_usage = min(95, max(10, base_cpu))
        memory_usage = min(90, max(20, base_memory))
        
        # 模拟音频处理数据
        audio_duration = random.uniform(30, 300)  # 30秒到5分钟
        processing_time = audio_duration * random.uniform(0.2, 0.8)  # 处理时间
        
        # 时间戳
        timestamp = base_time + timedelta(minutes=i*2)
        
        # 插入系统负载数据
        cursor.execute('''
            INSERT INTO system_load_monitor 
            (machine_name, cpu_usage, memory_usage, memory_total, memory_available,
             disk_usage, disk_total, disk_free, io_read_bytes, io_write_bytes, 
             network_sent_bytes, network_recv_bytes, concurrent_tasks, max_concurrent_tasks, 
             load_average_1m, load_average_5m, load_average_15m, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            machine_name,
            cpu_usage,
            memory_usage,
            16.0,  # memory_total (GB)
            16.0 * (1 - memory_usage / 100),  # memory_available
            random.uniform(40, 80),  # disk_usage
            500.0,  # disk_total (GB)
            500.0 * (1 - random.uniform(40, 80) / 100),  # disk_free
            random.uniform(50, 200) * 1024 * 1024,  # io_read_bytes
            random.uniform(30, 150) * 1024 * 1024,  # io_write_bytes
            random.uniform(5, 50) * 1024 * 1024,    # network_sent_bytes
            random.uniform(10, 100) * 1024 * 1024,  # network_recv_bytes
            concurrent,
            max(concurrent, random.randint(concurrent, concurrent + 2)),
            cpu_usage / 100 * 4,  # load_average_1m
            cpu_usage / 100 * 4,  # load_average_5m
            cpu_usage / 100 * 4,  # load_average_15m
            timestamp.isoformat()
        ))
        
        # 插入性能报告数据
        task_id = f"test_task_{i}_{int(time.time())}"
        cursor.execute('''
            INSERT INTO performance_reports 
            (task_id, machine_name, audio_duration, total_processing_time, 
             transcription_time, speaker_separation_time, speaker_matching_time,
             cpu_usage, memory_usage, model_type, device_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_id,
            machine_name,
            audio_duration,
            processing_time,
            processing_time * 0.7,  # transcription_time
            processing_time * 0.2,  # speaker_separation_time
            processing_time * 0.1,  # speaker_matching_time
            cpu_usage,
            memory_usage,
            "paraformer",  # model_type
            "cuda" if concurrent > 6 else "cpu",  # device_type
            timestamp.isoformat()
        ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 已生成100条模拟数据记录")

def test_api_endpoints():
    """测试API端点"""
    import requests
    
    base_url = "http://localhost:8080"
    endpoints = [
        "/api/system_load_current",
        "/api/system_load_history?limit=20",
        "/api/system_load_statistics",
        "/api/performance_reports?limit=50",
        "/api/machine_list"
    ]
    
    print("\n🧪 测试API端点...")
    
    for endpoint in endpoints:
        try:
            response = requests.get(base_url + endpoint, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint}: {len(data) if isinstance(data, list) else 'OK'}")
            else:
                print(f"❌ {endpoint}: HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint}: {str(e)}")

def analyze_concurrent_load():
    """分析并发负载关系"""
    print("\n📊 分析并发负载关系...")
    
    conn = sqlite3.connect('funasr_data.db')
    cursor = conn.cursor()
    
    # 查询数据
    cursor.execute('''
        SELECT 
            s.concurrent_tasks,
            s.cpu_usage,
            s.memory_usage,
            AVG(CASE WHEN p.audio_duration > 0 THEN p.total_processing_time / p.audio_duration ELSE NULL END) as avg_efficiency,
            COUNT(*) as sample_count
        FROM system_load_monitor s
        LEFT JOIN performance_reports p ON 
            DATE(s.created_at) = DATE(p.created_at) AND
            ABS(strftime('%s', s.created_at) - strftime('%s', p.created_at)) < 300
        WHERE s.concurrent_tasks > 0
        GROUP BY s.concurrent_tasks, ROUND(s.cpu_usage/10)*10, ROUND(s.memory_usage/10)*10
        ORDER BY s.concurrent_tasks
    ''')
    
    results = cursor.fetchall()
    
    print("\n📈 并发负载分析结果:")
    print("并发数 | CPU使用率 | 内存使用率 | 平均效率 | 样本数")
    print("-" * 55)
    
    for row in results:
        concurrent, cpu, memory, efficiency, count = row
        efficiency_str = f"{efficiency:.3f}" if efficiency else "N/A"
        print(f"{concurrent:6d} | {cpu:8.1f}% | {memory:9.1f}% | {efficiency_str:8s} | {count:6d}")
    
    # 找出最佳配置
    optimal_configs = [row for row in results if row[1] < 80 and row[2] < 85 and row[3] and row[3] < 0.5]
    
    if optimal_configs:
        best_config = min(optimal_configs, key=lambda x: x[3])  # 最低效率比
        print(f"\n🎯 推荐最佳配置:")
        print(f"   并发数: {best_config[0]}")
        print(f"   CPU使用率: {best_config[1]:.1f}%")
        print(f"   内存使用率: {best_config[2]:.1f}%")
        print(f"   效率比: {best_config[3]:.3f}")
    
    conn.close()

def main():
    print("🧪 FunASR 并发负载分析测试")
    print("=" * 40)
    
    # 生成模拟数据
    generate_mock_data()
    
    # 分析数据
    analyze_concurrent_load()
    
    # 测试API（如果服务器在运行）
    test_api_endpoints()
    
    print("\n✅ 测试完成！")
    print("💡 提示：访问 http://localhost:8080/system_monitor 查看并发负载分析页面")

if __name__ == "__main__":
    main() 