#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
混合分析器模块

该模块负责融合传统词频分析和LLM提取的关键词，
生成更全面的关键词分析结果。
"""

import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from collections import Counter

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

class HybridAnalyzer:
    """混合分析器类，用于融合传统词频分析和LLM提取的关键词"""
    
    def __init__(self):
        """
        初始化混合分析器
        """
        self.llm_weight = TEXT_ANALYSIS_CONFIG['hybrid']['llm_weight']
        self.traditional_weight = TEXT_ANALYSIS_CONFIG['hybrid']['traditional_weight']
        self.min_frequency = TEXT_ANALYSIS_CONFIG['hybrid'].get('min_frequency', 2)
        self.top_n = TEXT_ANALYSIS_CONFIG['hybrid'].get('top_n', 100)
        
        logger.info("混合分析器初始化完成")
    
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
                        llm_weight: float = None, 
                        traditional_weight: float = None,
                        top_n: int = None) -> List[Dict[str, Any]]:
        """
        融合传统关键词和LLM关键词
        
        Args:
            traditional_keywords: 传统方法提取的关键词
            llm_keywords: LLM提取的关键词
            llm_weight: LLM关键词权重，如果为None则使用配置值
            traditional_weight: 传统关键词权重，如果为None则使用配置值
            top_n: 返回前N个关键词，如果为None则使用配置值
        
        Returns:
            List[Dict[str, Any]]: 融合后的关键词列表
        """
        try:
            # 使用默认值或传入的参数
            llm_weight = llm_weight if llm_weight is not None else self.llm_weight
            traditional_weight = traditional_weight if traditional_weight is not None else self.traditional_weight
            top_n = top_n if top_n is not None else self.top_n
            
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
                    traditional_keywords: List[Dict[str, Any]],
                    llm_weight: float = None, 
                    traditional_weight: float = None,
                    top_n: int = None) -> List[Dict[str, Any]]:
        """
        分析职位数据，融合传统关键词和LLM关键词
        
        Args:
            jobs: 职位列表
            traditional_keywords: 传统方法提取的关键词
            llm_weight: LLM关键词权重，如果为None则使用配置值
            traditional_weight: 传统关键词权重，如果为None则使用配置值
            top_n: 返回前N个关键词，如果为None则使用配置值
        
        Returns:
            List[Dict[str, Any]]: 融合后的关键词列表
        """
        try:
            # 从LLM结果中提取关键词
            llm_keywords = self.extract_llm_keywords(jobs, top_n or self.top_n)
            
            # 融合关键词
            hybrid_keywords = self.combine_keywords(
                traditional_keywords, 
                llm_keywords, 
                llm_weight, 
                traditional_weight,
                top_n
            )
            
            return hybrid_keywords
            
        except Exception as e:
            logger.error(f"分析职位时出错: {str(e)}")
            return []