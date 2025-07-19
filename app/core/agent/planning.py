import json
import os
import re
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent

from app.core.agent.base import AgentBase
from app.core.config import settings
from app.core.prompt.planning import PLANNING_PROMPT, SOLVE_PROMPT
from app.core.prompt.search import SYSTEM_PROMPT
from app.core.tools.search.tavily_search import TavilySearchEngine
from app.core.tools.topic import TopicGenerator
from app.core.tools.summary import SummaryTool
from app.core.tools.writer import WriterTool


class ReWOO(TypedDict):
    task: str
    plan_string: str
    steps: List
    results: dict
    result: str


class PlanningAgent(AgentBase):
    """规划代理类，用于任务规划和步骤执行"""

    graph: Optional[Any] = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.deepseek_llm is None:
            os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
            self.deepseek_llm = ChatDeepSeek(model="deepseek-chat")
        # 初始化工具
        self._initialize_tools()
        self.graph = self.initialize_agent()

    def _initialize_tools(self) -> None:
        """初始化各种工具"""
        try:
            self.tavily_search = TavilySearchEngine()
            self.topic_generator = TopicGenerator()
            self.summary_tool = SummaryTool()
            self.writer_tool = WriterTool()
        except Exception as e:
            print(f"Warning: Failed to initialize some tools: {e}")

    def planning(self, state) -> Dict[str, Any]:
        """
        规划任务，将复杂任务分解为执行步骤
        
        Args:
            state: 当前状态

        Returns:
            任务规划结果
        """
        # 确保 task 是字符串
        task = str(state["task"])
        prompt_content = PLANNING_PROMPT.format(task=task)
        messages = [SystemMessage(content=prompt_content)]
        # 使用 LLM 生成规划结果
        assert self.deepseek_llm is not None, "deepseek_llm should be initialized"
        response = self.deepseek_llm.invoke(messages)
        print("planning response:", response.content)
        # 提取步骤
        steps = self._extract_steps_from_json(str(response.content))
        # print("Extracted steps:",
        #       json.dumps(steps, ensure_ascii=False, indent=2))

        # 返回规划结果
        return {"steps": steps, "plan_string": response.content}

    def execute_step(self, state: ReWOO) -> Dict[str, Any]:
        """
        执行单个步骤
        
        Args:
            state: 当前状态
            
        Returns:
            步骤执行结果
        """
        assert self.deepseek_llm is not None, "deepseek_llm should be initialized"
        _step = self._get_current_task(state)
        if _step is None:
            return {"result": state["results"]}
        current_step = state["steps"][_step - 1]
        print("current_step ===>", current_step)

        _results = state.get("results", {}) or {}

        for k, v in _results.items():
            print(f"replace {k} with {v}")
            current_step["tool_input"] = current_step["tool_input"].replace(k, v)

        # 根据工具类型执行不同的操作
        tool = current_step.get("tool", "")
        tool_input = current_step.get("tool_input", "")
        
        try:
            if tool == "Search":
                result = self._execute_search(tool_input)
            elif tool == "Topic":
                result = self._execute_topic(tool_input)
            elif tool == "Summary":
                result = self._execute_summary(tool_input)
            elif tool == "Writer":
                result = self._execute_writer(tool_input)
            elif tool == "LLM":
                result = self.deepseek_llm.invoke(tool_input)
           
        except Exception as e:
            result = f"Error executing {tool}: {str(e)}"

        print("execute_step result:", result)
        _results[current_step["step_name"]] = str(result)
        return {"results": _results}

    def _execute_search(self, query: str) -> str:
        """执行搜索操作"""
        try:
            search_results = self.tavily_search.perform_search(query)
            return f"Search results for '{query}': {search_results}"
        except Exception as e:
            return f"Search error: {str(e)}"

    def _execute_topic(self, requirement: str) -> str:
        """执行选题生成"""
        try:
            topics = self.topic_generator.generate_topics(requirement)
            return f"Generated topics for '{requirement}': {topics}"
        except Exception as e:
            return f"Topic generation error: {str(e)}"

    def _execute_summary(self, content: str) -> str:
        """执行内容摘要"""
        try:
            summary = self.summary_tool.summarize(content)
            return f"Summary: {summary}"
        except Exception as e:
            return f"Summary error: {str(e)}"

    def _execute_writer(self, topic: str) -> str:
        """执行文章写作"""
        try:
            # 直接根据主题写文章
            article = self.writer_tool.write_article_from_topic(topic)
            return f"Article for '{topic}': {article}"
        except Exception as e:
            return f"Writing error: {str(e)}"

    def solve(self, state: ReWOO) -> Any:
        """
        解决任务
        """
        assert self.deepseek_llm is not None, "deepseek_llm should be initialized"
        plan = ""
        for step_name, description, tool, tool_input, _ in state["steps"]:
            _results = state.get("results", {}) or {}
            for k, v in _results.items():
                tool_input = tool_input.replace(k, v)
                step_name = step_name.replace(k, v)
            plan += f"Plan: {description}\n{step_name} = {tool}[{tool_input}]"
        solve_prompt = SOLVE_PROMPT.format(plan=plan, task=state["task"])
        result = self.deepseek_llm.invoke(solve_prompt)
        return {"result": result.content}

    def _get_current_task(self, state: ReWOO):
        results = state.get("results", {})
        if results is None:
            return 1
        if len(results) == len(state["steps"]):
            return None
        else:
            return len(results) + 1

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
            match = re.search(r"\[\s*{.*?}\s*\]", output, re.DOTALL)
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

    def _route(self, state: ReWOO):
        _step = self._get_current_task(state)
        if _step is None:
            # 确定所有子任务执行
            return "solve"
        else:
            # 任务未执行完成返回工具
            return "tool"

    def initialize_agent(self) -> Any:
        """
        初始化规划代理

        Returns:
            规划节点函数
        """
        graph = StateGraph(ReWOO)
        graph.add_node("plan", self.planning)
        graph.add_node("tool", self.execute_step)
        graph.add_node("solve", self.solve)

        graph.add_edge(START, "plan")
        graph.add_edge("plan", "tool")
        # graph.add_conditional_edges("tool", self._route)
        graph.add_edge("tool", END)

        self.graph = graph
        return graph.compile()

    def test_async_start_chat(self, task: str) -> Any:
        """
        异步启动聊天
        """
        # 创建图并编译
        if not self.graph:
            self.graph = self.initialize_agent()
        initial_state = ReWOO(
            task=task, plan_string="", steps=[], results={}, result=""
        )

        final_response = ""
        if self.graph is not None:
            for chunk in self.graph.stream(
                initial_state, stream_mode="values", print_mode="debug"
            ):
                if "messages" in chunk and chunk["messages"]:
                    last_message = chunk["messages"][-1]
                    if hasattr(last_message, "content"):
                        final_response = last_message.content
        return final_response
