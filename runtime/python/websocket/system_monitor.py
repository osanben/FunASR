#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psutil
import platform
import time
import threading
from datetime import datetime
import socket

class SystemMonitor:
    """系统负载监控器"""
    
    def __init__(self, database=None):
        self.database = database
        self.machine_name = self._get_machine_name()
        self.concurrent_tasks = 0
        self.max_concurrent_tasks = 0
        self.monitoring = False
        self.monitor_thread = None
        self.monitor_interval = 30  # 30秒收集一次数据
        
        # 初始化IO和网络计数器
        self.last_io = psutil.disk_io_counters()
        self.last_net = psutil.net_io_counters()
        self.last_time = time.time()
    
    def _get_machine_name(self):
        """获取机器名称"""
        try:
            # 尝试获取主机名
            hostname = socket.gethostname()
            if hostname:
                return hostname
        except:
            pass
        
        try:
            # 备选方案：使用platform
            return platform.node()
        except:
            pass
        
        return "Unknown"
    
    def get_system_info(self):
        """获取系统基本信息"""
        try:
            return {
                'machine_name': self.machine_name,
                'platform': platform.platform(),
                'processor': platform.processor(),
                'cpu_count': psutil.cpu_count(),
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'memory_total': psutil.virtual_memory().total,
                'boot_time': psutil.boot_time()
            }
        except Exception as e:
            print(f"⚠️ 获取系统信息失败: {e}")
            return {'machine_name': self.machine_name}
    
    def get_current_load(self):
        """获取当前系统负载"""
        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            memory_total = memory.total / (1024**3)  # GB
            memory_available = memory.available / (1024**3)  # GB
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            disk_total = disk.total / (1024**3)  # GB
            disk_free = disk.free / (1024**3)  # GB
            
            # IO统计
            current_io = psutil.disk_io_counters()
            current_time = time.time()
            time_delta = current_time - self.last_time
            
            io_read_bytes = 0
            io_write_bytes = 0
            if self.last_io and time_delta > 0:
                io_read_bytes = (current_io.read_bytes - self.last_io.read_bytes) / time_delta
                io_write_bytes = (current_io.write_bytes - self.last_io.write_bytes) / time_delta
            
            # 网络统计
            current_net = psutil.net_io_counters()
            network_sent_bytes = 0
            network_recv_bytes = 0
            if self.last_net and time_delta > 0:
                network_sent_bytes = (current_net.bytes_sent - self.last_net.bytes_sent) / time_delta
                network_recv_bytes = (current_net.bytes_recv - self.last_net.bytes_recv) / time_delta
            
            # 更新上次记录
            self.last_io = current_io
            self.last_net = current_net
            self.last_time = current_time
            
            # 负载平均值（仅Linux/Unix系统）
            load_average_1m = None
            load_average_5m = None
            load_average_15m = None
            try:
                if hasattr(psutil, 'getloadavg'):
                    load_avg = psutil.getloadavg()
                    load_average_1m = load_avg[0]
                    load_average_5m = load_avg[1]
                    load_average_15m = load_avg[2]
            except:
                pass
            
            return {
                'machine_name': self.machine_name,
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'memory_total': memory_total,
                'memory_available': memory_available,
                'disk_usage': disk_usage,
                'disk_total': disk_total,
                'disk_free': disk_free,
                'io_read_bytes': io_read_bytes,
                'io_write_bytes': io_write_bytes,
                'network_sent_bytes': network_sent_bytes,
                'network_recv_bytes': network_recv_bytes,
                'concurrent_tasks': self.concurrent_tasks,
                'max_concurrent_tasks': self.max_concurrent_tasks,
                'load_average_1m': load_average_1m,
                'load_average_5m': load_average_5m,
                'load_average_15m': load_average_15m,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"⚠️ 获取系统负载失败: {e}")
            return {
                'machine_name': self.machine_name,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def increment_concurrent_tasks(self):
        """增加并发任务计数"""
        self.concurrent_tasks += 1
        self.max_concurrent_tasks = max(self.max_concurrent_tasks, self.concurrent_tasks)
        print(f"📊 当前并发任务: {self.concurrent_tasks}, 峰值: {self.max_concurrent_tasks}")
    
    def decrement_concurrent_tasks(self):
        """减少并发任务计数"""
        if self.concurrent_tasks > 0:
            self.concurrent_tasks -= 1
        print(f"📊 当前并发任务: {self.concurrent_tasks}, 峰值: {self.max_concurrent_tasks}")
    
    def start_monitoring(self):
        """开始监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"🔍 系统负载监控已启动 (间隔: {self.monitor_interval}秒)")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("🔍 系统负载监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                # 获取当前负载
                load_data = self.get_current_load()
                
                # 保存到数据库
                if self.database and 'error' not in load_data:
                    self.database.add_system_load(
                        machine_name=load_data['machine_name'],
                        cpu_usage=load_data.get('cpu_usage'),
                        memory_usage=load_data.get('memory_usage'),
                        memory_total=load_data.get('memory_total'),
                        memory_available=load_data.get('memory_available'),
                        disk_usage=load_data.get('disk_usage'),
                        disk_total=load_data.get('disk_total'),
                        disk_free=load_data.get('disk_free'),
                        io_read_bytes=load_data.get('io_read_bytes'),
                        io_write_bytes=load_data.get('io_write_bytes'),
                        network_sent_bytes=load_data.get('network_sent_bytes'),
                        network_recv_bytes=load_data.get('network_recv_bytes'),
                        concurrent_tasks=load_data.get('concurrent_tasks', 0),
                        max_concurrent_tasks=load_data.get('max_concurrent_tasks', 0),
                        load_average_1m=load_data.get('load_average_1m'),
                        load_average_5m=load_data.get('load_average_5m'),
                        load_average_15m=load_data.get('load_average_15m')
                    )
                
                # 等待下次监控
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                print(f"⚠️ 监控循环错误: {e}")
                time.sleep(self.monitor_interval)
    
    def get_performance_summary(self):
        """获取性能摘要"""
        load_data = self.get_current_load()
        
        # 计算性能等级
        cpu_level = "低" if load_data.get('cpu_usage', 0) < 50 else "中" if load_data.get('cpu_usage', 0) < 80 else "高"
        memory_level = "低" if load_data.get('memory_usage', 0) < 60 else "中" if load_data.get('memory_usage', 0) < 85 else "高"
        
        # 估算可支持的并发转录数
        cpu_usage = load_data.get('cpu_usage', 0)
        memory_usage = load_data.get('memory_usage', 0)
        
        # 简单的并发能力估算（基于经验值）
        cpu_capacity = max(1, int((100 - cpu_usage) / 20))  # 每20%CPU可支持1路转录
        memory_capacity = max(1, int((100 - memory_usage) / 15))  # 每15%内存可支持1路转录
        estimated_capacity = min(cpu_capacity, memory_capacity)
        
        return {
            'machine_name': self.machine_name,
            'cpu_usage': load_data.get('cpu_usage', 0),
            'cpu_level': cpu_level,
            'memory_usage': load_data.get('memory_usage', 0),
            'memory_level': memory_level,
            'disk_usage': load_data.get('disk_usage', 0),
            'concurrent_tasks': self.concurrent_tasks,
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'estimated_capacity': estimated_capacity,
            'status': '正常' if cpu_usage < 80 and memory_usage < 85 else '高负载',
            'timestamp': load_data.get('timestamp')
        }

# 全局系统监控实例
system_monitor = None

def get_system_monitor(database=None):
    """获取系统监控实例"""
    global system_monitor
    if system_monitor is None:
        system_monitor = SystemMonitor(database)
    return system_monitor 