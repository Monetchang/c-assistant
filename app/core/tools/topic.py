import json
import os
import re
from typing import List, Optional

from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel, Field

from app.core.config import settings


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

    def generate_topics(
        self, requirement: str, lang_detect_str: Optional[str] = None
    ) -> List[TopicSuggestion]:
        lang_detect_str = lang_detect_str or requirement
        try:
            from langdetect import detect

            lang = detect(lang_detect_str)
        except Exception:
            lang = "zh-cn" if re.search(r"[\u4e00-\u9fff]", lang_detect_str) else "en"
        lang_hint = "中文" if lang.startswith("zh") else "English"
        prompt = f"请根据以下需求，生成5-10个多样化的选题建议，覆盖初学者、进阶、资深等不同阶段的人员，内容必须用{lang_hint}，且不要包含具体年份、今年、最新等时效性词汇，选题应具有长期价值：\n需求：{requirement}"
        messages = [SystemMessage(content=prompt)]
        response = self.llm.with_structured_output(TopicList).invoke(messages)
        print(f"generate_topics Topic 工具结果: {response['topics']}")
        return response["topics"]
