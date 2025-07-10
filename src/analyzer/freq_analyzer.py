#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
频率分析器模块

该模块负责对职位描述进行传统词频统计分析，
使用NLP技术提取关键词并计算其频率。
"""

import re
import os
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Union, Tuple, Set
from collections import Counter

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# 导入配置
import sys
import os

# 获取项目根目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
# 将项目根目录添加到系统路径
if project_root not in sys.path:
    sys.path.append(project_root)

from config import TEXT_ANALYSIS_CONFIG

# 设置日志
logger = logging.getLogger(__name__)

class FrequencyAnalyzer:
    """频率分析器类，用于传统词频统计"""
    
    def __init__(self):
        """
        初始化频率分析器
        """
        # 下载NLTK资源（如果尚未下载）
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
            
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
        
        # 获取英文停用词
        self.stop_words = set(stopwords.words('english'))
        
        # 添加自定义停用词
        self.stop_words.update(TEXT_ANALYSIS_CONFIG['traditional']['custom_stop_words'] 
                              if 'custom_stop_words' in TEXT_ANALYSIS_CONFIG['traditional'] 
                              else [])
        
        # 加载技术关键词母表（如果有）
        self.tech_keywords = set()
        tech_keywords_file = TEXT_ANALYSIS_CONFIG['traditional'].get('tech_keywords_file')
        if tech_keywords_file and os.path.exists(tech_keywords_file):
            try:
                with open(tech_keywords_file, 'r', encoding='utf-8') as f:
                    self.tech_keywords = {line.strip().lower() for line in f if line.strip()}
                logger.info(f"加载了{len(self.tech_keywords)}个技术关键词")
            except Exception as e:
                logger.error(f"加载技术关键词文件时出错: {str(e)}")
        
        # 初始化向量化器
        self.count_vectorizer = CountVectorizer(
            stop_words=list(self.stop_words),
            ngram_range=TEXT_ANALYSIS_CONFIG['traditional']['ngram_range'],
            min_df=TEXT_ANALYSIS_CONFIG['traditional']['min_df'],
            max_df=TEXT_ANALYSIS_CONFIG['traditional']['max_df']
        )
        
        self.tfidf_vectorizer = TfidfVectorizer(
            stop_words=list(self.stop_words),
            ngram_range=TEXT_ANALYSIS_CONFIG['traditional']['ngram_range'],
            min_df=TEXT_ANALYSIS_CONFIG['traditional']['min_df'],
            max_df=TEXT_ANALYSIS_CONFIG['traditional']['max_df']
        )
        
        logger.info("频率分析器初始化完成")
    
    def preprocess_text(self, text: str) -> str:
        """
        预处理文本
        
        Args:
            text: 原始文本
        
        Returns:
            str: 预处理后的文本
        """
        if not text:
            return ""
        
        # 转换为小写
        text = text.lower()
        
        # 移除特殊字符，保留字母、数字和空格
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # 移除数字（可选，取决于是否需要保留版本号等信息）
        if TEXT_ANALYSIS_CONFIG['traditional'].get('remove_numbers', False):
            text = re.sub(r'\d+', '', text)
        
        # 分词
        tokens = word_tokenize(text)
        
        # 移除停用词
        tokens = [token for token in tokens if token not in self.stop_words]
        
        # 移除过短的词
        min_word_length = TEXT_ANALYSIS_CONFIG['traditional'].get('min_word_length', 2)
        tokens = [token for token in tokens if len(token) >= min_word_length]
        
        # 重新组合为文本
        return ' '.join(tokens)
    
    def extract_keywords(self, job_descriptions: List[str], top_n: int = 50) -> List[Dict[str, Any]]:
        """
        提取关键词
        
        Args:
            job_descriptions: 职位描述列表
            top_n: 返回前N个关键词
        
        Returns:
            List[Dict[str, Any]]: 关键词列表，包含关键词、频率和分数
        """
        try:
            # 预处理文本
            preprocessed_texts = [self.preprocess_text(text) for text in job_descriptions]
            
            # 使用CountVectorizer提取词频
            count_matrix = self.count_vectorizer.fit_transform(preprocessed_texts)
            
            # 获取特征名称（词语）
            feature_names = self.count_vectorizer.get_feature_names_out()
            
            # 计算总词频
            word_counts = count_matrix.sum(axis=0).A1
            
            # 创建词频字典
            word_freq = {feature_names[i]: int(word_counts[i]) for i in range(len(feature_names))}
            
            # 如果有技术关键词母表，优先保留母表中的词
            if self.tech_keywords:
                # 过滤关键词
                filtered_word_freq = {}
                for word, freq in word_freq.items():
                    # 检查单词或其小写形式是否在技术关键词母表中
                    word_lower = word.lower()
                    if word_lower in self.tech_keywords or any(tech_keyword in word_lower for tech_keyword in self.tech_keywords):
                        filtered_word_freq[word] = freq
                
                # 如果过滤后的词太少，则添加一些高频词
                if len(filtered_word_freq) < top_n:
                    # 按频率排序
                    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
                    # 添加高频词，直到达到top_n或用完所有词
                    for word, freq in sorted_words:
                        if word not in filtered_word_freq:
                            filtered_word_freq[word] = freq
                            if len(filtered_word_freq) >= top_n:
                                break
                
                word_freq = filtered_word_freq
            
            # 按频率排序并取前N个
            sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:top_n]
            
            # 转换为所需格式
            result = [
                {
                    "keyword": keyword,
                    "frequency": freq,
                    "score": float(freq)  # 使用频率作为分数
                }
                for keyword, freq in sorted_keywords
            ]
            
            logger.info(f"提取了{len(result)}个关键词")
            return result
            
        except Exception as e:
            logger.error(f"提取关键词时出错: {str(e)}")
            return []
    
    def analyze_jobs(self, jobs: List[Dict[str, Any]], top_n: int = 50) -> List[Dict[str, Any]]:
        """
        分析职位数据，提取关键词
        
        Args:
            jobs: 职位列表
            top_n: 返回前N个关键词
        
        Returns:
            List[Dict[str, Any]]: 关键词列表
        """
        try:
            # 提取职位描述
            job_descriptions = [job.get("job_description", "") for job in jobs if job.get("job_description")]
            
            # 提取关键词
            keywords = self.extract_keywords(job_descriptions, top_n)
            
            return keywords
            
        except Exception as e:
            logger.error(f"分析职位时出错: {str(e)}")
            return []