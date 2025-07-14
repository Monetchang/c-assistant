
from typing import List, Any, Dict, Optional, Sequence
from app.core.agent.base import AgentBase
from langchain_core.messages import BaseMessage, AnyMessage, AIMessage, HumanMessage
from langchain_core.language_models import BaseLanguageModel
from langgraph.prebuilt import create_react_agent
from app.core.prompt.planning import PLANNING_PROMPT


class PlanningAgent(AgentBase):
    """规划代理类，用于拆解复杂任务"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def planning(self, state) -> Dict[str, Sequence[AnyMessage]]:
        """
        规划节点，拆解复杂任务
        
        Args:
            state: 当前状态
            
        Returns:
            包含规划消息的状态
        """
        assert self.deepseek_llm is not None, "deepseek_llm should be initialized"
        
        # return self.deepseek_llm.invoke(PLANNING_PROMPT)
        planning_agent = create_react_agent(
            self.deepseek_llm,
            prompt=PLANNING_PROMPT
        )
        return planning_agent

    def initialize_agent(self) -> Any:
        """
        初始化规划代理
        
        Returns:
            规划节点函数
        """
        return self.planning