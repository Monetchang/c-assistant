
from typing import TypedDict, List, Any, Dict, Optional, Sequence
from app.core.agent.base import AgentBase
from langchain_core.messages import BaseMessage, AnyMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from app.core.prompt.planning import PLANNING_PROMPT
from langchain_deepseek import ChatDeepSeek
from app.core.config import settings
import re
import json
import os

class ReWOO(TypedDict):
    task: str
    plan_string: str
    steps: List
    results: dict
    result: str

class PlanningAgent(AgentBase):
    """规划代理类，用于拆解复杂任务"""

    graph: Optional[Any] = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.deepseek_llm is None:
            os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
            self.deepseek_llm = ChatDeepSeek(model="deepseek-chat")
        self.graph = self.initialize_agent()

    def planning(self, state) -> Dict[str, Any]:
        """
        规划节点，拆解复杂任务
        
        Args:
            state: 当前状态
            
        Returns:
            包含规划结果的状态
        """
        # 确保 task 是字符串
        task = str(state["task"])
        messages = [SystemMessage(content=PLANNING_PROMPT.format(task=task))] 
        # 使用 LLM 生成规划结果
        assert self.deepseek_llm is not None, "deepseek_llm should be initialized"
        response = self.deepseek_llm.invoke(messages)
        print("planning response:", response.content)
        # 提取步骤
        steps = self._extract_steps_from_json(response.content)
        # print("Extracted steps:",  json.dumps(steps, ensure_ascii=False, indent=2))
       
        # 返回规划结果
        return {"steps": steps, "plan_string": response.content}

    def _get_current_task(state: ReWOO):
        if state["results"] is None:
            return 1
        if len(state["results"]) == len(state["steps"]):
            return None
        else:
            return len(state["results"]) + 1

    def execute_step(self, state) -> Dict[str, Any]:
        """
        执行步骤
        """
        _step = self._get_current_task(state)
        _, step_name, description, tool, tool_input, step_type = state["steps"][_step - 1]
        _results = state["results"] or {}
        if step_type == "NEEDS_SEARCH":
            if tool == "Google":
                result = SearchAgent().initialize_agent().search(tool_input)
            else:
                raise ValueError(f"Invalid tool: {tool}")
        elif step_type == "NEEDS_GENERATION":
            if tool == "LLM":
                result = self.generate(tool_input)
            else:
                raise ValueError(f"Invalid tool: {tool}")
        elif step_type == "NEEDS_ANALYSIS":
            if tool == "LLM":
                result = self.analyze(tool_input)
            else:
                raise ValueError(f"Invalid tool: {tool}")
        else:
            raise ValueError(f"Invalid step type: {step_type}")
        _results[step_name] = str(result)
        return {"result": _results}

    def _extract_steps_from_json(self, output: str) -> List[Dict]:
        """
        从 LLM 输出中提取 JSON 格式的步骤
        
        Args:
            output: LLM的完整输出字符串
            
        Returns:
            步骤列表
        """
        try:
            # 匹配 JSON 数组部分
            match = re.search(r'\[\s*{.*?}\s*\]', output, re.DOTALL)
            if match:
                steps_json = match.group(0)
                steps = json.loads(steps_json)
                return steps
            else:
                print("No JSON array found in output")
                return []
        except Exception as e:
            print("JSON解析失败:", e)
            return []

    def initialize_agent(self) -> Any:
        """
        初始化规划代理
        
        Returns:
            规划节点函数
        """
        graph = StateGraph(ReWOO)
        graph.add_node("plan", self.planning)
        graph.add_edge(START, "plan")
        graph.add_edge("plan", END)
        self.graph = graph
        return graph.compile()

    def test_async_start_chat(self, task: str) -> Any:
        """
        异步启动聊天
        """
        # 创建图并编译
        if not self.graph:
            self.graph = self.initialize_agent()
        initial_state = ReWOO(task=task)

        final_response = ""
        for chunk in self.graph.stream(
                initial_state,
                stream_mode="values",
                print_mode="debug"
            ):
                if "messages" in chunk and chunk["messages"]:
                    last_message = chunk["messages"][-1]
                    if hasattr(last_message, 'content'):
                        final_response = last_message.content
        return final_response
        