import os
from typing import Any, Optional
from pydantic import BaseModel, Field
from app.core.config import settings
from langchain_deepseek import ChatDeepSeek


class AgentBase(BaseModel):
    """代理基类，提供基础的LLM配置和初始化功能"""
    
    deepseek_llm: Optional[ChatDeepSeek] = None

    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_llm()
        
    def _initialize_llm(self) -> None:
        """初始化DeepSeek LLM"""
        os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
        self.deepseek_llm = ChatDeepSeek(model="deepseek-chat")
        
    def initialize_agent(self) -> Any:
        """
        初始化代理，子类应该重写此方法
        
        Returns:
            配置好的代理实例
        """
        raise NotImplementedError("Subclasses must implement initialize_agent method")