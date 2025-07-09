#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LinkedIn关键词分析系统 - Gradio交互界面

该脚本提供了一个基于Gradio的Web界面，允许用户通过浏览器交互式地使用
LinkedIn关键词分析系统的各项功能，包括爬取数据、分析和可视化。
"""

import os
import sys
import logging
import subprocess
import pandas as pd
import numpy as np
import gradio as gr
from datetime import datetime
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入配置和模块
from config import LINKEDIN_CONFIG, GEMINI_CONFIG, TEXT_ANALYSIS_CONFIG, GRADIO_CONFIG
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 启动frpc（如果配置为使用）
def install_frpc(port, frpconfigfile, use_frpc):
    if use_frpc:
        try:
            frpc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frpc")
            subprocess.run(['chmod', '+x', frpc_path], check=True)
            logger.info(f'正在启动frp，端口{port}')
            subprocess.Popen([frpc_path, '-c', frpconfigfile])
        except Exception as e:
            logger.error(f"启动frpc时出错: {str(e)}")

# 如果配置为使用frpc，则启动
if GRADIO_CONFIG.get("use_frpc", False):
    install_frpc(
        GRADIO_CONFIG.get("port", 7860),
        GRADIO_CONFIG.get("frpc_config_file", "7860.ini"),
        True
    )

# 辅助函数
def get_timestamp():
    """
    生成时间戳字符串
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def get_available_excel_files(directory):
    """
    获取指定目录中的所有Excel文件
    """
    files = []
    if os.path.exists(directory):
        for file in os.listdir(directory):
            if file.endswith(".xlsx") or file.endswith(".xls"):
                files.append(os.path.join(directory, file))
    return files

def get_available_visualization_files(directory, prefix=None, suffix=None):
    """
    获取指定目录中的可视化文件
    """
    files = []
    if os.path.exists(directory):
        for file in os.listdir(directory):
            if prefix and not file.startswith(prefix):
                continue
            if suffix and not file.endswith(suffix):
                continue
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                files.append(file_path)
    return files

# 爬虫功能
def crawl_linkedin(keywords, locations, pages_per_search, headless, use_proxy, output_prefix):
    """
    爬取LinkedIn职位数据
    """
    try:
        # 更新配置
        config = LINKEDIN_CONFIG.copy()
        config['search']['keywords'] = keywords.split(",") if isinstance(keywords, str) else keywords
        config['search']['locations'] = locations.split(",") if isinstance(locations, str) else locations
        config['search']['pages_per_search'] = int(pages_per_search)
        config['crawler']['headless'] = headless
        config['crawler']['use_proxy'] = use_proxy
        
        # 生成输出文件名
        timestamp = get_timestamp()
        prefix = output_prefix or f"linkedin_{timestamp}"
        raw_excel_path = os.path.join(RAW_DATA_DIR, f"{prefix}_raw.xlsx")
        
        # 确保目录存在
        os.makedirs(RAW_DATA_DIR, exist_ok=True)
        
        # 执行爬取
        crawler = LinkedInCrawler(config)
        job_data = crawler.run()
        
        # 保存数据
        excel_handler = ExcelHandler()
        excel_handler.save_to_excel(job_data, raw_excel_path)
        
        return f"爬取完成！共获取{len(job_data)}条职位数据，已保存到{raw_excel_path}", raw_excel_path
    
    except Exception as e:
        error_msg = f"爬取过程中发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg, None

