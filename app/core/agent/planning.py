import json
import os
import re
import time
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from app.core.agent.base import AgentBase
from app.core.config import settings
from app.core.context import AgentContext
from app.core.prompt.planning import PLANNING_PROMPT, SOLVE_PROMPT
from app.core.prompt.search import SYSTEM_PROMPT
from app.core.tools.documentation import DocumentationTool
from app.core.tools.search.tavily_search import TavilySearchEngine
from app.core.tools.summary import SummaryTool
from app.core.tools.time import TimeTool
from app.core.tools.topic import TopicGenerator
from app.core.tools.topic_selection import TopicSelectionTool
from app.core.tools.writer import WriterTool


class TopicSuggestion(BaseModel):
    title: str
    description: str
    keywords: List[str]
    target_audience: str
    content_type: str


class TopicList(BaseModel):
    topics: List[TopicSuggestion]


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
    topic_selection_tool: Optional[TopicSelectionTool] = None
    graph: Optional[Any] = None
    agent_context: Optional[AgentContext] = None

    def __init__(self, agent_context: Optional[AgentContext] = None, **kwargs):
        super().__init__(**kwargs)
        self.agent_context = agent_context or AgentContext(agent_id="default")
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
            self.topic_selection_tool = TopicSelectionTool()
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

        # 用 step 的 description、step_name 和 tool 初始化 todo
        todo_items = []
        for step in steps:
            step_name = step.get("step_name", "")
            tool = step.get("tool", "")
            description = step.get("description", "")
            todo_item = f"{step_name} ({tool}): {description}"
            todo_items.append(todo_item)

        # 如果当前没有 task，则创建新任务，并用 steps 初始化 todo
        if (
            self.agent_context is not None
            and not self.agent_context.get_current_task_id()
        ):
            self.agent_context.create_new_task(
                title=task, description=task, todo_items=todo_items
            )

        # 新增：将任务描述写入 context scratchpad
        if self.agent_context is not None:
            self.agent_context.add_scratchpad_entry(f"任务描述: {task}")
        # 新增：将分解的步骤写入 context scratchpad
        if self.agent_context is not None:
            for i, step in enumerate(steps):
                self.agent_context.add_scratchpad_entry(
                    f"Step {i+1}: {step.get('description', '')}"
                )
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

        # 特殊处理：如果 tool_input 仍然包含 "Generated topics from step 3"，尝试从 _results 中找到 Topic 工具的结果
        if isinstance(tool_input, str) and "Generated topics from step 3" in tool_input:
            # 查找包含 "topic" 或 "Topic" 的结果
            topic_result = None
            for k, v in _results.items():
                if "topic" in k.lower() or "Topic" in k:
                    topic_result = v
                    break

            if topic_result:
                tool_input = str(topic_result)
                print(f"找到 Topic 结果，替换为: {tool_input[:200]}...")
            else:
                print("警告：未找到 Topic 工具的结果")

        print(f"After replacement tool_input: {tool_input} (type: {type(tool_input)})")

        # 执行常规工具
        start_time = time.time()

        try:
            if tool == "Search":
                # 检查搜索查询是否包含相对时间词汇，如果是则先处理时间
                if self._contains_relative_time_terms(tool_input):
                    # 先获取当前时间信息
                    time_result = self._execute_time("current")
                    # 然后执行搜索
                    search_result = self._execute_search(tool_input)
                else:
                    search_result = self._execute_search(tool_input)

                # 将搜索结果写入 context 的 resource 文件
                if self.agent_context is not None and isinstance(search_result, dict):
                    search_items = search_result.get("search_items", [])
                    from app.core.tools.search.base import SearchItem

                    for item in search_items:
                        if isinstance(item, SearchItem):
                            self.agent_context.add_resource_link(
                                title=item.title,
                                url=item.link,
                                description=item.summary or "",
                            )

                # 记录搜索操作到 scratchpad
                if self.agent_context is not None:
                    result = search_result.get("result", str(search_result))
                    self.agent_context.add_scratchpad_entry(
                        f"搜索[{tool_input}]结果: {result}"
                    )

                # 返回字符串格式的结果
                result = search_result.get("result", str(search_result))
            elif tool == "Topic":
                result = self._execute_topic(tool_input)
                if self.agent_context is not None:
                    self.agent_context.add_summary_entry("选题", str(result))
            elif tool == "Summary":
                result = self._execute_summary(tool_input)
                # 记录 summary 结果到 summary
                if self.agent_context is not None:
                    self.agent_context.add_summary_entry("内容摘要", str(result))
            elif tool == "Writer":
                # 自动拼接选题、摘要、搜索信息（如果有）
                topic_info = _results.get("selected_topic", "")
                summary_info = _results.get("Summarize research findings", "")
                search_info = _results.get("Research AI trends", "")
                if topic_info:
                    tool_input = f"Topic: {topic_info}\n"
                if summary_info:
                    tool_input += f"Summary: {summary_info}\n"
                if search_info:
                    tool_input += f"Search: {search_info}\n"
                # 继续后续 Writer 步骤逻辑
                result = self._execute_writer(tool_input)
                # 记录写作结果到 summary
                if self.agent_context is not None:
                    self.agent_context.add_summary_entry("写作结果", str(result))
            elif tool == "Time":
                result = self._execute_time(tool_input)
                # 记录时间工具结果到 scratchpad
                if self.agent_context is not None:
                    self.agent_context.add_scratchpad_entry(
                        f"时间工具[{tool_input}]结果: {result}"
                    )
            elif tool == "LLM":
                result = self.deepseek_llm.invoke(tool_input)
                # 记录 LLM 调用到 scratchpad
                if self.agent_context is not None:
                    self.agent_context.add_scratchpad_entry(
                        f"LLM调用[{tool_input}]结果: {result}"
                    )
        except Exception as e:
            result = f"Error executing {tool}: {str(e)}"

        execution_time = time.time() - start_time
        print("execute_step result:", result)
        print(f"Execution time: {execution_time:.2f}s")

        # 存储结果
        _results[current_step["step_name"]] = str(result)

        # 更新 todo 进度 - 标记当前步骤为完成
        if self.agent_context is not None:
            step_description = current_step.get("description", "")
            if step_description:
                try:
                    self.agent_context.update_todo_progress(
                        [step_description]
                    )  # Changed from single string to list
                    print(f"✓ 更新 todo 进度: {step_description}")
                except Exception as e:
                    print(f"Warning: Failed to update todo progress: {e}")

        return {"results": _results}

    def _execute_search(self, query: str) -> dict:
        """执行搜索操作"""
        try:
            # 检查查询是否包含相对时间词汇，如果是则先处理时间
            if self.time_tool is not None:
                processed_query = self.time_tool.process_time_in_query(query)
            else:
                processed_query = query

            # 执行搜索，获取 SearchItem 列表
            search_items = TavilySearchEngine.perform_search(processed_query)

            # 将 SearchItem 列表转换为字符串格式
            if isinstance(search_items, list):
                from app.core.tools.search.base import SearchItem

                items_str = ", ".join(
                    [
                        f"SearchItem(title='{item.title}', link='{item.link}', summary='{item.summary}')"
                        for item in search_items
                        if isinstance(item, SearchItem)
                    ]
                )
                result_str = f"Search results for '{processed_query}':[{items_str}]"
            else:
                result_str = f"Search results for '{processed_query}': {search_items}"

            return {
                "query": processed_query,
                "search_items": search_items,
                "result": result_str,
            }
        except Exception as e:
            return {
                "query": query,
                "search_items": [],
                "result": f"Search error: {str(e)}",
            }

    def _execute_topic(self, requirement: str) -> str:
        if self.topic_generator is not None:
            if isinstance(requirement, dict):
                requirement_str = requirement.get("requirement", str(requirement))
            else:
                requirement_str = str(requirement)
            topics = self.topic_generator.generate_topics(requirement_str)
            print(f"_execute_topic Topic 工具结果: {topics}")
            if not topics:
                raise RuntimeError("未生成选题，程序终止")
            print("\n可选主题：")
            for i, topic in enumerate(topics, 1):
                print(f"{i}. {topic.title} - {topic.description}")
            try:
                user_input = input(f"请选择主题 (1-{len(topics)}): ")
                idx = int(user_input) - 1
                selected_topic = topics[idx] if 0 <= idx < len(topics) else None
            except EOFError:
                print("输入流已关闭，无法读取输入。")
                selected_topic = None
            except Exception:
                print(f"user_input: {user_input} is not a number")
                selected_topic = None
            if selected_topic:
                print(f"用户选择了: {selected_topic.title}")
                # 返回包含所有信息的字符串
                topic_str = f"标题: {selected_topic.title}\n描述: {selected_topic.description}\n关键词: {selected_topic.keywords}\n目标受众: {selected_topic.target_audience}\n内容类型: {selected_topic.content_type}"
                return topic_str
            else:
                return f"topic selection failed"
        else:
            return f"topic generator not initialized"

    def _execute_summary(self, content: str) -> str:
        """执行内容摘要"""
        try:
            if self.summary_tool is not None:
                # 确保 content 是字符串类型
                if isinstance(content, dict):
                    content_str = content.get("content", str(content))
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
                    topic_str = topic.get("topic", str(topic))
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
                    time_term_str = relative_time_term.get(
                        "time_term", str(relative_time_term)
                    )
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
            "最新",
            "latest",
            "current",
            "当前",
            "this year",
            "今年",
            "recent",
            "最近",
            "now",
            "现在",
            "today",
            "今天",
            "当下",
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
                token_summary = self.documentation_tool.get_token_usage_summary(
                    task_doc
                )
                print(f"✓ Token usage summary: {token_summary}")

            except Exception as e:
                print(f"Warning: Failed to complete task documentation: {e}")

        # 新增：将最终结果写入 context summary
        if self.agent_context is not None:
            self.agent_context.add_summary_entry("最终结果", str(result.content))

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
            for chunk in self.graph.stream(initial_state, stream_mode="values"):
                if "messages" in chunk and chunk["messages"]:
                    last_message = chunk["messages"][-1]
                    if hasattr(last_message, "content"):
                        final_response = last_message.content
        return final_response
