#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LLM处理模块

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

from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE, GEMINI_MAX_OUTPUT_TOKENS, \
    GEMINI_TOP_P, GEMINI_TOP_K, GEMINI_MAX_RETRIES, GEMINI_RETRY_MIN_WAIT, GEMINI_RETRY_MAX_WAIT, \
    JOB_SUMMARY_PROMPT_TEMPLATE, SKILL_EXTRACTION_PROMPT_TEMPLATE

# 设置日志
logger = logging.getLogger(__name__)

# 定义输出模型
class JobAnalysisResult(BaseModel):
    """职位分析结果模型"""
    summary: str = Field(..., description="职位摘要")
    skills: List[str] = Field(..., description="技能列表")

class LLMProcessor:
    """LLM处理类，用于调用Gemini API进行职位摘要和技能提取"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化LLM处理器
        
        Args:
            api_key: Gemini API密钥，如果为None则使用配置文件中的密钥
        """
        self.api_key = api_key or GEMINI_API_KEY
        self.model = GEMINI_MODEL
        self.temperature = GEMINI_TEMPERATURE
        self.max_output_tokens = GEMINI_MAX_OUTPUT_TOKENS
        self.top_p = GEMINI_TOP_P
        self.top_k = GEMINI_TOP_K
        
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
        
        logger.info(f"LLM处理器初始化完成，使用模型: {self.model}")
    
    @retry(stop=stop_after_attempt(GEMINI_MAX_RETRIES), 
           wait=wait_exponential(multiplier=1, min=GEMINI_RETRY_MIN_WAIT, max=GEMINI_RETRY_MAX_WAIT))
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
                logger.debug(f"原始响应: {response_text}")
                raise ValueError(f"无法解析JSON响应: {str(e)}")
    
    def analyze_job(self, job_description: str, job_title: str, company: str) -> JobAnalysisResult:
        """
        分析职位描述，提取摘要和技能
        
        Args:
            job_description: 职位描述
            job_title: 职位标题
            company: 公司名称
        
        Returns:
            JobAnalysisResult: 职位分析结果
        """
        try:
            # 构建提示词
            prompt = JOB_SUMMARY_PROMPT_TEMPLATE.format(
                job_title=job_title,
                company=company,
                job_description=job_description
            )
            
            # 调用API
            logger.info(f"开始分析职位: {job_title} at {company}")
            response_text = self._call_gemini_api(prompt)
            
            # 解析响应
            result_json = self._parse_json_response(response_text)
            
            # 验证结果
            result = JobAnalysisResult(
                summary=result_json.get("summary", ""),
                skills=result_json.get("skills", [])
            )
            
            logger.info(f"成功分析职位，提取了{len(result.skills)}个技能")
            return result
            
        except ValidationError as e:
            logger.error(f"验证结果时出错: {str(e)}")
            # 返回空结果
            return JobAnalysisResult(summary="", skills=[])
            
        except Exception as e:
            logger.error(f"分析职位时出错: {str(e)}")
            # 返回空结果
            return JobAnalysisResult(summary="", skills=[])
    
    def batch_analyze_jobs(self, jobs: List[Dict[str, Any]], batch_size: int = 5, 
                          delay_seconds: float = 1.0) -> List[Dict[str, Any]]:
        """
        批量分析职位
        
        Args:
            jobs: 职位列表
            batch_size: 批处理大小
            delay_seconds: 每个请求之间的延迟（秒）
        
        Returns:
            List[Dict[str, Any]]: 带有分析结果的职位列表
        """
        results = []
        total_jobs = len(jobs)
        
        logger.info(f"开始批量分析{total_jobs}个职位，批处理大小: {batch_size}")
        
        for i, job in enumerate(jobs):
            try:
                # 获取职位信息
                job_id = job.get("job_id", f"job_{i}")
                job_title = job.get("job_title", "")
                company = job.get("company", "")
                job_description = job.get("job_description", "")
                
                # 检查是否已经有分析结果
                if "summary" in job and "skills" in job and job["summary"] and job["skills"]:
                    logger.info(f"跳过已分析的职位: {job_id}")
                    results.append(job)
                    continue
                
                # 分析职位
                logger.info(f"分析职位 {i+1}/{total_jobs}: {job_id}")
                analysis_result = self.analyze_job(job_description, job_title, company)
                
                # 更新职位信息
                job_copy = job.copy()
                job_copy["summary"] = analysis_result.summary
                job_copy["skills"] = analysis_result.skills
                
                results.append(job_copy)
                
                # 添加延迟
                if (i + 1) % batch_size == 0 and i < total_jobs - 1:
                    logger.info(f"已处理{i+1}/{total_jobs}个职位，暂停{delay_seconds}秒")
                    time.sleep(delay_seconds)
                    
            except Exception as e:
                logger.error(f"处理职位{i+1}/{total_jobs}时出错: {str(e)}")
                # 添加原始职位，不包含分析结果
                results.append(job)
        
        logger.info(f"批量分析完成，成功分析{len(results)}个职位")
        return results

# 测试代码
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建测试数据
    test_job = {
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
        
        Benefits:
        - Competitive salary
        - Health insurance
        - 401(k) matching
        - Flexible work hours
        - Remote work options
        """
    }
    
    # 创建LLM处理器
    processor = LLMProcessor()
    
    # 测试分析职位
    result = processor.analyze_job(
        job_description=test_job["job_description"],
        job_title=test_job["job_title"],
        company=test_job["company"]
    )
    
    print(f"职位摘要: {result.summary}")
    print(f"技能列表: {result.skills}")
    
    # 测试批量分析
    batch_results = processor.batch_analyze_jobs([test_job])
    print(f"批量分析结果: {batch_results}")