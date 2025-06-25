#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Chrome浏览器控制台错误信息的脚本
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def check_console_errors():
    """检查浏览器控制台错误"""
    print("🔍 正在启动Chrome浏览器检查控制台错误...")
    
    # Chrome选项配置
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # 启用日志记录
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--log-level=0")
    chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # 访问FunASR页面
        print("🌐 正在访问FunASR页面...")
        driver.get("http://localhost:8080/upload_demo")
        
        # 等待页面加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        print("✅ 页面加载完成，正在检查控制台...")
        
        # 获取浏览器日志
        logs = driver.get_log('browser')
        
        if logs:
            print("\n🚨 浏览器控制台消息:")
            print("=" * 60)
            
            for log in logs:
                level = log['level']
                message = log['message']
                timestamp = log['timestamp']
                
                # 根据日志级别使用不同的图标
                if level == 'SEVERE':
                    icon = "❌"
                elif level == 'WARNING':
                    icon = "⚠️"
                elif level == 'INFO':
                    icon = "ℹ️"
                else:
                    icon = "📝"
                
                print(f"{icon} [{level}] {message}")
                print(f"   时间: {timestamp}")
                print("-" * 60)
        else:
            print("✅ 控制台没有错误或警告信息")
        
        # 检查网络错误
        print("\n🌐 检查网络请求...")
        network_logs = driver.get_log('performance')
        
        error_count = 0
        for log in network_logs:
            message = log.get('message', {})
            if isinstance(message, str):
                import json
                try:
                    message = json.loads(message)
                except:
                    continue
                    
            method = message.get('message', {}).get('method', '')
            params = message.get('message', {}).get('params', {})
            
            if method == 'Network.responseReceived':
                response = params.get('response', {})
                status = response.get('status', 0)
                url = response.get('url', '')
                
                if status >= 400:
                    print(f"❌ 网络错误: {status} - {url}")
                    error_count += 1
        
        if error_count == 0:
            print("✅ 没有发现网络错误")
        
        # 执行JavaScript来获取更详细的错误信息
        print("\n🔍 执行JavaScript检查...")
        js_errors = driver.execute_script("""
            var errors = [];
            
            // 检查是否有JavaScript错误
            if (window.console && console.error) {
                var originalError = console.error;
                console.error = function() {
                    errors.push('Console Error: ' + Array.prototype.slice.call(arguments).join(' '));
                    originalError.apply(console, arguments);
                };
            }
            
            // 检查页面状态
            var status = {
                readyState: document.readyState,
                title: document.title,
                url: window.location.href,
                hasErrors: errors.length > 0,
                errors: errors
            };
            
            return status;
        """)
        
        print(f"📄 页面状态:")
        print(f"   标题: {js_errors.get('title', 'N/A')}")
        print(f"   URL: {js_errors.get('url', 'N/A')}")
        print(f"   加载状态: {js_errors.get('readyState', 'N/A')}")
        
        if js_errors.get('hasErrors'):
            print(f"❌ JavaScript错误:")
            for error in js_errors.get('errors', []):
                print(f"   {error}")
        else:
            print("✅ 没有发现JavaScript错误")
        
        # 保持浏览器打开一段时间，让用户可以手动检查
        print("\n💡 浏览器将保持打开30秒，您可以手动检查控制台...")
        print("   按F12打开开发者工具查看Console选项卡")
        
        time.sleep(30)
        
    except Exception as e:
        print(f"❌ 检查过程中出错: {e}")
    finally:
        print("🧹 关闭浏览器...")
        driver.quit()

if __name__ == "__main__":
    check_console_errors() 