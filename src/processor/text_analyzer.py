#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文本分析模块

该模块负责对职位描述进行文本分析，包括传统词频统计和与LLM结果的混合分析，
以生成关键词频率表和相关统计数据。
"""

import re
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

class TextAnalyzer:
    """文本分析类，用于传统词频统计和混合分析"""
    
    def __init__(self):
        """
        初始化文本分析器
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
        self.stop_words.update(TEXT_ANALYSIS_CONFIG['custom_stop_words'])
        
        # 加载技术关键词母表（如果有）
        self.tech_keywords = set()
        if TEXT_ANALYSIS_CONFIG['tech_keywords_file'] and os.path.exists(TEXT_ANALYSIS_CONFIG['tech_keywords_file']):
            try:
                with open(TEXT_ANALYSIS_CONFIG['tech_keywords_file'], 'r', encoding='utf-8') as f:
                    self.tech_keywords = {line.strip().lower() for line in f if line.strip()}
                logger.info(f"加载了{len(self.tech_keywords)}个技术关键词")
            except Exception as e:
                logger.error(f"加载技术关键词文件时出错: {str(e)}")
        
        # 初始化向量化器
        self.count_vectorizer = CountVectorizer(
            stop_words=list(self.stop_words),
            ngram_range=(1, 2),  # 支持单词和双词组合
            min_df=TEXT_ANALYSIS_CONFIG['min_document_frequency'],
            max_df=TEXT_ANALYSIS_CONFIG['max_document_frequency']
        )
        
        self.tfidf_vectorizer = TfidfVectorizer(
            stop_words=list(self.stop_words),
            ngram_range=(1, 2),  # 支持单词和双词组合
            min_df=TEXT_ANALYSIS_CONFIG['min_document_frequency'],
            max_df=TEXT_ANALYSIS_CONFIG['max_document_frequency']
        )
        
        logger.info("文本分析器初始化完成")
    
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
        if TEXT_ANALYSIS_CONFIG['remove_numbers']:
            text = re.sub(r'\d+', '', text)
        
        # 分词
        tokens = word_tokenize(text)
        
        # 移除停用词
        tokens = [token for token in tokens if token not in self.stop_words]
        
        # 移除过短的词
        tokens = [token for token in tokens if len(token) >= TEXT_ANALYSIS_CONFIG['min_word_length']]
        
        # 重新组合为文本
        return ' '.join(tokens)
    
    def extract_traditional_keywords(self, job_descriptions: List[str], top_n: int = 50) -> List[Dict[str, Any]]:
        """
        使用传统方法提取关键词
        
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
            
            logger.info(f"使用传统方法提取了{len(result)}个关键词")
            return result
            
        except Exception as e:
            logger.error(f"使用传统方法提取关键词时出错: {str(e)}")
            return []
    
    def extract_llm_keywords(self, jobs: List[Dict[str, Any]], top_n: int = 50) -> List[Dict[str, Any]]:
        """
        从LLM提取的技能中统计关键词
        
        Args:
            jobs: 职位列表，每个职位包含skills字段
            top_n: 返回前N个关键词
        
        Returns:
            List[Dict[str, Any]]: 关键词列表，包含关键词、频率和分数
        """
        try:
            # 收集所有技能
            all_skills = []
            for job in jobs:
                skills = job.get("skills", [])
                if skills and isinstance(skills, list):
                    all_skills.extend([skill.lower() for skill in skills if skill])
            
            # 统计技能频率
            skill_counter = Counter(all_skills)
            
            # 按频率排序并取前N个
            top_skills = skill_counter.most_common(top_n)
            
            # 转换为所需格式
            result = [
                {
                    "keyword": skill,
                    "frequency": freq,
                    "score": float(freq)  # 使用频率作为分数
                }
                for skill, freq in top_skills
            ]
            
            logger.info(f"从LLM结果中提取了{len(result)}个关键词")
            return result
            
        except Exception as e:
            logger.error(f"从LLM结果中提取关键词时出错: {str(e)}")
            return []
    
    def combine_keywords(self, traditional_keywords: List[Dict[str, Any]], 
                        llm_keywords: List[Dict[str, Any]], 
                        llm_weight: float = 1.5, 
                        traditional_weight: float = 1.0,
                        top_n: int = 50) -> List[Dict[str, Any]]:
        """
        融合传统关键词和LLM关键词
        
        Args:
            traditional_keywords: 传统方法提取的关键词
            llm_keywords: LLM提取的关键词
            llm_weight: LLM关键词权重
            traditional_weight: 传统关键词权重
            top_n: 返回前N个关键词
        
        Returns:
            List[Dict[str, Any]]: 融合后的关键词列表
        """
        try:
            # 创建关键词字典
            keyword_dict = {}
            
            # 添加传统关键词
            for item in traditional_keywords:
                keyword = item["keyword"].lower()
                score = item["score"] * traditional_weight
                frequency = item["frequency"]
                
                keyword_dict[keyword] = {
                    "keyword": keyword,
                    "score": score,
                    "frequency": frequency,
                    "sources": ["traditional"]
                }
            
            # 添加LLM关键词
            for item in llm_keywords:
                keyword = item["keyword"].lower()
                score = item["score"] * llm_weight
                frequency = item["frequency"]
                
                if keyword in keyword_dict:
                    # 更新现有关键词
                    keyword_dict[keyword]["score"] += score
                    keyword_dict[keyword]["frequency"] += frequency
                    keyword_dict[keyword]["sources"].append("llm")
                else:
                    # 添加新关键词
                    keyword_dict[keyword] = {
                        "keyword": keyword,
                        "score": score,
                        "frequency": frequency,
                        "sources": ["llm"]
                    }
            
            # 按分数排序
            sorted_keywords = sorted(keyword_dict.values(), key=lambda x: x["score"], reverse=True)[:top_n]
            
            # 转换为所需格式
            result = [
                {
                    "keyword": item["keyword"],
                    "frequency": item["frequency"],
                    "score": item["score"],
                    "sources": ", ".join(item["sources"])
                }
                for item in sorted_keywords
            ]
            
            logger.info(f"融合了{len(result)}个关键词")
            return result
            
        except Exception as e:
            logger.error(f"融合关键词时出错: {str(e)}")
            return []
    
    def analyze_jobs(self, jobs: List[Dict[str, Any]], 
                    llm_weight: float = 1.5, 
                    traditional_weight: float = 1.0,
                    top_n: int = 50) -> Dict[str, Any]:
        """
        分析职位数据，提取关键词
        
        Args:
            jobs: 职位列表
            llm_weight: LLM关键词权重
            traditional_weight: 传统关键词权重
            top_n: 返回前N个关键词
        
        Returns:
            Dict[str, Any]: 分析结果，包含传统关键词、LLM关键词和混合关键词
        """
        try:
            # 提取职位描述
            job_descriptions = [job.get("job_description", "") for job in jobs if job.get("job_description")]
            
            # 使用传统方法提取关键词
            traditional_keywords = self.extract_traditional_keywords(job_descriptions, top_n)
            
            # 从LLM结果中提取关键词
            llm_keywords = self.extract_llm_keywords(jobs, top_n)
            
            # 融合关键词
            hybrid_keywords = self.combine_keywords(
                traditional_keywords, 
                llm_keywords, 
                llm_weight, 
                traditional_weight,
                top_n
            )
            
            # 提取职位摘要
            job_summaries = [
                {
                    "job_id": job.get("job_id", ""),
                    "job_title": job.get("job_title", ""),
                    "company": job.get("company", ""),
                    "summary": job.get("summary", "")
                }
                for job in jobs if job.get("summary")
            ]
            
            # 创建元数据
            metadata = {
                "total_jobs": len(jobs),
                "analyzed_jobs": len(job_descriptions),
                "llm_weight": llm_weight,
                "traditional_weight": traditional_weight,
                "top_n": top_n,
                "analysis_time": self._get_current_time()
            }
            
            # 返回结果
            result = {
                "traditional_keywords": traditional_keywords,
                "llm_keywords": llm_keywords,
                "hybrid_keywords": hybrid_keywords,
                "job_summaries": job_summaries,
                "metadata": metadata
            }
            
            logger.info(f"成功分析{len(jobs)}个职位")
            return result
            
        except Exception as e:
            logger.error(f"分析职位时出错: {str(e)}")
            return {}
    
    def _get_current_time(self) -> str:
        """
        获取当前时间字符串
        
        Returns:
            str: 当前时间字符串
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 测试代码
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建测试数据
    test_jobs = [
        {
            "job_id": "test1",
            "job_title": "Senior Python Developer",
            "company": "Test Company",
            "job_description": """
            We are looking for a Senior Python Developer to join our team. 
            The ideal candidate will have 5+ years of experience with Python, 
            Django, Flask, and RESTful APIs. Experience with AWS, Docker, and 
            Kubernetes is a plus. You will be responsible for designing, 
            developing, and maintaining our backend services.
            
            Requirements:
            - 5+ years of experience with Python
            - Experience with Django and Flask
            - Experience with RESTful APIs
            - Experience with SQL and NoSQL databases
            - Experience with Git
            - Experience with AWS, Docker, and Kubernetes is a plus
            - Experience with CI/CD pipelines is a plus
            - Experience with Agile methodologies is a plus
            """,
            "skills": ["Python", "Django", "Flask", "RESTful APIs", "SQL", "NoSQL", "Git", "AWS", "Docker", "Kubernetes", "CI/CD", "Agile"]
        },
        {
            "job_id": "test2",
            "job_title": "Data Scientist",
            "company": "Another Company",
            "job_description": """
            We are seeking a Data Scientist to join our analytics team. 
            The ideal candidate will have a strong background in statistics, 
            machine learning, and data analysis. Experience with Python, R, 
            SQL, and big data technologies is required. You will be responsible 
            for developing and implementing data models and algorithms to solve 
            complex business problems.
            
            Requirements:
            - Master's or PhD in Statistics, Computer Science, or related field
            - 3+ years of experience in data science or related field
            - Proficiency in Python, R, and SQL
            - Experience with machine learning frameworks such as TensorFlow, PyTorch, or scikit-learn
            - Experience with big data technologies such as Hadoop, Spark, or Hive
            - Strong communication and presentation skills
            """,
            "skills": ["Python", "R", "SQL", "Statistics", "Machine Learning", "TensorFlow", "PyTorch", "scikit-learn", "Hadoop", "Spark", "Hive"]
        }
    ]
    
    # 创建文本分析器
    analyzer = TextAnalyzer()
    
    # 测试分析职位
    result = analyzer.analyze_jobs(test_jobs)
    
    # 打印结果
    print("\n传统关键词:")
    for item in result["traditional_keywords"][:10]:
        print(f"{item['keyword']}: {item['frequency']}")
    
    print("\nLLM关键词:")
    for item in result["llm_keywords"][:10]:
        print(f"{item['keyword']}: {item['frequency']}")
    
    print("\n混合关键词:")
    for item in result["hybrid_keywords"][:10]:
        print(f"{item['keyword']}: {item['score']} ({item['sources']})")
    
    print("\n元数据:")
    for key, value in result["metadata"].items():
        print(f"{key}: {value}")