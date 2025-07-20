import os
from datetime import datetime, timedelta
from typing import Dict, Any
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langchain_deepseek import ChatDeepSeek

from app.core.config import settings


class TimeTool:
    """时间工具 - 处理相对时间词汇"""
    
    def __init__(self):
        os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
        self.llm = ChatDeepSeek(model="deepseek-chat")
    
    @tool()
    def get_current_time_info(self, relative_time_term: str = "current") -> str:
        """
        根据相对时间词汇获取当前时间信息
        
        Args:
            relative_time_term: 相对时间词汇 (latest, current, this year, recent, etc.)
            
        Returns:
            当前时间信息的JSON字符串
        """
        try:
            now = datetime.now()
            
            # 根据不同的相对时间词汇返回相应的时间信息
            time_info = {
                "current_date": now.strftime("%Y-%m-%d"),
                "current_year": now.year,
                "current_month": now.month,
                "current_day": now.day,
                "relative_term": relative_time_term,
                "formatted_time": now.strftime("%Y年%m月%d日"),
                "iso_format": now.isoformat()
            }
            
            # 处理特定的相对时间词汇
            if "year" in relative_time_term.lower() or "年" in relative_time_term:
                time_info["search_context"] = f"{now.year}"
            elif "month" in relative_time_term.lower() or "月" in relative_time_term:
                time_info["search_context"] = f"{now.year}-{now.month:02d}"
            elif "latest" in relative_time_term.lower() or "最新" in relative_time_term:
                time_info["search_context"] = f"{now.year}"
            elif "recent" in relative_time_term.lower() or "最近" in relative_time_term:
                # 最近可以是过去3个月
                recent_date = now - timedelta(days=90)
                time_info["search_context"] = f"{recent_date.year}-{now.year}"
            else:
                time_info["search_context"] = f"{now.year}"
            
            return str(time_info)
            
        except Exception as e:
            return f"Time processing error: {str(e)}"
    
    def process_time_in_query(self, query: str) -> str:
        """
        处理查询中的时间词汇，将相对时间转换为具体时间
        
        Args:
            query: 原始查询
            
        Returns:
            处理后的查询
        """
        try:
            # 定义相对时间词汇模式
            relative_time_patterns = [
                "最新", "latest", "current", "当前", "this year", "今年", 
                "recent", "最近", "now", "现在", "today", "今天"
            ]
            
            # 检查是否包含相对时间词汇
            contains_relative_time = any(pattern in query.lower() for pattern in relative_time_patterns)
            
            if contains_relative_time:
                # 获取当前时间信息
                time_info = self.get_current_time_info("current")
                # 这里可以进一步处理，将查询中的相对时间词汇替换为具体时间
                # 简化处理：在查询后添加时间上下文
                return f"{query} ({time_info})"
            else:
                return query
                
        except Exception as e:
            return f"Query processing error: {str(e)}" 