#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志工具模块

该模块提供日志配置和管理功能，用于记录系统运行日志。
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from typing import Optional

# 导入配置
import sys
import os

# 获取项目根目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
# 将项目根目录添加到系统路径
if project_root not in sys.path:
    sys.path.append(project_root)

from config import LOG_CONFIG

def setup_logger(name: str = None, log_file: str = None, level: int = None) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称，如果为None则使用根记录器
        log_file: 日志文件路径，如果为None则使用配置中的默认路径
        level: 日志级别，如果为None则使用配置中的默认级别
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 使用配置中的默认值
    name = name or LOG_CONFIG['logger_name']
    level = level or getattr(logging, LOG_CONFIG['log_level'])
    
    # 如果未指定日志文件，使用配置中的默认路径
    if log_file is None:
        log_dir = os.path.join(project_root, LOG_CONFIG['log_dir'])
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, LOG_CONFIG['log_file'])
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 清除现有处理器
    if logger.handlers:
        logger.handlers.clear()
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # 创建文件处理器
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=LOG_CONFIG['max_bytes'],
        backupCount=LOG_CONFIG['backup_count'],
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    # 创建格式化器
    formatter = logging.Formatter(LOG_CONFIG['log_format'])
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称，如果为None则使用根记录器
    
    Returns:
        logging.Logger: 日志记录器
    """
    if name is None:
        return logging.getLogger(LOG_CONFIG['logger_name'])
    else:
        return logging.getLogger(name)

# 初始化根日志记录器
setup_logger()

# 测试代码
if __name__ == "__main__":
    # 获取日志记录器
    logger = get_logger()
    
    # 测试日志记录
    logger.debug("这是一条调试日志")
    logger.info("这是一条信息日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
    logger.critical("这是一条严重错误日志")
    
    # 测试自定义名称的日志记录器
    custom_logger = get_logger("custom")
    custom_logger.info("这是来自自定义日志记录器的日志")