# 分析功能
def analyze_data(input_file, llm_weight, traditional_weight, top_n, output_prefix):
    """
    分析职位数据，提取关键词
    """
    try:
        # 生成输出文件名
        timestamp = get_timestamp()
        prefix = output_prefix or f"linkedin_{timestamp}"
        processed_excel_path = os.path.join(PROCESSED_DATA_DIR, f"{prefix}_processed.xlsx")
        keywords_excel_path = os.path.join(EXCEL_OUTPUT_DIR, f"{prefix}_keywords.xlsx")
        
        # 确保目录存在
        for directory in [PROCESSED_DATA_DIR, EXCEL_OUTPUT_DIR]:
            os.makedirs(directory, exist_ok=True)
        
        # 加载数据
        excel_handler = ExcelHandler()
        job_data = excel_handler.load_from_excel(input_file)
        
        # 更新分析配置
        hybrid_config = TEXT_ANALYSIS_CONFIG['hybrid'].copy()
        hybrid_config['llm_weight'] = float(llm_weight)
        hybrid_config['traditional_weight'] = float(traditional_weight)
        hybrid_config['top_n'] = int(top_n)
        
        # LLM抽取
        gemini_extractor = GeminiExtractor(GEMINI_CONFIG)
        job_data_with_llm = gemini_extractor.process_jobs(job_data)
        
        # 保存处理后的数据
        excel_handler.save_to_excel(job_data_with_llm, processed_excel_path)
        
        # 传统词频分析
        freq_analyzer = FrequencyAnalyzer(TEXT_ANALYSIS_CONFIG['traditional'])
        traditional_keywords = freq_analyzer.analyze(job_data_with_llm)
        
        # 混合分析
        hybrid_analyzer = HybridAnalyzer(hybrid_config)
        keyword_results = hybrid_analyzer.analyze(job_data_with_llm, traditional_keywords)
        
        # 保存关键词结果
        excel_handler.save_keywords_to_excel(keyword_results, keywords_excel_path)
        
        return f"分析完成！处理了{len(job_data)}条职位数据，提取了{len(keyword_results)}个关键词。\n结果已保存到{keywords_excel_path}", keywords_excel_path
    
    except Exception as e:
        error_msg = f"分析过程中发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg, None

# 可视化功能
def generate_visualizations(input_file, generate_wordcloud, generate_heatmap, output_prefix):
    """
    生成可视化图表
    """
    try:
        # 生成输出文件名
        timestamp = get_timestamp()
        prefix = output_prefix or f"linkedin_{timestamp}"
        
        # 确保目录存在
        os.makedirs(VISUALIZATION_DIR, exist_ok=True)
        
        # 加载关键词数据
        excel_handler = ExcelHandler()
        keyword_data = excel_handler.load_keywords_from_excel(input_file)
        
        results = []
        output_files = []
        
        # 生成热力图
        if generate_heatmap:
            heatmap_generator = HeatmapGenerator()
            heatmap_path = os.path.join(VISUALIZATION_DIR, f"{prefix}_heatmap")
            heatmap_files = heatmap_generator.generate(keyword_data, heatmap_path)
            results.append(f"热力图已生成: {', '.join(heatmap_files)}")
            output_files.extend(heatmap_files)
        
        # 生成词云
        if generate_wordcloud:
            wordcloud_generator = WordCloudGenerator()
            wordcloud_path = os.path.join(VISUALIZATION_DIR, f"{prefix}_wordcloud")
            wordcloud_files = wordcloud_generator.generate(keyword_data, wordcloud_path)
            results.append(f"词云已生成: {', '.join(wordcloud_files)}")
            output_files.extend(wordcloud_files)
        
        return "\n".join(results), output_files
    
    except Exception as e:
        error_msg = f"可视化过程中发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg, []

