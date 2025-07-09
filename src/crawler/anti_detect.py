#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
反检测模块

该模块提供了一系列方法来增强Selenium的反检测能力，
帮助爬虫绕过LinkedIn的反爬虫机制。
"""

import random
import logging
from typing import Any

# Selenium相关
from selenium import webdriver
from selenium_stealth import stealth

# 设置日志
logger = logging.getLogger(__name__)

def setup_anti_detection(driver: Any) -> None:
    """
    设置Selenium反检测措施
    
    Args:
        driver: WebDriver实例
    """
    try:
        # 应用selenium-stealth
        stealth(
            driver,
            languages=["zh-CN", "zh", "en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        
        # 执行额外的反检测JavaScript
        apply_js_evasions(driver)
        
        logger.info("已应用反检测措施")
        
    except Exception as e:
        logger.error(f"应用反检测措施时出错: {str(e)}")

def apply_js_evasions(driver: Any) -> None:
    """
    应用JavaScript反检测脚本
    
    Args:
        driver: WebDriver实例
    """
    try:
        # 修改navigator属性以绕过检测
        driver.execute_script("""
        // 修改webdriver属性
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
        
        // 修改user-agent
        Object.defineProperty(navigator, 'userAgent', {
            get: () => window.navigator.userAgent.replace('Headless', ''),
        });
        
        // 添加Chrome特有的属性
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {},
        };
        
        // 添加语言和插件
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en'],
        });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: {
                        type: 'application/x-google-chrome-pdf',
                        suffixes: 'pdf',
                        description: 'Portable Document Format',
                        enabledPlugin: true,
                    },
                    name: 'Chrome PDF Plugin',
                    filename: 'internal-pdf-viewer',
                    description: 'Portable Document Format',
                    length: 1,
                },
                {
                    0: {
                        type: 'application/pdf',
                        suffixes: 'pdf',
                        description: 'Portable Document Format',
                        enabledPlugin: true,
                    },
                    name: 'Chrome PDF Viewer',
                    filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                    description: 'Portable Document Format',
                    length: 1,
                },
                {
                    0: {
                        type: 'application/x-nacl',
                        suffixes: '',
                        description: 'Native Client Executable',
                        enabledPlugin: true,
                    },
                    1: {
                        type: 'application/x-pnacl',
                        suffixes: '',
                        description: 'Portable Native Client Executable',
                        enabledPlugin: true,
                    },
                    name: 'Native Client',
                    filename: 'internal-nacl-plugin',
                    description: '',
                    length: 2,
                },
            ],
        });
        
        // 修改permissions API
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // 添加WebGL
        HTMLCanvasElement.prototype.getContext = (function(original) {
            return function(type) {
                if (type === 'webgl') {
                    const gl = original.apply(this, arguments);
                    gl.getParameter = function(parameter) {
                        // 伪造WebGL参数
                        if (parameter === 37445) {
                            return 'Intel Inc.';
                        }
                        if (parameter === 37446) {
                            return 'Intel Iris OpenGL Engine';
                        }
                        return original.apply(this, arguments);
                    };
                    return gl;
                }
                return original.apply(this, arguments);
            };
        })(HTMLCanvasElement.prototype.getContext);
        
        // 防止检测自动化控制
        window.navigator.hasOwnProperty = (function(original) {
            return function(property) {
                if (property === 'webdriver') {
                    return false;
                }
                return original.apply(this, arguments);
            };
        })(window.navigator.hasOwnProperty);
        
        // 修改屏幕分辨率
        Object.defineProperty(window.screen, 'width', {
            get: function() {
                return 1920;
            }
        });
        Object.defineProperty(window.screen, 'height', {
            get: function() {
                return 1080;
            }
        });
        Object.defineProperty(window.screen, 'availWidth', {
            get: function() {
                return 1920;
            }
        });
        Object.defineProperty(window.screen, 'availHeight', {
            get: function() {
                return 1050;
            }
        });
        Object.defineProperty(window.screen, 'colorDepth', {
            get: function() {
                return 24;
            }
        });
        Object.defineProperty(window.screen, 'pixelDepth', {
            get: function() {
                return 24;
            }
        });
        
        // 修改Canvas指纹
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            if (this.width === 0 && this.height === 0) {
                return originalToDataURL.apply(this, arguments);
            }
            
            const canvas = this.cloneNode(true);
            const ctx = canvas.getContext('2d');
            
            // 添加微小的随机噪点
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const data = imageData.data;
            for (let i = 0; i < data.length; i += 4) {
                // 只修改一小部分像素，避免明显变化
                if (Math.random() < 0.005) {
                    data[i] = data[i] + Math.floor(Math.random() * 2);     // R
                    data[i+1] = data[i+1] + Math.floor(Math.random() * 2); // G
                    data[i+2] = data[i+2] + Math.floor(Math.random() * 2); // B
                }
            }
            ctx.putImageData(imageData, 0, 0);
            
            return canvas.toDataURL(type);
        };
        
        // 修改AudioContext指纹
        const audioContextProto = window.AudioContext || window.webkitAudioContext;
        if (audioContextProto) {
            const originalGetChannelData = AudioBuffer.prototype.getChannelData;
            AudioBuffer.prototype.getChannelData = function() {
                const result = originalGetChannelData.apply(this, arguments);
                // 只修改一小部分样本
                if (result.length > 0) {
                    const random = Math.random() * 0.0001;
                    // 只修改少量样本点
                    const sampleCount = Math.floor(result.length * 0.001);
                    for (let i = 0; i < sampleCount; i++) {
                        const index = Math.floor(Math.random() * result.length);
                        result[index] = result[index] + random;
                    }
                }
                return result;
            };
        }
        
        // 防止检测Selenium特有的属性
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """)
        
        logger.info("已应用JavaScript反检测脚本")
        
    except Exception as e:
        logger.error(f"应用JavaScript反检测脚本时出错: {str(e)}")

def randomize_mouse_movements(driver: Any) -> None:
    """
    随机化鼠标移动以模拟人类行为
    
    Args:
        driver: WebDriver实例
    """
    try:
        # 获取窗口大小
        window_size = driver.get_window_size()
        width = window_size['width']
        height = window_size['height']
        
        # 生成随机坐标
        x = random.randint(0, width)
        y = random.randint(0, height)
        
        # 执行鼠标移动脚本
        driver.execute_script(f"""
        const event = new MouseEvent('mousemove', {{
            'view': window,
            'bubbles': true,
            'cancelable': true,
            'clientX': {x},
            'clientY': {y}
        }});
        document.dispatchEvent(event);
        """)
        
    except Exception as e:
        logger.error(f"随机化鼠标移动时出错: {str(e)}")

def add_random_scrolling(driver: Any) -> None:
    """
    添加随机滚动以模拟人类行为
    
    Args:
        driver: WebDriver实例
    """
    try:
        # 生成随机滚动距离
        scroll_y = random.randint(100, 300)
        
        # 执行滚动脚本
        driver.execute_script(f"window.scrollBy(0, {scroll_y});")
        
    except Exception as e:
        logger.error(f"添加随机滚动时出错: {str(e)}")

# 测试代码
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建测试WebDriver
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    
    try:
        # 应用反检测措施
        setup_anti_detection(driver)
        
        # 访问测试页面
        driver.get("https://bot.sannysoft.com/")
        
        # 等待检查结果
        import time
        time.sleep(5)
        
        # 保存截图
        driver.save_screenshot("anti_detect_test.png")
        logger.info("测试完成，请查看截图检查反检测效果")
        
    finally:
        # 关闭WebDriver
        driver.quit()