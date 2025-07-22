import json
import os
from typing import List, Dict, Any
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel, Field
import re

from app.core.config import settings
from app.core.prompt.topic import TOPIC_GENERATION_PROMPT


class TopicSuggestion(BaseModel):
    """选题建议模型"""
    title: str = Field(description="选题标题")
    description: str = Field(description="选题描述")
    keywords: List[str] = Field(description="相关关键词")
    target_audience: str = Field(description="目标受众")
    content_type: str = Field(description="内容类型")


class TopicList(BaseModel):
    topics: List[TopicSuggestion]
    def __getitem__(self, key):
        return self.__dict__[key]


class TopicGenerator:
    """选题生成工具 - 基于LLM实现"""
    
    def __init__(self):
        os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
        self.llm = ChatDeepSeek(model="deepseek-chat")
    
    def generate_topics(self, requirement: str) -> List[TopicSuggestion]:
        try:
            from langdetect import detect
            lang = detect(requirement)
        except Exception:
            lang = "zh-cn" if re.search(r"[\u4e00-\u9fff]", requirement) else "en"
        lang_hint = "中文" if lang.startswith("zh") else "English"
        prompt = f"请根据以下需求，生成3-5个适合的选题建议，内容必须用{lang_hint}：\n需求：{requirement}"
        messages = [SystemMessage(content=prompt)]
        response = self.llm.with_structured_output(TopicList).invoke(messages)
        print(f"generate_topics Topic 工具结果: {response["topics"]}") 
        return response["topics"]