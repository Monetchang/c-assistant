
from typing import List, Any, Dict, Optional, Sequence
from app.core.agent.base import AgentBase
from langchain_core.tools import BaseTool
from langchain_core.messages import BaseMessage, AnyMessage, AIMessage, HumanMessage
from langchain_core.language_models import BaseLanguageModel
from langgraph.prebuilt import create_react_agent
from app.core.tools.search.google_search import GoogleSearchEngine
from app.core.prompt.search import SYSTEM_PROMPT


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
            self.tools = [
                GoogleSearchEngine.perform_search,
            ]
        except Exception as e:
            print(f"Warning: Failed to initialize some search tools: {e}")
            self.tools = []

    def search(self, state) -> Dict[str, Sequence[AnyMessage]]:
        """
        搜索节点，执行搜索任务
        
        Args:
            state: 当前状态
            
        Returns:
            包含搜索消息的状态
        """
        assert self.deepseek_llm is not None, "deepseek_llm should be initialized"
        
        if not self.tools:
            # 如果没有工具可用，返回错误消息
            error_message = [AIMessage(content="Search tools are not available", name="search")]
            return {"messages": error_message}
        
        # 创建搜索代理
        search_agent = create_react_agent(
            self.deepseek_llm,
            tools=self.tools,
            prompt=SYSTEM_PROMPT
        )
        return search_agent

    def initialize_agent(self) -> Any:
        """
        初始化搜索代理
        
        Returns:
            搜索节点函数
        """
        return self.search
