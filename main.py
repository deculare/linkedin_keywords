#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LinkedIn关键词分析系统 - 主程序

该脚本是项目的主入口点，整合了爬虫、分析和可视化模块，
提供命令行接口来执行完整的数据收集和分析流程。
"""

import os
import sys
import argparse
import logging
import time
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入配置和模块
from config import LINKEDIN_CONFIG, GEMINI_CONFIG, TEXT_ANALYSIS_CONFIG, LOGGING_CONFIG
from config import RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUT_DIR, EXCEL_OUTPUT_DIR, VISUALIZATION_DIR

# 导入项目模块
from src.crawler.linkedin_crawler import LinkedInCrawler
from src.processor.excel_handler import ExcelHandler
from src.analyzer.llm_extractor import GeminiExtractor
from src.analyzer.freq_analyzer import FrequencyAnalyzer
from src.analyzer.hybrid_analyzer import HybridAnalyzer
from src.visualizer.heatmap import HeatmapGenerator
from src.visualizer.wordcloud import WordCloudGenerator

# 设置日志
def setup_logging():
    """
    配置日志系统
    """
    log_dir = os.path.dirname(LOGGING_CONFIG['file'])
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, LOGGING_CONFIG['level']),
        format=LOGGING_CONFIG['format'],
        handlers=[
            logging.FileHandler(LOGGING_CONFIG['file']),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# 解析命令行参数
def parse_args():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(description='LinkedIn关键词分析系统')
    
    # 主要操作模式
    parser.add_argument('--mode', type=str, default='all',
                        choices=['crawl', 'analyze', 'visualize', 'all'],
                        help='运行模式: 爬取(crawl), 分析(analyze), 可视化(visualize), 或全部(all)')
    
    # 爬虫参数
    parser.add_argument('--keywords', type=str, nargs='+',
                        help='要搜索的关键词列表，用空格分隔')
    parser.add_argument('--locations', type=str, nargs='+',
                        help='要搜索的地区列表，用空格分隔')
    parser.add_argument('--pages', type=int,
                        help='每个搜索组合爬取的页数')
    parser.add_argument('--headless', action='store_true',
                        help='使用无头模式运行浏览器')
    parser.add_argument('--use-proxy', action='store_true',
                        help='使用代理')
    
    # 分析参数
    parser.add_argument('--input-file', type=str,
                        help='要分析的Excel文件路径')
    parser.add_argument('--llm-weight', type=float,
                        help='LLM结果权重')
    parser.add_argument('--top-n', type=int,
                        help='保留前N个关键词')
    
    # 可视化参数
    parser.add_argument('--no-wordcloud', action='store_true',
                        help='不生成词云')
    parser.add_argument('--no-heatmap', action='store_true',
                        help='不生成热力图')
    
    # 其他参数
    parser.add_argument('--output-prefix', type=str,
                        help='输出文件前缀')
    parser.add_argument('--debug', action='store_true',
                        help='启用调试模式')
    
    return parser.parse_args()

# 更新配置
def update_config(args):
    """
    根据命令行参数更新配置
    """
    # 更新LinkedIn爬虫配置
    if args.keywords:
        LINKEDIN_CONFIG['search']['keywords'] = args.keywords
    if args.locations:
        LINKEDIN_CONFIG['search']['locations'] = args.locations
    if args.pages:
        LINKEDIN_CONFIG['search']['pages_per_search'] = args.pages
    if args.headless:
        LINKEDIN_CONFIG['crawler']['headless'] = True
    if args.use_proxy:
        LINKEDIN_CONFIG['crawler']['use_proxy'] = True
    
    # 更新分析配置
    if args.llm_weight:
        TEXT_ANALYSIS_CONFIG['hybrid']['llm_weight'] = args.llm_weight
    if args.top_n:
        TEXT_ANALYSIS_CONFIG['hybrid']['top_n'] = args.top_n
    
    # 更新日志级别
    if args.debug:
        LOGGING_CONFIG['level'] = 'DEBUG'

# 主函数
def main():
    """
    主程序入口
    """
    # 解析命令行参数
    args = parse_args()
    
    # 更新配置
    update_config(args)
    
    # 设置日志
    logger = setup_logging()
    logger.info("启动LinkedIn关键词分析系统")
    
    # 生成时间戳和输出前缀
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_prefix = args.output_prefix or f"linkedin_{timestamp}"
    
    # 确保目录存在
    for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUT_DIR, EXCEL_OUTPUT_DIR, VISUALIZATION_DIR]:
        os.makedirs(directory, exist_ok=True)
    
    # 定义输出文件路径
    raw_excel_path = os.path.join(RAW_DATA_DIR, f"{output_prefix}_raw.xlsx")
    processed_excel_path = os.path.join(PROCESSED_DATA_DIR, f"{output_prefix}_processed.xlsx")
    keywords_excel_path = os.path.join(EXCEL_OUTPUT_DIR, f"{output_prefix}_keywords.xlsx")
    
    try:
        # 爬取数据
        if args.mode in ['crawl', 'all']:
            logger.info("开始爬取LinkedIn职位数据")
            crawler = LinkedInCrawler(LINKEDIN_CONFIG)
            job_data = crawler.run()
            
            # 保存原始数据
            excel_handler = ExcelHandler()
            excel_handler.save_to_excel(job_data, raw_excel_path)
            logger.info(f"原始数据已保存到: {raw_excel_path}")
        
        # 分析数据
        if args.mode in ['analyze', 'all']:
            logger.info("开始分析职位数据")
            
            # 如果不是从爬虫阶段开始，则加载指定的Excel文件
            if args.mode != 'all' and args.input_file:
                raw_excel_path = args.input_file
            
            # 加载数据
            excel_handler = ExcelHandler()
            job_data = excel_handler.load_from_excel(raw_excel_path)
            
            # LLM抽取
            logger.info("使用Gemini进行职位摘要和技能抽取")
            gemini_extractor = GeminiExtractor(GEMINI_CONFIG)
            job_data_with_llm = gemini_extractor.process_jobs(job_data)
            
            # 保存处理后的数据
            excel_handler.save_to_excel(job_data_with_llm, processed_excel_path)
            logger.info(f"处理后的数据已保存到: {processed_excel_path}")
            
            # 传统词频分析
            logger.info("执行传统词频分析")
            freq_analyzer = FrequencyAnalyzer(TEXT_ANALYSIS_CONFIG['traditional'])
            traditional_keywords = freq_analyzer.analyze(job_data_with_llm)
            
            # 混合分析
            logger.info("执行混合关键词分析")
            hybrid_analyzer = HybridAnalyzer(TEXT_ANALYSIS_CONFIG['hybrid'])
            keyword_results = hybrid_analyzer.analyze(job_data_with_llm, traditional_keywords)
            
            # 保存关键词结果
            excel_handler.save_keywords_to_excel(keyword_results, keywords_excel_path)
            logger.info(f"关键词分析结果已保存到: {keywords_excel_path}")
        
        # 可视化
        if args.mode in ['visualize', 'all']:
            logger.info("生成可视化图表")
            
            # 如果不是从分析阶段开始，则加载指定的Excel文件
            if args.mode == 'visualize' and args.input_file:
                keywords_excel_path = args.input_file
            
            # 加载关键词数据
            excel_handler = ExcelHandler()
            keyword_data = excel_handler.load_keywords_from_excel(keywords_excel_path)
            
            # 生成热力图
            if not args.no_heatmap:
                logger.info("生成热力图")
                heatmap_generator = HeatmapGenerator()
                heatmap_path = os.path.join(VISUALIZATION_DIR, f"{output_prefix}_heatmap")
                heatmap_generator.generate(keyword_data, heatmap_path)
            
            # 生成词云
            if not args.no_wordcloud:
                logger.info("生成词云")
                wordcloud_generator = WordCloudGenerator()
                wordcloud_path = os.path.join(VISUALIZATION_DIR, f"{output_prefix}_wordcloud")
                wordcloud_generator.generate(keyword_data, wordcloud_path)
        
        logger.info("LinkedIn关键词分析系统执行完成")
        
    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())