#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LLM提取器模块

该模块负责调用Gemini API进行职位摘要和技能提取，
包括提示词构建、API调用、结果解析和错误处理。
"""

import os
import json
import logging
import time
from typing import List, Dict, Any, Optional, Union, Tuple

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic import BaseModel, Field, ValidationError

# 导入配置
import sys
import os

# 获取项目根目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
# 将项目根目录添加到系统路径
if project_root not in sys.path:
    sys.path.append(project_root)

from config import GEMINI_CONFIG, JOB_SUMMARY_PROMPT_TEMPLATE, SKILL_EXTRACTION_PROMPT_TEMPLATE

# 设置日志
logger = logging.getLogger(__name__)

# 定义输出模型
class JobAnalysisResult(BaseModel):
    """职位分析结果模型"""
    summary: str = Field(..., description="职位摘要")
    skills: List[str] = Field(..., description="技能列表")

class GeminiExtractor:
    """Gemini提取器类，用于调用Gemini API进行职位摘要和技能提取"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化Gemini提取器
        
        Args:
            api_key: Gemini API密钥，如果为None则使用配置文件中的密钥
        """
        self.api_key = api_key or GEMINI_CONFIG["api_key"]
        self.model = GEMINI_CONFIG["model"]
        self.temperature = GEMINI_CONFIG["temperature"]
        self.max_output_tokens = GEMINI_CONFIG["max_output_tokens"]
        self.top_p = GEMINI_CONFIG["top_p"]
        self.top_k = GEMINI_CONFIG["top_k"]
        
        # 初始化Gemini API
        genai.configure(api_key=self.api_key)
        
        # 获取模型
        self.model_instance = genai.GenerativeModel(
            model_name=self.model,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": self.max_output_tokens,
                "top_p": self.top_p,
                "top_k": self.top_k
            }
        )
        
        logger.info(f"Gemini提取器初始化完成，使用模型: {self.model}")
    
    @retry(stop=stop_after_attempt(GEMINI_CONFIG["retry_config"]["max_retries"]), 
           wait=wait_exponential(multiplier=1, min=GEMINI_CONFIG["retry_config"]["min_seconds"], 
                                max=GEMINI_CONFIG["retry_config"]["max_seconds"]))
    def _call_gemini_api(self, prompt: str) -> str:
        """
        调用Gemini API
        
        Args:
            prompt: 提示词
        
        Returns:
            str: API返回的文本
        """
        try:
            response = self.model_instance.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"调用Gemini API时出错: {str(e)}")
            raise
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析JSON响应
        
        Args:
            response_text: API返回的文本
        
        Returns:
            Dict[str, Any]: 解析后的JSON对象
        """
        try:
            # 尝试直接解析JSON
            return json.loads(response_text)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON部分
            try:
                # 查找第一个{和最后一个}
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx+1]
                    return json.loads(json_str)
                else:
                    raise ValueError("无法在响应中找到有效的JSON")
            except Exception as e:
                logger.error(f"解析JSON响应时出错: {str(e)}")
                raise ValueError(f"无法解析响应为JSON: {response_text}")
    
    def analyze_job(self, job_description: str) -> JobAnalysisResult:
        """
        分析职位描述
        
        Args:
            job_description: 职位描述文本
        
        Returns:
            JobAnalysisResult: 职位分析结果
        """
        try:
            # 构建提示词
            prompt = JOB_SUMMARY_PROMPT_TEMPLATE.format(job_description=job_description)
            
            # 调用API
            response_text = self._call_gemini_api(prompt)
            
            # 解析响应
            result_dict = self._parse_json_response(response_text)
            
            # 验证结果
            result = JobAnalysisResult(
                summary=result_dict.get("summary", ""),
                skills=result_dict.get("skills", [])
            )
            
            return result
            
        except Exception as e:
            logger.error(f"分析职位描述时出错: {str(e)}")
            # 返回空结果
            return JobAnalysisResult(summary="", skills=[])
    
    def batch_analyze_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量分析职位
        
        Args:
            jobs: 职位列表
        
        Returns:
            List[Dict[str, Any]]: 更新后的职位列表
        """
        try:
            total_jobs = len(jobs)
            logger.info(f"开始批量分析{total_jobs}个职位")
            
            for i, job in enumerate(jobs):
                job_id = job.get("job_id", f"job_{i}")
                job_description = job.get("job_description", "")
                
                if not job_description:
                    logger.warning(f"职位 {job_id} 没有描述，跳过分析")
                    continue
                
                logger.info(f"分析职位 {job_id} ({i+1}/{total_jobs})")
                
                # 分析职位
                result = self.analyze_job(job_description)
                
                # 更新职位数据
                job["summary"] = result.summary
                job["skills"] = result.skills
                
                # 添加延迟以避免API限制
                if i < total_jobs - 1:  # 不在最后一个请求后延迟
                    time.sleep(1)  # 1秒延迟
            
            logger.info(f"批量分析完成，处理了{total_jobs}个职位")
            return jobs
            
        except Exception as e:
            logger.error(f"批量分析职位时出错: {str(e)}")
            return jobs