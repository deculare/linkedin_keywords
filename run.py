#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
项目入口点

该脚本是LinkedIn关键词分析系统的入口点，用于启动整个系统。
可以选择运行爬虫、分析、可视化或Gradio界面。
"""

import os
import sys
import argparse
import logging
from typing import List, Dict, Any, Optional

# 将项目根目录添加到系统路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入配置和模块
from config import LINKEDIN_CONFIG, TEXT_ANALYSIS_CONFIG, VISUALIZATION_CONFIG, GRADIO_CONFIG
from src.utils.logger import setup_logger
from main import run_crawler, run_analysis, run_visualization, run_all
from app import run_app

# 设置日志
logger = setup_logger("run")

def parse_arguments():
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description="LinkedIn关键词分析系统")
    
    # 运行模式
    parser.add_argument("--mode", type=str, default="app", choices=["crawler", "analysis", "visualization", "all", "app"],
                        help="运行模式: crawler(爬虫), analysis(分析), visualization(可视化), all(全部), app(Gradio界面)")
    
    # 爬虫参数
    parser.add_argument("--keyword", type=str, help="搜索关键词")
    parser.add_argument("--location", type=str, help="搜索地区")
    parser.add_argument("--pages", type=int, help="爬取页数")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--proxy", type=str, help="代理地址")
    
    # 分析参数
    parser.add_argument("--input", type=str, help="输入文件路径")
    parser.add_argument("--llm-weight", type=float, help="LLM关键词权重")
    parser.add_argument("--top-n", type=int, help="Top N关键词")
    
    # 可视化参数
    parser.add_argument("--wordcloud", action="store_true", help="生成词云")
    parser.add_argument("--heatmap", action="store_true", help="生成热力图")
    
    # Gradio参数
    parser.add_argument("--share", action="store_true", help="共享Gradio界面")
    parser.add_argument("--port", type=int, help="Gradio端口")
    
    return parser.parse_args()

def main():
    """
    主函数
    """
    # 解析命令行参数
    args = parse_arguments()
    
    # 根据运行模式执行相应功能
    if args.mode == "crawler":
        # 更新爬虫配置
        crawler_config = LINKEDIN_CONFIG.copy()
        if args.keyword:
            crawler_config["search"]["keywords"] = [args.keyword]
        if args.location:
            crawler_config["search"]["locations"] = [args.location]
        if args.pages:
            crawler_config["search"]["pages_per_search"] = args.pages
        if args.headless is not None:
            crawler_config["crawler"]["headless"] = args.headless
        if args.proxy:
            crawler_config["crawler"]["proxy_list"] = [args.proxy]
            crawler_config["crawler"]["use_proxy"] = True
        
        # 运行爬虫
        run_crawler(crawler_config)
        
    elif args.mode == "analysis":
        # 更新分析配置
        analysis_config = TEXT_ANALYSIS_CONFIG.copy()
        if args.llm_weight:
            analysis_config["hybrid"]["llm_weight"] = args.llm_weight
        if args.top_n:
            analysis_config["hybrid"]["top_n"] = args.top_n
        
        # 运行分析
        input_file = args.input if args.input else None
        run_analysis(input_file, analysis_config)
        
    elif args.mode == "visualization":
        # 更新可视化配置
        vis_config = VISUALIZATION_CONFIG.copy()
        # 添加生成标志
        vis_config["generate_wordcloud"] = not args.no_wordcloud if args.wordcloud is None else args.wordcloud
        vis_config["generate_heatmap"] = not args.no_heatmap if args.heatmap is None else args.heatmap
        
        # 运行可视化
        input_file = args.input if args.input else None
        run_visualization(input_file, vis_config)
        
    elif args.mode == "all":
        # 更新所有配置
        crawler_config = LINKEDIN_CONFIG.copy()
        analysis_config = TEXT_ANALYSIS_CONFIG.copy()
        vis_config = VISUALIZATION_CONFIG.copy()
        
        # 爬虫配置
        if args.keyword:
            crawler_config["search"]["keywords"] = [args.keyword]
        if args.location:
            crawler_config["search"]["locations"] = [args.location]
        if args.pages:
            crawler_config["search"]["pages_per_search"] = args.pages
        if args.headless is not None:
            crawler_config["crawler"]["headless"] = args.headless
        if args.proxy:
            crawler_config["crawler"]["proxy_list"] = [args.proxy]
            crawler_config["crawler"]["use_proxy"] = True
        
        # 分析配置
        if args.llm_weight:
            analysis_config["hybrid"]["llm_weight"] = args.llm_weight
        if args.top_n:
            analysis_config["hybrid"]["top_n"] = args.top_n
        
        # 可视化配置
        # 添加生成标志
        vis_config["generate_wordcloud"] = not args.no_wordcloud if args.wordcloud is None else args.wordcloud
        vis_config["generate_heatmap"] = not args.no_heatmap if args.heatmap is None else args.heatmap
        
        # 运行全部
        run_all(crawler_config, analysis_config, vis_config)
        
    elif args.mode == "app":
        # 更新Gradio配置
        app_config = GRADIO_CONFIG.copy()
        if args.share is not None:
            app_config["share"] = args.share
        if args.port:
            app_config["port"] = args.port
        
        # 运行Gradio应用
        run_app(app_config)
    
    else:
        logger.error(f"未知的运行模式: {args.mode}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("用户中断，程序退出")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"程序运行出错: {str(e)}")
        sys.exit(1)