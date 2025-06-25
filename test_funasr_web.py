#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunASR Web界面自动化测试脚本
使用Selenium驱动Chrome浏览器进行文件上传和语音识别测试
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class FunASRWebTester:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.driver = None
        
    def setup_driver(self):
        """设置Chrome WebDriver"""
        print("🚀 正在启动Chrome浏览器...")
        
        # Chrome选项配置
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # 如果需要无头模式，取消下面的注释
        # chrome_options.add_argument("--headless")
        
        # 自动下载并设置ChromeDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.maximize_window()
        print("✅ Chrome浏览器启动成功!")
        
    def select_page_to_test(self):
        """选择要测试的页面"""
        print("\n📋 请选择要测试的页面:")
        print("1. 基础上传页面 (/)")
        print("2. 完整演示页面 (/upload_demo)")
        print("3. 实时录音页面 (/realtime)")
        print("4. 说话人管理页面 (API测试)")
        
        while True:
            try:
                choice = input("请输入选择 (1-4): ").strip()
                if choice in ['1', '2', '3', '4']:
                    return int(choice)
                else:
                    print("❌ 无效选择，请输入1-4之间的数字")
            except KeyboardInterrupt:
                print("\n⚠️ 用户取消选择")
                return None
        
    def open_funasr_page(self, page_type=1):
        """打开FunASR Web页面"""
        page_urls = {
            1: self.base_url,
            2: f"{self.base_url}/upload_demo",
            3: f"{self.base_url}/realtime",
            4: self.base_url  # API测试使用基础页面
        }
        
        page_names = {
            1: "基础上传页面",
            2: "完整演示页面",
            3: "实时录音页面", 
            4: "说话人管理页面"
        }
        
        url = page_urls.get(page_type, self.base_url)
        page_name = page_names.get(page_type, "基础页面")
        
        print(f"🌐 正在访问 {page_name}: {url}")
        try:
            self.driver.get(url)
            print(f"✅ {page_name}加载成功!")
            return True, page_type
        except Exception as e:
            print(f"❌ 页面加载失败: {e}")
            return False, page_type
            
    def check_page_elements(self, page_type=1):
        """检查页面关键元素"""
        print("🔍 正在检查页面元素...")
        
        try:
            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 获取页面标题
            title = self.driver.title
            print(f"📄 页面标题: {title}")
            
            if page_type == 4:  # 说话人管理页面
                return self.check_speaker_management_elements()
            
            # 查找文件上传相关元素
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            print(f"📁 找到 {len(file_inputs)} 个文件上传控件")
            
            # 查找按钮元素
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            print(f"🔘 找到 {len(buttons)} 个按钮")
            
            # 查找特殊元素
            if page_type == 2:  # 完整演示页面
                # 查找说话人相关元素
                speaker_elements = self.driver.find_elements(By.CSS_SELECTOR, "[id*='speaker'], [class*='speaker']")
                print(f"🎭 找到 {len(speaker_elements)} 个说话人相关元素")
                
                # 查找音色关联相关元素
                voice_elements = self.driver.find_elements(By.CSS_SELECTOR, "[id*='voice'], [class*='voice'], [id*='register'], [class*='register']")
                print(f"🎵 找到 {len(voice_elements)} 个音色关联相关元素")
                
            elif page_type == 3:  # 实时录音页面
                # 查找录音相关元素
                record_elements = self.driver.find_elements(By.CSS_SELECTOR, "[id*='record'], [class*='record'], [id*='mic'], [class*='mic']")
                print(f"🎤 找到 {len(record_elements)} 个录音相关元素")
            
            # 打印页面源码的前500个字符（用于调试）
            page_source = self.driver.page_source[:500]
            print(f"📋 页面内容预览: {page_source}...")
            
            return True
            
        except TimeoutException:
            print("❌ 页面加载超时")
            return False
        except Exception as e:
            print(f"❌ 检查页面元素时出错: {e}")
            return False
    
    def check_speaker_management_elements(self):
        """检查说话人管理相关元素"""
        print("🎭 检查说话人管理功能...")
        
        # 检查是否有说话人注册相关的表单或按钮
        speaker_inputs = self.driver.find_elements(By.CSS_SELECTOR, 
            "input[name*='speaker'], input[id*='speaker'], input[placeholder*='说话人'], input[placeholder*='speaker']")
        print(f"👤 找到 {len(speaker_inputs)} 个说话人输入框")
        
        # 检查注册按钮
        register_buttons = self.driver.find_elements(By.XPATH, 
            "//button[contains(text(), '注册') or contains(text(), 'register') or contains(text(), '添加')]")
        print(f"📝 找到 {len(register_buttons)} 个注册相关按钮")
        
        return True
    
    def test_speaker_management_api(self):
        """测试说话人管理API"""
        print("\n🎭 测试说话人管理API功能...")
        
        # 使用JavaScript调用API
        test_script = """
        async function testSpeakerAPI() {
            try {
                // 获取说话人列表
                const listResponse = await fetch('/list_speakers');
                const speakers = await listResponse.json();
                console.log('说话人列表:', speakers);
                
                // 在页面上显示结果
                const resultDiv = document.createElement('div');
                resultDiv.id = 'api-test-results';
                resultDiv.innerHTML = `
                    <h3>🎭 说话人管理API测试结果</h3>
                    <p><strong>说话人列表:</strong> ${JSON.stringify(speakers, null, 2)}</p>
                `;
                resultDiv.style.cssText = 'background: #f8f9fa; padding: 15px; margin: 10px; border: 1px solid #dee2e6; border-radius: 4px;';
                document.body.appendChild(resultDiv);
                
                return speakers;
            } catch (error) {
                console.error('API测试失败:', error);
                const errorDiv = document.createElement('div');
                errorDiv.innerHTML = `<p style="color: red;">API测试失败: ${error}</p>`;
                document.body.appendChild(errorDiv);
                return null;
            }
        }
        return testSpeakerAPI();
        """
        
        try:
            result = self.driver.execute_script(test_script)
            print("✅ 说话人管理API测试完成")
            return True
        except Exception as e:
            print(f"❌ API测试失败: {e}")
            return False
    
    def wait_for_file_selection(self, timeout=60):
        """等待用户选择文件"""
        print("⏳ 请在浏览器中选择要上传的音频文件...")
        print("💡 支持的格式: wav, mp3, m4a, flac 等")
        print("⏰ 等待文件选择，超时时间: 60秒")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 检查是否有文件被选中
                file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                for file_input in file_inputs:
                    if file_input.get_attribute("value"):
                        selected_file = file_input.get_attribute("value")
                        print(f"✅ 检测到已选择文件: {selected_file}")
                        return True
                        
                time.sleep(1)  # 每秒检查一次
                
            except Exception as e:
                print(f"⚠️ 检查文件选择时出错: {e}")
                
        print("❌ 文件选择超时")
        return False
    
    def find_and_click_upload_button(self):
        """查找并点击上传按钮"""
        print("🔍 正在查找上传按钮...")
        
        try:
            # 常见的上传按钮选择器
            button_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('上传')",
                "button:contains('Upload')",
                "button:contains('提交')",
                ".upload-btn",
                "#upload-btn",
                "button.btn"
            ]
            
            for selector in button_selectors:
                try:
                    if ":contains" in selector:
                        # 使用XPath查找包含特定文本的按钮
                        text = selector.split("'")[1]
                        xpath = f"//button[contains(text(), '{text}')]"
                        buttons = self.driver.find_elements(By.XPATH, xpath)
                    else:
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if buttons:
                        button = buttons[0]
                        print(f"✅ 找到上传按钮: {selector}")
                        button.click()
                        print("🚀 上传按钮已点击!")
                        return True
                        
                except Exception as e:
                    continue
            
            # 如果没找到特定按钮，列出所有按钮让用户选择
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            if all_buttons:
                print("📋 页面中的所有按钮:")
                for i, btn in enumerate(all_buttons):
                    text = btn.text or btn.get_attribute("value") or f"按钮{i+1}"
                    print(f"  {i+1}. {text}")
                
                print("💡 请手动点击上传按钮，或按回车键继续...")
                input()
                return True
            
            print("❌ 未找到上传按钮")
            return False
            
        except Exception as e:
            print(f"❌ 查找上传按钮时出错: {e}")
            return False
    
    def wait_for_results(self, timeout=30):
        """等待识别结果"""
        print("⏳ 等待语音识别结果...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 查找可能包含结果的元素
                result_selectors = [
                    ".result",
                    "#result", 
                    ".transcription",
                    ".output",
                    "textarea",
                    ".recognition-result",
                    "#results"
                ]
                
                for selector in result_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text or element.get_attribute("value")
                        if text and len(text.strip()) > 0:
                            print(f"✅ 识别结果: {text}")
                            return True
                
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ 检查结果时出错: {e}")
                
        print("❌ 等待结果超时")
        return False
    
    def take_screenshot(self, filename="funasr_test_screenshot.png"):
        """截图保存"""
        try:
            self.driver.save_screenshot(filename)
            print(f"📸 截图已保存: {filename}")
            return True
        except Exception as e:
            print(f"❌ 截图失败: {e}")
            return False
    
    def run_test(self):
        """运行完整测试流程"""
        try:
            # 1. 设置浏览器
            self.setup_driver()
            
            # 2. 选择要测试的页面
            page_type = self.select_page_to_test()
            if page_type is None:
                return False
            
            # 3. 打开页面
            success, selected_page = self.open_funasr_page(page_type)
            if not success:
                return False
            
            # 4. 检查页面元素
            if not self.check_page_elements(selected_page):
                return False
            
            # 5. 截图记录
            self.take_screenshot(f"funasr_page_{selected_page}_loaded.png")
            
            # 6. 根据页面类型执行不同的测试
            if selected_page == 4:  # 说话人管理API测试
                self.test_speaker_management_api()
                input("⏳ 请查看页面上的API测试结果，然后按回车键继续...")
            else:
                # 文件上传测试
                print("\n" + "="*50)
                print("🎯 现在可以在浏览器中进行文件上传测试!")
                print("📁 请选择一个音频文件进行上传")
                print("🔘 然后点击上传按钮")
                if selected_page == 2:
                    print("🎭 注意: 这是完整演示页面，可能包含音色关联功能")
                print("="*50 + "\n")
                
                # 保持浏览器打开，让用户手动操作
                input("⏳ 请在浏览器中完成文件上传操作，然后按回车键继续...")
                
                # 等待结果
                self.wait_for_results()
            
            # 7. 最终截图
            self.take_screenshot(f"funasr_test_result_{selected_page}.png")
            
            print("✅ 测试完成!")
            return True
            
        except Exception as e:
            print(f"❌ 测试过程中出错: {e}")
            return False
        
    def cleanup(self):
        """清理资源"""
        if self.driver:
            print("🧹 正在关闭浏览器...")
            self.driver.quit()
            print("✅ 浏览器已关闭")

def main():
    """主函数"""
    print("🎉 FunASR Web界面自动化测试工具")
    print("=" * 50)
    
    tester = FunASRWebTester()
    
    try:
        success = tester.run_test()
        if success:
            print("\n🎉 测试成功完成!")
        else:
            print("\n❌ 测试失败")
            
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main() 