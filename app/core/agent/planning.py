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
from app.core.tools.time import TimeTool
from app.core.tools.documentation import DocumentationTool


class ReWOO(TypedDict):
    task: str
    plan_string: str
    steps: List
    results: dict
    result: str


class PlanningAgent(AgentBase):
    """规划代理类，用于任务规划和步骤执行"""

    # 定义工具属性
    tavily_search: Optional[Any] = None
    topic_generator: Optional[Any] = None
    summary_tool: Optional[Any] = None
    writer_tool: Optional[Any] = None
    time_tool: Optional[Any] = None
    documentation_tool: Optional[Any] = None
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
            self.time_tool = TimeTool()
            self.documentation_tool = DocumentationTool()
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
        
        # 启动任务记录
        if self.documentation_tool is not None:
            self.documentation_tool.start_task(task)
            print(f"✓ Started documentation for task: {task}")
        
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
        return {"steps": steps}

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

        _results = state.get("results", {}) or {}

        # 获取工具和输入
        tool = current_step.get("tool", "")
        tool_input = current_step.get("tool_input", "")
        
        print(f"Current step: {current_step}")
        print(f"Original tool_input: {tool_input} (type: {type(tool_input)})")
        print(f"Results: {_results}")
        
        # 替换结果变量
        for k, v in _results.items():
            print(f"replace {k} with {v} (type: {type(v)})")
            if isinstance(tool_input, str):
                # 如果值是字典，只使用其字符串表示的前100个字符
                if isinstance(v, dict):
                    replacement = str(v)[:100] + "..." if len(str(v)) > 100 else str(v)
                else:
                    replacement = str(v)
                tool_input = tool_input.replace(k, replacement)
        
        print(f"After replacement tool_input: {tool_input} (type: {type(tool_input)})")
        
        import time
        start_time = time.time()
        
        try:
            if tool == "Search":
                # 检查搜索查询是否包含相对时间词汇，如果是则先处理时间
                if self._contains_relative_time_terms(tool_input):
                    # 先获取当前时间信息
                    time_result = self._execute_time("current")
                    # 然后执行搜索
                    result = self._execute_search(tool_input)
                else:
                    result = self._execute_search(tool_input)
            elif tool == "Topic":
                result = self._execute_topic(tool_input)
            elif tool == "Summary":
                result = self._execute_summary(tool_input)
            elif tool == "Writer":
                result = self._execute_writer(tool_input)
            elif tool == "Time":
                result = self._execute_time(tool_input)
            elif tool == "LLM":
                result = self.deepseek_llm.invoke(tool_input)
           
        except Exception as e:
            result = f"Error executing {tool}: {str(e)}"

        execution_time = time.time() - start_time
        print("execute_step result:", result)
        
        # 记录步骤执行信息
        if self.documentation_tool is not None:
            try:
                # 模拟token使用情况（实际应该从LLM响应中提取）
                token_usage = {
                    "prompt_tokens": 100,  # 这里应该从实际响应中获取
                    "completion_tokens": 200,
                    "total_tokens": 300
                }
                
                step_doc = self.documentation_tool.add_step(
                    current_step, 
                    str(result), 
                    token_usage, 
                    execution_time
                )
                print(f"✓ Documented step {step_doc.step_number}: {step_doc.step_name}")
                
                # 不保存中间进度，只在任务完成时保存最终报告
                
            except Exception as e:
                print(f"Warning: Failed to document step: {e}")
        
        _results[current_step["step_name"]] = str(result)
        return {"results": _results}

    def _execute_search(self, query: str) -> str:
        """执行搜索操作"""
        try:
            # 检查查询是否包含相对时间词汇，如果是则先处理时间
            if self.time_tool is not None:
                processed_query = self.time_tool.process_time_in_query(query)
            else:
                processed_query = query
            search_results = TavilySearchEngine.perform_search(processed_query)
            return f"Search results for '{processed_query}': {search_results}"
        except Exception as e:
            return f"Search error: {str(e)}"

    def _execute_topic(self, requirement: str) -> str:
        """执行选题生成"""
        try:
            if self.topic_generator is not None:
                # 确保 requirement 是字符串类型
                if isinstance(requirement, dict):
                    requirement_str = requirement.get('requirement', str(requirement))
                else:
                    requirement_str = str(requirement)
                
                topics = self.topic_generator.generate_topics(requirement_str)
                return f"Generated topics for '{requirement_str}': {topics}"
            else:
                return f"Topic generator not initialized"
        except Exception as e:
            return f"Topic generation error: {str(e)}"

    def _execute_summary(self, content: str) -> str:
        """执行内容摘要"""
        try:
            if self.summary_tool is not None:
                # 确保 content 是字符串类型
                if isinstance(content, dict):
                    content_str = content.get('content', str(content))
                else:
                    content_str = str(content)
                
                summary = self.summary_tool.summarize(content_str)
                return f"Summary: {summary}"
            else:
                return f"Summary tool not initialized"
            
        except Exception as e:
            return f"Summary error: {str(e)}"

    def _execute_writer(self, topic: str) -> str:
        """执行文章写作"""
        try:
            # 直接根据主题写文章
            if self.writer_tool is not None:
                # 确保 topic 是字符串类型
                if isinstance(topic, dict):
                    # 如果是字典，提取相关字段
                    topic_str = topic.get('topic', str(topic))
                else:
                    topic_str = str(topic)
                
                article = self.writer_tool.write_article_from_topic(topic_str)
                return f"Article for '{topic_str}': {article}"
            else:
                return f"Writer tool not initialized"
        except Exception as e:
            return f"Writing error: {str(e)}"

    def _execute_time(self, relative_time_term: str) -> str:
        """执行时间处理"""
        try:
            if self.time_tool is not None:
                # 确保 relative_time_term 是字符串类型
                if isinstance(relative_time_term, dict):
                    time_term_str = relative_time_term.get('time_term', str(relative_time_term))
                else:
                    time_term_str = str(relative_time_term)
                
                time_info = self.time_tool.get_current_time_info(time_term_str)
                return f"Time information for '{time_term_str}': {time_info}"
            else:
                return f"Time tool not initialized"
        except Exception as e:
            return f"Time processing error: {str(e)}"

    def _contains_relative_time_terms(self, text: str) -> bool:
        """检查文本是否包含相对时间词汇"""
        relative_time_patterns = [
            "最新", "latest", "current", "当前", "this year", "今年", 
            "recent", "最近", "now", "现在", "today", "今天", "当下"
        ]
        return any(pattern in text.lower() for pattern in relative_time_patterns)



    def solve(self, state: ReWOO) -> Any:
        """
        解决任务
        """
        assert self.deepseek_llm is not None, "deepseek_llm should be initialized"
        plan = ""
        for step in state["steps"]:
            # 步骤是字典格式，包含 step_name, description, tool, tool_input 等字段
            step_name = step.get("step_name", "Unknown Step")
            description = step.get("description", "")
            tool = step.get("tool", "")
            tool_input = step.get("tool_input", "")
            
            _results = state.get("results", {}) or {}
            for k, v in _results.items():
                if isinstance(tool_input, str):
                    tool_input = tool_input.replace(k, str(v))
                if isinstance(step_name, str):
                    step_name = step_name.replace(k, str(v))
            
            plan += f"Plan: {description}\n{step_name} = {tool}[{tool_input}]\n"
        
        solve_prompt = SOLVE_PROMPT.format(plan=plan, task=state["task"])
        result = self.deepseek_llm.invoke(solve_prompt)
        
        # 完成任务记录
        if self.documentation_tool is not None:
            try:
                task_doc = self.documentation_tool.complete_task(result.content)
                
                # 生成并保存最终报告
                final_report_path = self.documentation_tool.save_task_report(task_doc)
                print(f"✓ Final report saved: {final_report_path}")
                
                # 显示token使用统计
                token_summary = self.documentation_tool.get_token_usage_summary(task_doc)
                print(f"✓ Token usage summary: {token_summary}")
                
            except Exception as e:
                print(f"Warning: Failed to complete task documentation: {e}")
        
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
        graph.add_conditional_edges("tool", self._route)
        graph.add_edge("solve", END)

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
                initial_state, stream_mode="values"
            ):
                if "messages" in chunk and chunk["messages"]:
                    last_message = chunk["messages"][-1]
                    if hasattr(last_message, "content"):
                        final_response = last_message.content
        return final_response
