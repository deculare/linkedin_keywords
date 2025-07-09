#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
辅助函数模块

该模块提供各种辅助函数，用于简化常见操作。
"""

import os
import re
import time
import random
import string
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple

# 导入日志模块
from src.utils.logger import get_logger

# 设置日志
logger = get_logger(__name__)

def create_directories(directories: List[str]) -> None:
    """
    创建多个目录
    
    Args:
        directories: 目录路径列表
    """
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"创建目录: {directory}")
        except Exception as e:
            logger.error(f"创建目录时出错: {directory}, 错误: {str(e)}")

def get_timestamp() -> str:
    """
    获取当前时间戳字符串，格式：YYYYMMDD_HHMMSS
    
    Returns:
        str: 时间戳字符串
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def get_formatted_date() -> str:
    """
    获取格式化的日期字符串，格式：YYYY-MM-DD
    
    Returns:
        str: 日期字符串
    """
    return datetime.now().strftime("%Y-%m-%d")

def get_formatted_datetime() -> str:
    """
    获取格式化的日期时间字符串，格式：YYYY-MM-DD HH:MM:SS
    
    Returns:
        str: 日期时间字符串
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def generate_random_string(length: int = 8) -> str:
    """
    生成随机字符串
    
    Args:
        length: 字符串长度
    
    Returns:
        str: 随机字符串
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_id(prefix: str = "") -> str:
    """
    生成唯一ID
    
    Args:
        prefix: ID前缀
    
    Returns:
        str: 唯一ID
    """
    timestamp = int(time.time() * 1000)
    random_str = generate_random_string(4)
    return f"{prefix}{timestamp}_{random_str}"

def clean_filename(filename: str) -> str:
    """
    清理文件名，移除不允许的字符
    
    Args:
        filename: 原始文件名
    
    Returns:
        str: 清理后的文件名
    """
    # 移除不允许的字符
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", filename)
    # 移除前后空格
    cleaned = cleaned.strip()
    # 如果为空，使用默认名称
    if not cleaned:
        cleaned = f"file_{get_timestamp()}"
    return cleaned

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀
    
    Returns:
        str: 截断后的文本
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def md5_hash(text: str) -> str:
    """
    计算文本的MD5哈希值
    
    Args:
        text: 输入文本
    
    Returns:
        str: MD5哈希值
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def retry_function(func, max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0, 
                 exceptions: tuple = (Exception,), logger=None):
    """
    重试函数装饰器
    
    Args:
        func: 要重试的函数
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟时间的增长因子
        exceptions: 捕获的异常类型
        logger: 日志记录器
    
    Returns:
        函数的返回值
    """
    def wrapper(*args, **kwargs):
        mtries, mdelay = max_retries, delay
        while mtries > 0:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                msg = f"{func.__name__} 失败，剩余重试次数 {mtries-1}，错误: {str(e)}"
                if logger:
                    logger.warning(msg)
                else:
                    print(msg)
                    
                mtries -= 1
                if mtries == 0:
                    raise
                    
                time.sleep(mdelay)
                mdelay *= backoff
    return wrapper

def format_time_delta(seconds: float) -> str:
    """
    格式化时间差
    
    Args:
        seconds: 秒数
    
    Returns:
        str: 格式化的时间差字符串
    """
    if seconds < 60:
        return f"{seconds:.2f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.2f}小时"

def extract_domain(url: str) -> str:
    """
    从URL中提取域名
    
    Args:
        url: URL字符串
    
    Returns:
        str: 域名
    """
    if not url:
        return ""
        
    # 移除协议
    domain = re.sub(r'^https?://', '', url)
    # 移除路径和查询参数
    domain = domain.split('/', 1)[0]
    # 移除端口号
    domain = domain.split(':', 1)[0]
    
    return domain

def is_valid_url(url: str) -> bool:
    """
    检查URL是否有效
    
    Args:
        url: URL字符串
    
    Returns:
        bool: 是否有效
    """
    if not url:
        return False
        
    pattern = re.compile(
        r'^(?:http|https)://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'
        r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return bool(pattern.match(url))

# 测试代码
if __name__ == "__main__":
    # 测试创建目录
    create_directories(["test_dir", "test_dir/subdir"])
    
    # 测试时间戳
    print(f"时间戳: {get_timestamp()}")
    print(f"格式化日期: {get_formatted_date()}")
    print(f"格式化日期时间: {get_formatted_datetime()}")
    
    # 测试随机字符串
    print(f"随机字符串: {generate_random_string()}")
    print(f"唯一ID: {generate_id('test_')}")
    
    # 测试文件名清理
    print(f"清理文件名: {clean_filename('file*name?.txt')}")
    
    # 测试文本截断
    print(f"截断文本: {truncate_text('这是一段很长的文本，需要被截断', 10)}")
    
    # 测试MD5哈希
    print(f"MD5哈希: {md5_hash('test')}")
    
    # 测试重试函数
    @retry_function
    def test_retry():
        print("尝试执行...")
        raise ValueError("测试错误")
    
    try:
        test_retry()
    except ValueError:
        print("重试失败")
    
    # 测试时间差格式化
    print(f"30秒: {format_time_delta(30)}")
    print(f"300秒: {format_time_delta(300)}")
    print(f"3600秒: {format_time_delta(3600)}")
    
    # 测试URL处理
    print(f"提取域名: {extract_domain('https://www.example.com/path?query=1')}")
    print(f"URL有效性: {is_valid_url('https://www.example.com')}")
    print(f"URL有效性: {is_valid_url('invalid-url')}")
    
    # 清理测试目录
    import shutil
    if os.path.exists("test_dir"):
        shutil.rmtree("test_dir")