
from typing import List, Any, Dict, Optional
from app.core.agent.base import AgentBase
from langchain_core.tools import BaseTool
from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseLanguageModel
from langgraph.prebuilt import create_react_agent
from app.core.tools.search.google_search import GoogleSearchEngine


class SearchAgent(AgentBase):
    """搜索代理类，用于执行搜索相关任务"""
    
    tools: List[BaseTool] = []
    agent: Optional[Any] = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化搜索工具
        self._initialize_tools()

    def _initialize_tools(self) -> None:
        """初始化搜索工具"""
        try:
            google_search = GoogleSearchEngine()
            
            self.tools = [
                google_search.perform_search,
            ]
        except Exception as e:
            print(f"Warning: Failed to initialize some search tools: {e}")
            self.tools = []

    def initialize_agent(self) -> Any:
        """
        初始化搜索代理
        
        Returns:
            配置好的代理实例
        """
        assert self.deepseek_llm is not None, "deepseek_llm should be initialized"
        
        if not self.tools:
            print("Warning: No search tools available")
            return None
            
        return create_react_agent(
            self.deepseek_llm,
            tools=self.tools,
            prompt="You are a search agent. You are given a query and you need to search the web for the information. You should use the tools provided to you to search the web. You should return the results in a structured format."
        )
