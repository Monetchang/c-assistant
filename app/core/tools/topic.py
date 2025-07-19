import json
import os
from typing import List, Dict, Any
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.prompt.topic import TOPIC_GENERATION_PROMPT


class TopicSuggestion(BaseModel):
    """选题建议模型"""
    title: str = Field(description="选题标题")
    description: str = Field(description="选题描述")
    keywords: List[str] = Field(description="相关关键词")
    target_audience: str = Field(description="目标受众")
    content_type: str = Field(description="内容类型")


class TopicGenerator:
    """选题生成工具 - 基于LLM实现"""
    
    def __init__(self):
        os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
        self.llm = ChatDeepSeek(model="deepseek-chat")
    
    @tool()
    def generate_topics(
        self, 
        user_requirement: str, 
        content_type: str = "article",
        num_topics: int = 5,
        *args, **kwargs
    ) -> str:
        """
        根据用户需求生成相关选题
        
        Args:
            user_requirement: 用户需求描述
            content_type: 内容类型 (article, blog, report, etc.)
            num_topics: 生成选题数量
            
        Returns:
            选题建议的JSON字符串
        """
        try:
            # 构建prompt
            prompt_content = TOPIC_GENERATION_PROMPT.format(
                user_requirement=user_requirement,
                content_type=content_type,
                num_topics=num_topics
            )
            
            # 使用LLM生成选题
            messages = [SystemMessage(content=prompt_content)]
            response = self.llm.invoke(messages)
            
            # 尝试解析JSON响应
            try:
                topics_data = json.loads(str(response.content))
                return json.dumps(topics_data, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                # 如果JSON解析失败，返回原始响应
                return str(response.content)
            
        except Exception as e:
            return f"选题生成错误: {str(e)}" 