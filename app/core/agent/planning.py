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
from app.core.tools.search.google_search import GoogleSearchEngine


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
        执行步骤
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

        if current_step["step_type"] == "NEEDS_SEARCH":
            if current_step["tool"] == "Google":
                search_agent = create_react_agent(
                    self.deepseek_llm,
                    tools=[GoogleSearchEngine.perform_search],
                    prompt=SYSTEM_PROMPT,
                )
                inputs = {
                    "messages": [
                        {"role": "user", "content": current_step["tool_input"]}
                    ]
                }
                result = search_agent.invoke(inputs)
            else:
                raise ValueError(f"Invalid tool: {current_step['tool']}")
        elif current_step["step_type"] == "NEEDS_GENERATION":
            if current_step["tool"] == "LLM":
                result = self.deepseek_llm.invoke(current_step["tool_input"])
            else:
                raise ValueError(f"Invalid tool: {current_step['tool']}")
        elif current_step["step_type"] == "NEEDS_ANALYSIS":
            if current_step["tool"] == "LLM":
                result = self.deepseek_llm.invoke(current_step["tool_input"])
            else:
                raise ValueError(f"Invalid tool: {current_step['tool']}")
        else:
            raise ValueError(f"Invalid step type: {current_step['step_type']}")

        print("execute_step result:", result)
        _results[current_step["step_name"]] = str(result)
        return {"results": _results}

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
        compiled_graph = self.graph
        if compiled_graph is not None:
            for chunk in compiled_graph.stream(
                initial_state, stream_mode="values", print_mode="debug"
            ):
                if "messages" in chunk and chunk["messages"]:
                    last_message = chunk["messages"][-1]
                    if hasattr(last_message, "content"):
                        final_response = last_message.content
        return final_response
