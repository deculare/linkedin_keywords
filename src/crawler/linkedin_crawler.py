#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LinkedIn爬虫模块

该模块负责从LinkedIn网站爬取职位数据，使用Selenium和多种反爬技术
确保稳定抓取。支持按关键词和地区搜索，并提取职位详情。
"""

import os
import time
import json
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Selenium相关
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# 反爬相关
from selenium_stealth import stealth
from fake_useragent import UserAgent

# 可选的截图调试
try:
    from PIL import Image
    import pyautogui
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False

# 导入反检测模块
from .anti_detect import setup_anti_detection

# 设置日志
logger = logging.getLogger(__name__)

class LinkedInCrawler:
    """
    LinkedIn职位爬虫类
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化LinkedIn爬虫
        
        Args:
            config: 爬虫配置字典，包含搜索参数、爬虫行为控制等
        """
        self.config = config
        self.driver = None
        self.wait = None
        self.job_data = []
        
        # 创建截图目录
        if self.config['crawler'].get('save_screenshots', False):
            self.screenshot_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "logs" / "screenshots"
            os.makedirs(self.screenshot_dir, exist_ok=True)
    
    def setup_driver(self) -> None:
        """
        设置并初始化WebDriver
        """
        try:
            # 创建Chrome选项
            options = uc.ChromeOptions()
            
            # 设置窗口大小
            window_size = self.config['browser'].get('window_size', (1920, 1080))
            options.add_argument(f"--window-size={window_size[0]},{window_size[1]}")
            
            # 无头模式设置
            if self.config['crawler'].get('headless', False):
                options.add_argument("--headless")
            
            # 禁用图片加载（可选）
            if self.config['browser'].get('disable_images', False):
                options.add_argument('--blink-settings=imagesEnabled=false')
            
            # 禁用JavaScript（可选，但可能影响页面功能）
            if self.config['browser'].get('disable_javascript', False):
                options.add_argument('--disable-javascript')
            
            # 禁用扩展
            if self.config['browser'].get('disable_extensions', True):
                options.add_argument('--disable-extensions')
            
            # 随机User-Agent
            if self.config['crawler'].get('random_user_agent', True):
                ua = UserAgent()
                user_agent = ua.random
                options.add_argument(f'--user-agent={user_agent}')
            
            # 创建undetected_chromedriver实例
            self.driver = uc.Chrome(options=options)
            
            # 应用反检测措施
            setup_anti_detection(self.driver)
            
            # 设置页面加载超时
            self.driver.set_page_load_timeout(self.config['crawler'].get('page_load_timeout', 30))
            
            # 创建WebDriverWait实例
            self.wait = WebDriverWait(
                self.driver,
                timeout=10,
                poll_frequency=0.5,
                ignored_exceptions=[NoSuchElementException, StaleElementReferenceException]
            )
            
            logger.info("WebDriver初始化成功")
            
        except Exception as e:
            logger.error(f"WebDriver初始化失败: {str(e)}")
            raise
    
    def load_cookies(self) -> bool:
        """
        从文件加载Cookie
        
        Returns:
            bool: 是否成功加载Cookie
        """
        cookie_file = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / self.config['crawler'].get('cookie_file', 'linkedin_cookies.json')
        
        if not cookie_file.exists():
            logger.warning(f"Cookie文件不存在: {cookie_file}")
            return False
        
        try:
            # 首先访问LinkedIn域名，然后才能添加cookie
            self.driver.get("https://www.linkedin.com")
            self.random_delay(1, 2)
            
            # 加载并应用cookie
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                # 处理可能的cookie格式问题
                if 'expiry' in cookie:
                    cookie['expiry'] = int(cookie['expiry'])
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"添加cookie时出错: {str(e)}")
            
            # 刷新页面应用cookie
            self.driver.refresh()
            self.random_delay(2, 3)
            
            logger.info("成功加载Cookie")
            return True
            
        except Exception as e:
            logger.error(f"加载Cookie时出错: {str(e)}")
            return False
    
    def save_cookies(self) -> None:
        """
        保存Cookie到文件
        """
        try:
            cookie_file = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / self.config['crawler'].get('cookie_file', 'linkedin_cookies.json')
            cookies = self.driver.get_cookies()
            
            with open(cookie_file, 'w') as f:
                json.dump(cookies, f)
            
            logger.info(f"Cookie已保存到: {cookie_file}")
            
        except Exception as e:
            logger.error(f"保存Cookie时出错: {str(e)}")
    
    def login(self) -> bool:
        """
        登录LinkedIn
        
        Returns:
            bool: 是否成功登录
        """
        # 首先尝试使用Cookie登录
        if self.load_cookies():
            # 验证是否已登录
            if self.is_logged_in():
                logger.info("使用Cookie成功登录")
                return True
        
        # 如果Cookie登录失败且配置了使用账号密码
        if self.config['credentials'].get('use_credentials', False):
            try:
                email = self.config['credentials'].get('email', '')
                password = self.config['credentials'].get('password', '')
                
                if not email or not password:
                    logger.error("未提供有效的LinkedIn账号或密码")
                    return False
                
                # 访问登录页
                self.driver.get("https://www.linkedin.com/login")
                self.random_delay(2, 3)
                
                # 输入邮箱
                email_input = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
                self.type_like_human(email_input, email)
                
                # 输入密码
                password_input = self.wait.until(EC.presence_of_element_located((By.ID, "password")))
                self.type_like_human(password_input, password)
                
                # 点击登录按钮
                login_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
                login_button.click()
                
                # 等待登录完成
                self.random_delay(5, 8)
                
                # 验证是否登录成功
                if self.is_logged_in():
                    logger.info("使用账号密码成功登录")
                    # 保存Cookie以便下次使用
                    self.save_cookies()
                    return True
                else:
                    logger.error("登录失败，可能需要处理验证码或其他安全检查")
                    # 保存截图以便调试
                    self.take_screenshot("login_failed")
                    return False
                
            except Exception as e:
                logger.error(f"登录过程中出错: {str(e)}")
                self.take_screenshot("login_error")
                return False
        
        logger.warning("无法登录LinkedIn，将以未登录状态继续")
        return False
    
    def is_logged_in(self) -> bool:
        """
        检查是否已登录LinkedIn
        
        Returns:
            bool: 是否已登录
        """
        try:
            # 访问LinkedIn首页
            self.driver.get("https://www.linkedin.com/feed/")
            self.random_delay(2, 3)
            
            # 检查是否存在个人资料图标或其他登录状态元素
            profile_nav = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'profile-rail-card')]")
            nav_button = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'global-nav__primary-link')]")
            
            return len(profile_nav) > 0 or len(nav_button) > 0
            
        except Exception as e:
            logger.error(f"检查登录状态时出错: {str(e)}")
            return False
    
    def construct_search_url(self, keyword: str, location: str, page: int = 1) -> str:
        """
        构造LinkedIn职位搜索URL
        
        Args:
            keyword: 搜索关键词
            location: 搜索地区
            page: 页码
        
        Returns:
            str: 搜索URL
        """
        # 编码关键词和地区
        keyword_encoded = keyword.replace(' ', '%20')
        location_encoded = location.replace(' ', '%20')
        
        # 计算起始位置
        start = (page - 1) * 25
        
        # 构造基本URL
        base_url = "https://www.linkedin.com/jobs/search/"
        
        # 添加查询参数
        params = [
            f"keywords={keyword_encoded}",
            f"location={location_encoded}",
            "f_TPR=r86400",  # 最近24小时
            "geoId=92000000",  # 全球
            f"start={start}"
        ]
        
        # 组合URL
        url = f"{base_url}?{'&'.join(params)}"
        
        return url
    
    def scrape_job_listings(self, keyword: str, location: str, pages: int) -> List[Dict[str, Any]]:
        """
        抓取职位列表页
        
        Args:
            keyword: 搜索关键词
            location: 搜索地区
            pages: 要抓取的页数
        
        Returns:
            List[Dict[str, Any]]: 职位数据列表
        """
        job_listings = []
        
        try:
            for page in range(1, pages + 1):
                logger.info(f"正在抓取 '{keyword}' 在 '{location}' 的第 {page} 页")
                
                # 构造并访问搜索URL
                search_url = self.construct_search_url(keyword, location, page)
                self.driver.get(search_url)
                
                # 等待页面加载
                self.random_delay(3, 5)
                
                # 滚动页面以加载更多结果
                self.scroll_page()
                
                # 等待职位列表加载
                try:
                    job_list = self.wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".jobs-search__results-list")
                    ))
                    job_items = job_list.find_elements(By.TAG_NAME, "li")
                    
                    logger.info(f"找到 {len(job_items)} 个职位列表项")
                    
                    # 提取每个职位的基本信息
                    for job_item in job_items:
                        try:
                            # 提取职位链接和ID
                            job_link_elem = job_item.find_element(By.CSS_SELECTOR, "a.job-card-container__link")
                            job_link = job_link_elem.get_attribute("href")
                            job_id = self.extract_job_id(job_link)
                            
                            # 提取职位标题
                            job_title_elem = job_item.find_element(By.CSS_SELECTOR, "h3.job-card-container__title")
                            job_title = job_title_elem.text.strip()
                            
                            # 提取公司名称
                            company_elem = job_item.find_element(By.CSS_SELECTOR, "h4.job-card-container__company-name")
                            company = company_elem.text.strip()
                            
                            # 提取地点
                            location_elem = job_item.find_element(By.CSS_SELECTOR, ".job-card-container__metadata-item")
                            job_location = location_elem.text.strip()
                            
                            # 创建职位数据字典
                            job_data = {
                                "job_id": job_id,
                                "job_title": job_title,
                                "company": company,
                                "location": job_location,
                                "job_link": job_link,
                                "search_keyword": keyword,
                                "search_location": location,
                                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            job_listings.append(job_data)
                            
                        except Exception as e:
                            logger.warning(f"提取职位项时出错: {str(e)}")
                            continue
                    
                except TimeoutException:
                    logger.warning(f"等待职位列表超时，页面 {page}")
                    self.take_screenshot(f"timeout_page_{page}")
                    continue
                
                # 控制抓取频率
                if page < pages:
                    self.random_delay(5, 8)
        
        except Exception as e:
            logger.error(f"抓取职位列表时出错: {str(e)}")
            self.take_screenshot("job_listing_error")
        
        return job_listings
    
    def scrape_job_details(self, job_listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        抓取职位详情页
        
        Args:
            job_listings: 职位列表数据
        
        Returns:
            List[Dict[str, Any]]: 包含详情的职位数据列表
        """
        detailed_jobs = []
        
        for i, job in enumerate(job_listings):
            try:
                logger.info(f"正在抓取职位详情 [{i+1}/{len(job_listings)}]: {job['job_title']} at {job['company']}")
                
                # 访问职位详情页
                self.driver.get(job['job_link'])
                
                # 等待页面加载
                self.random_delay(3, 5)
                
                # 等待职位描述加载
                try:
                    job_description_elem = self.wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".jobs-description__content")
                    ))
                    
                    # 提取职位描述
                    job_description = job_description_elem.text.strip()
                    
                    # 尝试提取其他详细信息
                    job_details = {}
                    
                    # 工作类型（全职/兼职等）
                    try:
                        job_type_elems = self.driver.find_elements(
                            By.CSS_SELECTOR, ".jobs-unified-top-card__job-insight span"
                        )
                        if job_type_elems:
                            job_details['job_type'] = job_type_elems[0].text.strip()
                    except:
                        pass
                    
                    # 经验要求
                    try:
                        criteria_elems = self.driver.find_elements(
                            By.CSS_SELECTOR, ".jobs-unified-top-card__job-criteria-item"
                        )
                        for elem in criteria_elems:
                            label_elem = elem.find_element(By.CSS_SELECTOR, ".jobs-unified-top-card__job-criteria-subheader")
                            value_elem = elem.find_element(By.CSS_SELECTOR, ".jobs-unified-top-card__job-criteria-text")
                            
                            label = label_elem.text.strip().lower().replace(' ', '_')
                            value = value_elem.text.strip()
                            
                            job_details[label] = value
                    except:
                        pass
                    
                    # 更新职位数据
                    job_data = job.copy()
                    job_data['job_description'] = job_description
                    job_data.update(job_details)
                    
                    detailed_jobs.append(job_data)
                    
                except TimeoutException:
                    logger.warning(f"等待职位描述超时: {job['job_title']}")
                    self.take_screenshot(f"timeout_job_{i}")
                    
                    # 即使没有详情，也添加基本信息
                    job_data = job.copy()
                    job_data['job_description'] = "[抓取失败]"
                    detailed_jobs.append(job_data)
                
                # 控制抓取频率
                if i < len(job_listings) - 1:
                    self.random_delay(4, 7)
            
            except Exception as e:
                logger.error(f"抓取职位详情时出错: {str(e)}")
                self.take_screenshot(f"job_detail_error_{i}")
                
                # 即使出错，也添加基本信息
                job_data = job.copy()
                job_data['job_description'] = f"[抓取错误: {str(e)}]"
                detailed_jobs.append(job_data)
        
        return detailed_jobs
    
    def extract_job_id(self, job_url: str) -> str:
        """
        从职位URL中提取职位ID
        
        Args:
            job_url: 职位URL
        
        Returns:
            str: 职位ID
        """
        try:
            # 尝试从URL中提取ID
            if "currentJobId=" in job_url:
                job_id = job_url.split("currentJobId=")[1].split("&")[0]
            elif "/view/" in job_url:
                job_id = job_url.split("/view/")[1].split("/")[0]
            else:
                # 生成随机ID作为后备
                job_id = f"unknown_{int(time.time())}_{random.randint(1000, 9999)}"
            
            return job_id
            
        except Exception:
            # 生成随机ID作为后备
            return f"unknown_{int(time.time())}_{random.randint(1000, 9999)}"
    
    def scroll_page(self, max_scrolls: int = 5) -> None:
        """
        滚动页面以加载更多内容
        
        Args:
            max_scrolls: 最大滚动次数
        """
        try:
            scroll_pause_time = self.config['crawler'].get('scroll_pause_time', 1.5)
            
            for _ in range(max_scrolls):
                # 执行滚动
                self.driver.execute_script("window.scrollBy(0, 800);")
                
                # 添加随机鼠标移动（如果可用）
                if SCREENSHOT_AVAILABLE and random.random() < 0.3:
                    try:
                        screen_width, screen_height = pyautogui.size()
                        pyautogui.moveTo(
                            random.randint(100, screen_width - 100),
                            random.randint(100, screen_height - 100),
                            duration=0.5
                        )
                    except:
                        pass
                
                # 暂停以等待内容加载
                time.sleep(scroll_pause_time)
        
        except Exception as e:
            logger.warning(f"滚动页面时出错: {str(e)}")
    
    def type_like_human(self, element, text: str) -> None:
        """
        模拟人类输入文本
        
        Args:
            element: 要输入的元素
            text: 要输入的文本
        """
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
    
    def random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
        """
        随机延迟一段时间
        
        Args:
            min_seconds: 最小延迟秒数
            max_seconds: 最大延迟秒数
        """
        delay_time = random.uniform(min_seconds, max_seconds)
        time.sleep(delay_time)
    
    def take_screenshot(self, name: str) -> None:
        """
        保存屏幕截图
        
        Args:
            name: 截图名称
        """
        if not self.config['crawler'].get('save_screenshots', False):
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            self.driver.save_screenshot(filepath)
            logger.info(f"截图已保存: {filepath}")
            
        except Exception as e:
            logger.error(f"保存截图时出错: {str(e)}")
    
    def run(self) -> List[Dict[str, Any]]:
        """
        运行爬虫
        
        Returns:
            List[Dict[str, Any]]: 爬取的职位数据
        """
        try:
            # 设置WebDriver
            self.setup_driver()
            
            # 登录LinkedIn（可选）
            self.login()
            
            # 获取搜索参数
            keywords = self.config['search'].get('keywords', [])
            locations = self.config['search'].get('locations', [])
            pages_per_search = self.config['search'].get('pages_per_search', 5)
            
            all_job_listings = []
            
            # 对每个关键词和地区组合进行搜索
            for keyword in keywords:
                for location in locations:
                    logger.info(f"开始搜索关键词 '{keyword}' 在 '{location}'")
                    
                    # 抓取职位列表
                    job_listings = self.scrape_job_listings(keyword, location, pages_per_search)
                    logger.info(f"找到 {len(job_listings)} 个职位列表项")
                    
                    # 添加到总列表
                    all_job_listings.extend(job_listings)
                    
                    # 控制搜索频率
                    if keyword != keywords[-1] or location != locations[-1]:
                        self.random_delay(10, 15)
            
            logger.info(f"总共找到 {len(all_job_listings)} 个职位列表项")
            
            # 去重（基于job_id）
            unique_jobs = {}
            for job in all_job_listings:
                if job['job_id'] not in unique_jobs:
                    unique_jobs[job['job_id']] = job
            
            unique_job_listings = list(unique_jobs.values())
            logger.info(f"去重后剩余 {len(unique_job_listings)} 个职位")
            
            # 抓取职位详情
            detailed_jobs = self.scrape_job_details(unique_job_listings)
            
            # 保存结果
            self.job_data = detailed_jobs
            
            return detailed_jobs
            
        except Exception as e:
            logger.error(f"爬虫运行时出错: {str(e)}")
            raise
            
        finally:
            # 关闭WebDriver
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver已关闭")

# 测试代码
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 测试配置
    test_config = {
        "search": {
            "keywords": ["Python Developer"],
            "locations": ["United States"],
            "pages_per_search": 1
        },
        "crawler": {
            "headless": False,
            "page_load_timeout": 30,
            "delay_range": (2, 5),
            "scroll_pause_time": 1.5,
            "max_retries": 3,
            "use_proxy": False,
            "save_screenshots": True,
            "random_user_agent": True
        },
        "credentials": {
            "use_credentials": False
        },
        "browser": {
            "window_size": (1920, 1080),
            "disable_images": False,
            "disable_javascript": False,
            "disable_extensions": True
        }
    }
    
    # 创建并运行爬虫
    crawler = LinkedInCrawler(test_config)
    jobs = crawler.run()
    
    # 打印结果
    print(f"爬取了 {len(jobs)} 个职位")
    if jobs:
        print("示例职位:")
        print(f"标题: {jobs[0]['job_title']}")
        print(f"公司: {jobs[0]['company']}")
        print(f"地点: {jobs[0]['location']}")
        print(f"描述前100字符: {jobs[0]['job_description'][:100]}...")