# 创建Gradio界面
def create_interface():
    """
    创建Gradio交互界面
    """
    with gr.Blocks(title=GRADIO_CONFIG.get("title", "LinkedIn关键词分析系统")) as demo:
        gr.HTML(f"<h1 style='text-align: center'>{GRADIO_CONFIG.get('title', 'LinkedIn关键词分析系统')}</h1>")
        gr.HTML(f"<p style='text-align: center'>{GRADIO_CONFIG.get('description', '分析LinkedIn职位描述中的关键技能和趋势')}</p>")
        
        # 爬虫标签页
        with gr.Tab("1. 爬取LinkedIn数据"):
            with gr.Row():
                with gr.Column():
                    keywords_input = gr.Textbox(
                        label="搜索关键词",
                        placeholder="输入关键词，多个关键词用逗号分隔",
                        value="AI, Machine Learning, Data Science"
                    )
                    locations_input = gr.Textbox(
                        label="搜索地区",
                        placeholder="输入地区，多个地区用逗号分隔",
                        value="United States, China, Singapore"
                    )
                    pages_input = gr.Slider(
                        label="每个搜索组合爬取的页数",
                        minimum=1,
                        maximum=20,
                        value=5,
                        step=1
                    )
                with gr.Column():
                    headless_checkbox = gr.Checkbox(
                        label="无头模式（不显示浏览器界面）",
                        value=False
                    )
                    proxy_checkbox = gr.Checkbox(
                        label="使用代理",
                        value=False
                    )
                    output_prefix_input = gr.Textbox(
                        label="输出文件前缀（可选）",
                        placeholder="留空将使用时间戳作为前缀"
                    )
                    crawl_button = gr.Button("开始爬取")
            
            crawl_output = gr.Textbox(label="爬取结果")
            crawl_file_output = gr.Textbox(label="输出文件路径", visible=False)
        
        # 分析标签页
        with gr.Tab("2. 分析职位数据"):
            with gr.Row():
                with gr.Column():
                    input_file_dropdown = gr.Dropdown(
                        label="选择输入文件",
                        choices=get_available_excel_files(RAW_DATA_DIR),
                        interactive=True
                    )
                    refresh_input_button = gr.Button("刷新文件列表")
                    
                    def refresh_input_files():
                        return gr.Dropdown(choices=get_available_excel_files(RAW_DATA_DIR))
                    
                    refresh_input_button.click(
                        refresh_input_files,
                        outputs=[input_file_dropdown]
                    )
                    
                with gr.Column():
                    llm_weight_input = gr.Slider(
                        label="LLM结果权重",
                        minimum=0.5,
                        maximum=3.0,
                        value=1.5,
                        step=0.1
                    )
                    traditional_weight_input = gr.Slider(
                        label="传统词频权重",
                        minimum=0.5,
                        maximum=3.0,
                        value=1.0,
                        step=0.1
                    )
                    top_n_input = gr.Slider(
                        label="保留前N个关键词",
                        minimum=10,
                        maximum=200,
                        value=100,
                        step=10
                    )
                    analysis_prefix_input = gr.Textbox(
                        label="输出文件前缀（可选）",
                        placeholder="留空将使用时间戳作为前缀"
                    )
                    analyze_button = gr.Button("开始分析")
            
            analysis_output = gr.Textbox(label="分析结果")
            analysis_file_output = gr.Textbox(label="输出文件路径", visible=False)
        
        # 可视化标签页
        with gr.Tab("3. 生成可视化"):
            with gr.Row():
                with gr.Column():
                    viz_file_dropdown = gr.Dropdown(
                        label="选择关键词文件",
                        choices=get_available_excel_files(EXCEL_OUTPUT_DIR),
                        interactive=True
                    )
                    refresh_viz_button = gr.Button("刷新文件列表")
                    
                    def refresh_viz_files():
                        return gr.Dropdown(choices=get_available_excel_files(EXCEL_OUTPUT_DIR))
                    
                    refresh_viz_button.click(
                        refresh_viz_files,
                        outputs=[viz_file_dropdown]
                    )
                    
                with gr.Column():
                    wordcloud_checkbox = gr.Checkbox(
                        label="生成词云",
                        value=True
                    )
                    heatmap_checkbox = gr.Checkbox(
                        label="生成热力图",
                        value=True
                    )
                    viz_prefix_input = gr.Textbox(
                        label="输出文件前缀（可选）",
                        placeholder="留空将使用时间戳作为前缀"
                    )
                    visualize_button = gr.Button("生成可视化")
            
            viz_output = gr.Textbox(label="可视化结果")
            viz_gallery = gr.Gallery(label="可视化图表", show_label=True, columns=2, rows=2, height=600)
        
        # 查看结果标签页
        with gr.Tab("4. 查看结果"):
            with gr.Row():
                refresh_results_button = gr.Button("刷新结果文件")
            
            with gr.Row():
                with gr.Column():
                    gr.HTML("<h3>原始数据文件</h3>")
                    raw_files_dropdown = gr.Dropdown(
                        label="选择文件",
                        choices=get_available_excel_files(RAW_DATA_DIR),
                        interactive=True
                    )
                    view_raw_button = gr.Button("查看数据")
                
                with gr.Column():
                    gr.HTML("<h3>处理后的数据文件</h3>")
                    processed_files_dropdown = gr.Dropdown(
                        label="选择文件",
                        choices=get_available_excel_files(PROCESSED_DATA_DIR),
                        interactive=True
                    )
                    view_processed_button = gr.Button("查看数据")
                
                with gr.Column():
                    gr.HTML("<h3>关键词分析文件</h3>")
                    keywords_files_dropdown = gr.Dropdown(
                        label="选择文件",
                        choices=get_available_excel_files(EXCEL_OUTPUT_DIR),
                        interactive=True
                    )
                    view_keywords_button = gr.Button("查看数据")
            
            def refresh_result_files():
                raw_files = get_available_excel_files(RAW_DATA_DIR)
                processed_files = get_available_excel_files(PROCESSED_DATA_DIR)
                keywords_files = get_available_excel_files(EXCEL_OUTPUT_DIR)
                return raw_files, processed_files, keywords_files
            
            refresh_results_button.click(
                refresh_result_files,
                outputs=[raw_files_dropdown, processed_files_dropdown, keywords_files_dropdown]
            )
            
            with gr.Row():
                data_table = gr.Dataframe(label="数据预览", interactive=False)
            
            def load_excel_preview(file_path):
                if not file_path:
                    return pd.DataFrame()
                try:
                    df = pd.read_excel(file_path)
                    return df
                except Exception as e:
                    logger.error(f"加载Excel文件时出错: {str(e)}")
                    return pd.DataFrame({"错误": [f"加载文件时出错: {str(e)}"]})
            
            view_raw_button.click(
                load_excel_preview,
                inputs=[raw_files_dropdown],
                outputs=[data_table]
            )
            
            view_processed_button.click(
                load_excel_preview,
                inputs=[processed_files_dropdown],
                outputs=[data_table]
            )
            
            view_keywords_button.click(
                load_excel_preview,
                inputs=[keywords_files_dropdown],
                outputs=[data_table]
            )
        
        # 连接爬虫功能
        crawl_button.click(
            crawl_linkedin,
            inputs=[
                keywords_input,
                locations_input,
                pages_input,
                headless_checkbox,
                proxy_checkbox,
                output_prefix_input
            ],
            outputs=[crawl_output, crawl_file_output]
        )
        
        # 连接分析功能
        analyze_button.click(
            analyze_data,
            inputs=[
                input_file_dropdown,
                llm_weight_input,
                traditional_weight_input,
                top_n_input,
                analysis_prefix_input
            ],
            outputs=[analysis_output, analysis_file_output]
        )
        
        # 连接可视化功能
        visualize_button.click(
            generate_visualizations,
            inputs=[
                viz_file_dropdown,
                wordcloud_checkbox,
                heatmap_checkbox,
                viz_prefix_input
            ],
            outputs=[viz_output, viz_gallery]
        )
    
    return demo

# 主函数
def main():
    """
    主程序入口
    """
    # 确保目录存在
    for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUT_DIR, EXCEL_OUTPUT_DIR, VISUALIZATION_DIR]:
        os.makedirs(directory, exist_ok=True)
    
    # 创建并启动Gradio界面
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=GRADIO_CONFIG.get("port", 7860),
        share=GRADIO_CONFIG.get("share", True)
    )

if __name__ == "__main__":
    main()