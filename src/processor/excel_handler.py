#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Excel处理模块

该模块负责处理Excel文件的读写操作，包括保存爬取的职位数据、
加载已有数据进行分析，以及保存关键词分析结果。
"""

import os
import logging
import pandas as pd
from typing import List, Dict, Any, Optional, Union

# 设置日志
logger = logging.getLogger(__name__)

class ExcelHandler:
    """
    Excel文件处理类
    """
    
    def __init__(self):
        """
        初始化Excel处理器
        """
        pass
    
    def save_to_excel(self, data: List[Dict[str, Any]], file_path: str) -> bool:
        """
        将职位数据保存到Excel文件
        
        Args:
            data: 职位数据列表
            file_path: 保存路径
        
        Returns:
            bool: 是否成功保存
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 转换为DataFrame
            df = pd.DataFrame(data)
            
            # 重新排列列顺序，使重要列在前面
            columns_order = [
                'job_id', 'job_title', 'company', 'location', 'job_type',
                'search_keyword', 'search_location', 'crawl_time',
                'job_description', 'job_link'
            ]
            
            # 添加其他可能存在的列
            all_columns = list(df.columns)
            for col in columns_order:
                if col in all_columns:
                    all_columns.remove(col)
            
            # 最终列顺序
            final_columns = columns_order + all_columns
            final_columns = [col for col in final_columns if col in df.columns]
            
            # 重新排序列
            df = df[final_columns]
            
            # 保存到Excel
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            logger.info(f"成功保存{len(data)}条数据到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存Excel文件时出错: {str(e)}")
            return False
    
    def load_from_excel(self, file_path: str) -> List[Dict[str, Any]]:
        """
        从Excel文件加载职位数据
        
        Args:
            file_path: Excel文件路径
        
        Returns:
            List[Dict[str, Any]]: 职位数据列表
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return []
            
            # 读取Excel文件
            df = pd.read_excel(file_path, engine='openpyxl')
            
            # 转换为字典列表
            data = df.to_dict('records')
            
            logger.info(f"从{file_path}加载了{len(data)}条数据")
            return data
            
        except Exception as e:
            logger.error(f"加载Excel文件时出错: {str(e)}")
            return []
    
    def append_to_excel(self, data: List[Dict[str, Any]], file_path: str) -> bool:
        """
        将新数据追加到现有Excel文件
        
        Args:
            data: 要追加的数据
            file_path: Excel文件路径
        
        Returns:
            bool: 是否成功追加
        """
        try:
            # 检查文件是否存在
            if os.path.exists(file_path):
                # 读取现有数据
                existing_df = pd.read_excel(file_path, engine='openpyxl')
                
                # 转换新数据为DataFrame
                new_df = pd.DataFrame(data)
                
                # 合并数据
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                
                # 去重（基于job_id）
                if 'job_id' in combined_df.columns:
                    combined_df = combined_df.drop_duplicates(subset=['job_id'], keep='last')
                
                # 保存合并后的数据
                combined_df.to_excel(file_path, index=False, engine='openpyxl')
                
                logger.info(f"成功追加{len(data)}条数据到: {file_path}，总计{len(combined_df)}条")
                return True
                
            else:
                # 如果文件不存在，直接保存
                return self.save_to_excel(data, file_path)
                
        except Exception as e:
            logger.error(f"追加数据到Excel文件时出错: {str(e)}")
            return False
    
    def save_keywords_to_excel(self, keyword_data: Dict[str, Any], file_path: str) -> bool:
        """
        保存关键词分析结果到Excel文件
        
        Args:
            keyword_data: 关键词分析结果
            file_path: 保存路径
        
        Returns:
            bool: 是否成功保存
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 创建Excel写入器
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 保存混合关键词结果
                if 'hybrid_keywords' in keyword_data:
                    hybrid_df = pd.DataFrame(keyword_data['hybrid_keywords'])
                    hybrid_df.to_excel(writer, sheet_name='混合关键词', index=False)
                
                # 保存LLM关键词结果
                if 'llm_keywords' in keyword_data:
                    llm_df = pd.DataFrame(keyword_data['llm_keywords'])
                    llm_df.to_excel(writer, sheet_name='LLM关键词', index=False)
                
                # 保存传统关键词结果
                if 'traditional_keywords' in keyword_data:
                    trad_df = pd.DataFrame(keyword_data['traditional_keywords'])
                    trad_df.to_excel(writer, sheet_name='传统关键词', index=False)
                
                # 保存职位摘要
                if 'job_summaries' in keyword_data:
                    summary_df = pd.DataFrame(keyword_data['job_summaries'])
                    summary_df.to_excel(writer, sheet_name='职位摘要', index=False)
                
                # 保存元数据
                if 'metadata' in keyword_data:
                    meta_df = pd.DataFrame([keyword_data['metadata']])
                    meta_df.to_excel(writer, sheet_name='元数据', index=False)
            
            logger.info(f"成功保存关键词分析结果到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存关键词分析结果时出错: {str(e)}")
            return False
    
    def load_keywords_from_excel(self, file_path: str) -> Dict[str, Any]:
        """
        从Excel文件加载关键词分析结果
        
        Args:
            file_path: Excel文件路径
        
        Returns:
            Dict[str, Any]: 关键词分析结果
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return {}
            
            # 读取Excel文件的所有sheet
            xls = pd.ExcelFile(file_path, engine='openpyxl')
            
            # 初始化结果字典
            keyword_data = {}
            
            # 读取混合关键词
            if '混合关键词' in xls.sheet_names:
                hybrid_df = pd.read_excel(xls, '混合关键词')
                keyword_data['hybrid_keywords'] = hybrid_df.to_dict('records')
            
            # 读取LLM关键词
            if 'LLM关键词' in xls.sheet_names:
                llm_df = pd.read_excel(xls, 'LLM关键词')
                keyword_data['llm_keywords'] = llm_df.to_dict('records')
            
            # 读取传统关键词
            if '传统关键词' in xls.sheet_names:
                trad_df = pd.read_excel(xls, '传统关键词')
                keyword_data['traditional_keywords'] = trad_df.to_dict('records')
            
            # 读取职位摘要
            if '职位摘要' in xls.sheet_names:
                summary_df = pd.read_excel(xls, '职位摘要')
                keyword_data['job_summaries'] = summary_df.to_dict('records')
            
            # 读取元数据
            if '元数据' in xls.sheet_names:
                meta_df = pd.read_excel(xls, '元数据')
                if not meta_df.empty:
                    keyword_data['metadata'] = meta_df.iloc[0].to_dict()
            
            logger.info(f"从{file_path}加载了关键词分析结果")
            return keyword_data
            
        except Exception as e:
            logger.error(f"加载关键词分析结果时出错: {str(e)}")
            return {}
    
    def clean_text(self, text: Optional[str]) -> str:
        """
        清理文本数据
        
        Args:
            text: 要清理的文本
        
        Returns:
            str: 清理后的文本
        """
        if text is None:
            return ""
        
        # 转换为字符串
        if not isinstance(text, str):
            text = str(text)
        
        # 替换特殊字符
        text = text.replace('\r', ' ').replace('\n', ' ')
        
        # 移除多余空格
        text = ' '.join(text.split())
        
        return text

# 测试代码
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建测试数据
    test_data = [
        {
            "job_id": "test1",
            "job_title": "Python Developer",
            "company": "Test Company",
            "location": "Remote",
            "job_description": "This is a test job description.",
            "job_link": "https://example.com/job/1",
            "search_keyword": "Python",
            "search_location": "United States",
            "crawl_time": "2023-01-01 12:00:00"
        },
        {
            "job_id": "test2",
            "job_title": "Data Scientist",
            "company": "Another Company",
            "location": "New York",
            "job_description": "This is another test job description.",
            "job_link": "https://example.com/job/2",
            "search_keyword": "Data Science",
            "search_location": "United States",
            "crawl_time": "2023-01-01 12:30:00"
        }
    ]
    
    # 创建Excel处理器
    handler = ExcelHandler()
    
    # 测试保存到Excel
    test_file = "test_jobs.xlsx"
    handler.save_to_excel(test_data, test_file)
    
    # 测试加载Excel
    loaded_data = handler.load_from_excel(test_file)
    print(f"加载的数据: {loaded_data}")
    
    # 测试追加数据
    append_data = [
        {
            "job_id": "test3",
            "job_title": "ML Engineer",
            "company": "Third Company",
            "location": "San Francisco",
            "job_description": "This is a third test job description.",
            "job_link": "https://example.com/job/3",
            "search_keyword": "Machine Learning",
            "search_location": "United States",
            "crawl_time": "2023-01-01 13:00:00"
        }
    ]
    handler.append_to_excel(append_data, test_file)
    
    # 测试关键词数据
    keyword_data = {
        "hybrid_keywords": [
            {"keyword": "Python", "frequency": 10, "score": 15.0},
            {"keyword": "Machine Learning", "frequency": 8, "score": 12.0}
        ],
        "llm_keywords": [
            {"keyword": "Python", "frequency": 7, "score": 7.0},
            {"keyword": "Machine Learning", "frequency": 5, "score": 5.0}
        ],
        "traditional_keywords": [
            {"keyword": "Python", "frequency": 10, "score": 10.0},
            {"keyword": "Machine Learning", "frequency": 8, "score": 8.0}
        ],
        "metadata": {
            "total_jobs": 3,
            "analysis_time": "2023-01-01 14:00:00",
            "llm_weight": 1.5,
            "traditional_weight": 1.0
        }
    }
    
    # 测试保存关键词数据
    keyword_file = "test_keywords.xlsx"
    handler.save_keywords_to_excel(keyword_data, keyword_file)
    
    # 测试加载关键词数据
    loaded_keywords = handler.load_keywords_from_excel(keyword_file)
    print(f"加载的关键词数据: {loaded_keywords}")
    
    # 清理测试文件
    import os
    if os.path.exists(test_file):
        os.remove(test_file)
    if os.path.exists(keyword_file):
        os.remove(keyword_file)