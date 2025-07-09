#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
可视化模块

该模块负责生成各种可视化图表，包括词云、热力图、条形图等，
用于展示关键词分析结果。
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Union, Tuple

# 可视化库
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud, STOPWORDS

# 导入配置
import sys
import os

# 获取项目根目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
# 将项目根目录添加到系统路径
if project_root not in sys.path:
    sys.path.append(project_root)

from config import VISUALIZATION_CONFIG

# 设置日志
logger = logging.getLogger(__name__)

# 设置Matplotlib中文字体（如果需要）
try:
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
except Exception as e:
    logger.warning(f"设置Matplotlib中文字体时出错: {str(e)}")

class Visualizer:
    """可视化类，用于生成各种可视化图表"""
    
    def __init__(self, output_dir: str = None):
        """
        初始化可视化器
        
        Args:
            output_dir: 输出目录，如果为None则使用当前目录
        """
        self.output_dir = output_dir or os.path.join(project_root, 'output', 'visualizations')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 设置颜色主题
        self.color_palette = VISUALIZATION_CONFIG['color_palette']
        
        # 设置图表尺寸
        self.figure_width = VISUALIZATION_CONFIG['figure_width']
        self.figure_height = VISUALIZATION_CONFIG['figure_height']
        
        # 设置DPI
        self.dpi = VISUALIZATION_CONFIG['dpi']
        
        logger.info(f"可视化器初始化完成，输出目录: {self.output_dir}")
    
    def generate_wordcloud(self, keywords: List[Dict[str, Any]], 
                          title: str = "关键词词云", 
                          filename: str = "wordcloud",
                          width: int = 800, 
                          height: int = 400,
                          max_words: int = 100,
                          background_color: str = "white") -> str:
        """
        生成词云图
        
        Args:
            keywords: 关键词列表，每个关键词包含keyword和score字段
            title: 图表标题
            filename: 输出文件名（不含扩展名）
            width: 图表宽度
            height: 图表高度
            max_words: 最大词数
            background_color: 背景颜色
        
        Returns:
            str: 保存的文件路径
        """
        try:
            # 创建词频字典
            word_freq = {item["keyword"]: item["score"] for item in keywords}
            
            # 创建词云对象
            wordcloud = WordCloud(
                width=width,
                height=height,
                background_color=background_color,
                max_words=max_words,
                colormap=self.color_palette,
                collocations=False,  # 避免重复词组
                stopwords=STOPWORDS
            ).generate_from_frequencies(word_freq)
            
            # 创建图表
            plt.figure(figsize=(self.figure_width, self.figure_height), dpi=self.dpi)
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis("off")
            plt.title(title, fontsize=16)
            plt.tight_layout()
            
            # 保存图表
            output_path = os.path.join(self.output_dir, f"{filename}.png")
            plt.savefig(output_path, dpi=self.dpi)
            plt.close()
            
            logger.info(f"成功生成词云图: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"生成词云图时出错: {str(e)}")
            return ""
    
    def generate_bar_chart(self, keywords: List[Dict[str, Any]], 
                          title: str = "关键词频率", 
                          filename: str = "bar_chart",
                          top_n: int = 20,
                          x_label: str = "关键词",
                          y_label: str = "频率",
                          use_plotly: bool = True) -> str:
        """
        生成条形图
        
        Args:
            keywords: 关键词列表，每个关键词包含keyword和frequency字段
            title: 图表标题
            filename: 输出文件名（不含扩展名）
            top_n: 显示前N个关键词
            x_label: X轴标签
            y_label: Y轴标签
            use_plotly: 是否使用Plotly生成交互式图表
        
        Returns:
            str: 保存的文件路径
        """
        try:
            # 取前N个关键词
            top_keywords = sorted(keywords, key=lambda x: x["frequency"], reverse=True)[:top_n]
            
            # 提取数据
            words = [item["keyword"] for item in top_keywords]
            freqs = [item["frequency"] for item in top_keywords]
            
            # 反转列表，使最高频的在顶部
            words.reverse()
            freqs.reverse()
            
            if use_plotly:
                # 使用Plotly创建交互式条形图
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=words,
                    x=freqs,
                    orientation='h',
                    marker=dict(color=freqs, colorscale=self.color_palette)
                ))
                
                fig.update_layout(
                    title=title,
                    xaxis_title=y_label,
                    yaxis_title=x_label,
                    height=max(400, len(words) * 20),  # 动态调整高度
                    width=self.figure_width * 100,
                    template="plotly_white"
                )
                
                # 保存为HTML
                output_path = os.path.join(self.output_dir, f"{filename}.html")
                fig.write_html(output_path)
                
                # 同时保存为图片
                img_path = os.path.join(self.output_dir, f"{filename}.png")
                fig.write_image(img_path)
                
            else:
                # 使用Matplotlib创建静态条形图
                plt.figure(figsize=(self.figure_width, self.figure_height), dpi=self.dpi)
                plt.barh(words, freqs, color=sns.color_palette(self.color_palette, len(words)))
                plt.xlabel(y_label)
                plt.ylabel(x_label)
                plt.title(title)
                plt.tight_layout()
                
                # 保存图表
                output_path = os.path.join(self.output_dir, f"{filename}.png")
                plt.savefig(output_path, dpi=self.dpi)
                plt.close()
            
            logger.info(f"成功生成条形图: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"生成条形图时出错: {str(e)}")
            return ""
    
    def generate_heatmap(self, jobs: List[Dict[str, Any]], 
                        keywords: List[Dict[str, Any]],
                        title: str = "职位-关键词热力图", 
                        filename: str = "heatmap",
                        top_n_jobs: int = 20,
                        top_n_keywords: int = 20,
                        use_plotly: bool = True) -> str:
        """
        生成热力图
        
        Args:
            jobs: 职位列表，每个职位包含job_title和skills字段
            keywords: 关键词列表，每个关键词包含keyword字段
            title: 图表标题
            filename: 输出文件名（不含扩展名）
            top_n_jobs: 显示前N个职位
            top_n_keywords: 显示前N个关键词
            use_plotly: 是否使用Plotly生成交互式图表
        
        Returns:
            str: 保存的文件路径
        """
        try:
            # 取前N个关键词
            top_keywords = [item["keyword"] for item in 
                          sorted(keywords, key=lambda x: x["frequency"], reverse=True)[:top_n_keywords]]
            
            # 取前N个职位
            top_jobs = jobs[:top_n_jobs]
            
            # 创建矩阵
            matrix = np.zeros((len(top_jobs), len(top_keywords)))
            
            # 填充矩阵
            for i, job in enumerate(top_jobs):
                job_skills = [skill.lower() for skill in job.get("skills", [])]
                job_desc = job.get("job_description", "").lower()
                
                for j, keyword in enumerate(top_keywords):
                    keyword_lower = keyword.lower()
                    # 检查关键词是否在技能列表中
                    if keyword_lower in job_skills:
                        matrix[i, j] = 1
                    # 检查关键词是否在职位描述中
                    elif keyword_lower in job_desc:
                        matrix[i, j] = 0.5
            
            # 提取职位标题
            job_titles = [f"{job.get('job_title', '')} ({job.get('company', '')})" for job in top_jobs]
            
            if use_plotly:
                # 使用Plotly创建交互式热力图
                fig = go.Figure(data=go.Heatmap(
                    z=matrix,
                    x=top_keywords,
                    y=job_titles,
                    colorscale=self.color_palette,
                    showscale=True
                ))
                
                fig.update_layout(
                    title=title,
                    xaxis_title="关键词",
                    yaxis_title="职位",
                    height=max(500, len(job_titles) * 25),  # 动态调整高度
                    width=max(700, len(top_keywords) * 40),  # 动态调整宽度
                    xaxis=dict(tickangle=-45),
                    template="plotly_white"
                )
                
                # 保存为HTML
                output_path = os.path.join(self.output_dir, f"{filename}.html")
                fig.write_html(output_path)
                
                # 同时保存为图片
                img_path = os.path.join(self.output_dir, f"{filename}.png")
                fig.write_image(img_path)
                
            else:
                # 使用Seaborn创建静态热力图
                plt.figure(figsize=(max(self.figure_width, len(top_keywords) * 0.4), 
                                   max(self.figure_height, len(job_titles) * 0.3)), 
                          dpi=self.dpi)
                
                sns.heatmap(matrix, annot=False, cmap=self.color_palette,
                          xticklabels=top_keywords, yticklabels=job_titles)
                
                plt.title(title)
                plt.xlabel("关键词")
                plt.ylabel("职位")
                plt.xticks(rotation=45, ha="right")
                plt.tight_layout()
                
                # 保存图表
                output_path = os.path.join(self.output_dir, f"{filename}.png")
                plt.savefig(output_path, dpi=self.dpi)
                plt.close()
            
            logger.info(f"成功生成热力图: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"生成热力图时出错: {str(e)}")
            return ""
    
    def generate_pie_chart(self, keywords: List[Dict[str, Any]], 
                         title: str = "关键词占比", 
                         filename: str = "pie_chart",
                         top_n: int = 10,
                         use_plotly: bool = True) -> str:
        """
        生成饼图
        
        Args:
            keywords: 关键词列表，每个关键词包含keyword和frequency字段
            title: 图表标题
            filename: 输出文件名（不含扩展名）
            top_n: 显示前N个关键词
            use_plotly: 是否使用Plotly生成交互式图表
        
        Returns:
            str: 保存的文件路径
        """
        try:
            # 取前N个关键词
            top_keywords = sorted(keywords, key=lambda x: x["frequency"], reverse=True)[:top_n]
            
            # 提取数据
            labels = [item["keyword"] for item in top_keywords]
            values = [item["frequency"] for item in top_keywords]
            
            if use_plotly:
                # 使用Plotly创建交互式饼图
                fig = go.Figure(data=[go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.3,  # 创建环形图
                    textinfo='label+percent',
                    insidetextorientation='radial',
                    marker=dict(colors=px.colors.qualitative.Plotly)
                )])
                
                fig.update_layout(
                    title=title,
                    height=self.figure_height * 100,
                    width=self.figure_width * 100,
                    template="plotly_white"
                )
                
                # 保存为HTML
                output_path = os.path.join(self.output_dir, f"{filename}.html")
                fig.write_html(output_path)
                
                # 同时保存为图片
                img_path = os.path.join(self.output_dir, f"{filename}.png")
                fig.write_image(img_path)
                
            else:
                # 使用Matplotlib创建静态饼图
                plt.figure(figsize=(self.figure_width, self.figure_height), dpi=self.dpi)
                plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90,
                      colors=sns.color_palette(self.color_palette, len(labels)))
                plt.axis('equal')  # 保持饼图为圆形
                plt.title(title)
                plt.tight_layout()
                
                # 保存图表
                output_path = os.path.join(self.output_dir, f"{filename}.png")
                plt.savefig(output_path, dpi=self.dpi)
                plt.close()
            
            logger.info(f"成功生成饼图: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"生成饼图时出错: {str(e)}")
            return ""
    
    def generate_all_visualizations(self, jobs: List[Dict[str, Any]], 
                                  keyword_data: Dict[str, Any],
                                  prefix: str = "") -> Dict[str, str]:
        """
        生成所有可视化图表
        
        Args:
            jobs: 职位列表
            keyword_data: 关键词数据，包含traditional_keywords、llm_keywords和hybrid_keywords
            prefix: 文件名前缀
        
        Returns:
            Dict[str, str]: 图表路径字典
        """
        try:
            result = {}
            
            # 添加前缀
            prefix = f"{prefix}_" if prefix else ""
            
            # 生成混合关键词词云
            if "hybrid_keywords" in keyword_data and keyword_data["hybrid_keywords"]:
                result["hybrid_wordcloud"] = self.generate_wordcloud(
                    keyword_data["hybrid_keywords"],
                    title="混合关键词词云",
                    filename=f"{prefix}hybrid_wordcloud"
                )
                
                result["hybrid_bar"] = self.generate_bar_chart(
                    keyword_data["hybrid_keywords"],
                    title="混合关键词频率",
                    filename=f"{prefix}hybrid_bar",
                    use_plotly=True
                )
            
            # 生成LLM关键词词云
            if "llm_keywords" in keyword_data and keyword_data["llm_keywords"]:
                result["llm_wordcloud"] = self.generate_wordcloud(
                    keyword_data["llm_keywords"],
                    title="LLM提取关键词词云",
                    filename=f"{prefix}llm_wordcloud"
                )
                
                result["llm_bar"] = self.generate_bar_chart(
                    keyword_data["llm_keywords"],
                    title="LLM提取关键词频率",
                    filename=f"{prefix}llm_bar",
                    use_plotly=True
                )
            
            # 生成传统关键词词云
            if "traditional_keywords" in keyword_data and keyword_data["traditional_keywords"]:
                result["traditional_wordcloud"] = self.generate_wordcloud(
                    keyword_data["traditional_keywords"],
                    title="传统方法关键词词云",
                    filename=f"{prefix}traditional_wordcloud"
                )
                
                result["traditional_bar"] = self.generate_bar_chart(
                    keyword_data["traditional_keywords"],
                    title="传统方法关键词频率",
                    filename=f"{prefix}traditional_bar",
                    use_plotly=True
                )
            
            # 生成热力图
            if "hybrid_keywords" in keyword_data and keyword_data["hybrid_keywords"] and jobs:
                result["heatmap"] = self.generate_heatmap(
                    jobs,
                    keyword_data["hybrid_keywords"],
                    title="职位-关键词热力图",
                    filename=f"{prefix}heatmap",
                    use_plotly=True
                )
            
            # 生成饼图
            if "hybrid_keywords" in keyword_data and keyword_data["hybrid_keywords"]:
                result["pie_chart"] = self.generate_pie_chart(
                    keyword_data["hybrid_keywords"],
                    title="关键词占比",
                    filename=f"{prefix}pie_chart",
                    use_plotly=True
                )
            
            logger.info(f"成功生成所有可视化图表，共{len(result)}个")
            return result
            
        except Exception as e:
            logger.error(f"生成所有可视化图表时出错: {str(e)}")
            return {}

# 测试代码
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建测试数据
    test_keywords = [
        {"keyword": "Python", "frequency": 15, "score": 22.5},
        {"keyword": "Machine Learning", "frequency": 12, "score": 18.0},
        {"keyword": "SQL", "frequency": 10, "score": 15.0},
        {"keyword": "Data Science", "frequency": 8, "score": 12.0},
        {"keyword": "TensorFlow", "frequency": 7, "score": 10.5},
        {"keyword": "PyTorch", "frequency": 6, "score": 9.0},
        {"keyword": "Pandas", "frequency": 5, "score": 7.5},
        {"keyword": "NumPy", "frequency": 5, "score": 7.5},
        {"keyword": "Scikit-learn", "frequency": 4, "score": 6.0},
        {"keyword": "Deep Learning", "frequency": 4, "score": 6.0},
        {"keyword": "NLP", "frequency": 3, "score": 4.5},
        {"keyword": "Computer Vision", "frequency": 3, "score": 4.5},
        {"keyword": "Big Data", "frequency": 3, "score": 4.5},
        {"keyword": "Spark", "frequency": 2, "score": 3.0},
        {"keyword": "Hadoop", "frequency": 2, "score": 3.0}
    ]
    
    test_jobs = [
        {
            "job_id": "test1",
            "job_title": "Senior Data Scientist",
            "company": "Test Company",
            "job_description": "Python, Machine Learning, SQL, TensorFlow",
            "skills": ["Python", "Machine Learning", "SQL", "TensorFlow"]
        },
        {
            "job_id": "test2",
            "job_title": "ML Engineer",
            "company": "Another Company",
            "job_description": "Python, PyTorch, Deep Learning, Computer Vision",
            "skills": ["Python", "PyTorch", "Deep Learning", "Computer Vision"]
        },
        {
            "job_id": "test3",
            "job_title": "Data Analyst",
            "company": "Third Company",
            "job_description": "SQL, Python, Pandas, Data Science",
            "skills": ["SQL", "Python", "Pandas", "Data Science"]
        }
    ]
    
    keyword_data = {
        "hybrid_keywords": test_keywords,
        "llm_keywords": test_keywords[:10],
        "traditional_keywords": test_keywords[5:]
    }
    
    # 创建可视化器
    visualizer = Visualizer()
    
    # 测试生成所有可视化图表
    result = visualizer.generate_all_visualizations(test_jobs, keyword_data, "test")
    
    # 打印结果
    for name, path in result.items():
        print(f"{name}: {path}")