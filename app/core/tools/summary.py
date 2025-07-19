import json
import os
from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.prompt.summary import SUMMARY_GENERATION_PROMPT


class SummaryResult(BaseModel):
    """摘要结果模型"""
    original_length: int = Field(description="原文长度")
    summary_length: int = Field(description="摘要长度")
    summary: str = Field(description="摘要内容")
    key_points: List[str] = Field(description="关键要点")
    compression_ratio: float = Field(description="压缩比例")


class SummaryTool:
    """摘要工具 - 基于LLM实现"""
    
    def __init__(self):
        os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
        self.llm = ChatDeepSeek(model="deepseek-chat")
    
    def summarize_content(
        self, 
        content: str, 
        max_length: int = 500,
        include_key_points: bool = True,
        *args, **kwargs
    ) -> SummaryResult:
        """
        对长文本内容进行摘要总结
        
        Args:
            content: 需要摘要的内容
            max_length: 摘要最大长度
            include_key_points: 是否包含关键要点
            
        Returns:
            摘要结果
        """
        try:
            original_length = len(content)
            
            # 构建prompt
            prompt_content = SUMMARY_GENERATION_PROMPT.format(
                content=content,
                max_length=max_length
            )
            
            # 使用LLM生成摘要
            messages = [SystemMessage(content=prompt_content)]
            response = self.llm.invoke(messages)
            
            # 尝试解析JSON响应
            try:
                summary_data = json.loads(str(response.content))
                summary = summary_data.get('summary', str(response.content))
                key_points = summary_data.get('key_points', [])
                summary_length = len(summary)
            except json.JSONDecodeError:
                # 如果JSON解析失败，使用原始响应
                summary = str(response.content)
                key_points = []
                summary_length = len(summary)
            
            compression_ratio = summary_length / original_length if original_length > 0 else 1.0
            
            return SummaryResult(
                original_length=original_length,
                summary_length=summary_length,
                summary=summary,
                key_points=key_points,
                compression_ratio=compression_ratio
            )
            
        except Exception as e:
            return SummaryResult(
                original_length=0,
                summary_length=0,
                summary=f"摘要生成错误: {str(e)}",
                key_points=[],
                compression_ratio=0.0
            )
    
    @tool()
    def summarize(
        self, 
        content: str, 
        max_length: int = 500,
        *args, **kwargs
    ) -> str:
        """
        对文本内容进行摘要总结
        
        Args:
            content: 需要摘要的内容
            max_length: 摘要最大长度
            
        Returns:
            摘要内容字符串
        """
        result = self.summarize_content(content, max_length)
        return result.summary
    
    def summarize_multiple_sources(
        self, 
        sources: List[str], 
        max_length: int = 800,
        *args, **kwargs
    ) -> SummaryResult:
        """
        对多个信息源进行综合摘要
        
        Args:
            sources: 多个信息源列表
            max_length: 摘要最大长度
            
        Returns:
            综合摘要结果
        """
        try:
            combined_content = "\n\n".join(sources)
            return self.summarize_content(combined_content, max_length)
            
        except Exception as e:
            return SummaryResult(
                original_length=0,
                summary_length=0,
                summary=f"多源摘要生成错误: {str(e)}",
                key_points=[],
                compression_ratio=0.0
            ) 