import json
import os
import re
import time
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.core.agent.base import AgentBase
from app.core.config import settings
from app.core.context import AgentContext
from app.core.prompt.planning import PLANNING_PROMPT, SOLVE_PROMPT
from app.core.tools.documentation import DocumentationTool
from app.core.tools.markdown_saver import MarkdownSaver
from app.core.tools.search.tavily_search import TavilySearchEngine
from app.core.tools.summary import SummaryTool
from app.core.tools.time import TimeTool
from app.core.tools.topic import TopicGenerator
from app.core.tools.topic_selection import TopicSelectionTool
from app.core.tools.writer import ArticleWriterTool, OutlineTool, WriterTool


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


class WriterPlanningAgent(AgentBase):
    """规划代理类，用于任务规划和步骤执行"""

    # 定义工具属性
    tavily_search: Optional[Any] = None
    topic_generator: Optional[Any] = None
    summary_tool: Optional[Any] = None
    writer_tool: Optional[Any] = None
    outline_tool: Optional[OutlineTool] = None
    article_writer_tool: Optional[ArticleWriterTool] = None
    time_tool: Optional[Any] = None
    documentation_tool: Optional[Any] = None
    topic_selection_tool: Optional[TopicSelectionTool] = None
    graph: Optional[Any] = None
    agent_context: Optional[AgentContext] = None
    markdown_saver: Optional[MarkdownSaver] = None  # 显式声明

    def __init__(self, agent_context: Optional[AgentContext] = None, **kwargs):
        super().__init__(**kwargs)
        self.agent_context = agent_context or AgentContext(agent_id="default")
        # 确保 deepseek_llm 初始化
        if not hasattr(self, "deepseek_llm") or self.deepseek_llm is None:
            os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
            self.deepseek_llm = ChatDeepSeek(model="deepseek-chat")
        object.__setattr__(
            self, "markdown_saver", MarkdownSaver()
        )  # 兼容 pydantic BaseModel
        self._initialize_tools()  # 只初始化其他工具
        self.graph = self.initialize_agent()

    def _initialize_tools(self) -> None:
        """初始化各种工具"""
        try:
            self.tavily_search = TavilySearchEngine()
            self.topic_generator = TopicGenerator()
            self.summary_tool = SummaryTool()
            self.writer_tool = WriterTool()
            self.outline_tool = OutlineTool()
            self.article_writer_tool = ArticleWriterTool()
            self.time_tool = TimeTool()
            self.documentation_tool = DocumentationTool()
            self.topic_selection_tool = TopicSelectionTool()
            # self.markdown_saver = MarkdownSaver()  # 移除，已在 __init__ 初始化
            print("markdown_saver initialized:", hasattr(self, "markdown_saver"))
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

        # 1. 生成 LLM 规划内容创作主流程（不包含 MarkdownSaver）
        prompt_content = PLANNING_PROMPT.format(task=task)
        messages = [SystemMessage(content=prompt_content)]
        if self.deepseek_llm is not None:
            response = self.deepseek_llm.invoke(messages)
            steps = self._extract_steps_from_json(str(response.content))
        else:
            steps = []

        # 2. 检查是否已经存在 MarkdownSaver 步骤，如果没有则在最后一个 ArticleWriter 后插入
        has_markdown_saver = any(step.get("tool") == "MarkdownSaver" for step in steps)
        if not has_markdown_saver:
            last_writer_idx = None
            for i, step in enumerate(steps):
                if step.get("tool") == "ArticleWriter":
                    last_writer_idx = i
            if last_writer_idx is not None:
                markdown_step = {
                    "step": len(steps) + 1,
                    "step_name": "Save as Markdown",
                    "description": "Save the final article as a markdown file",
                    "tool": "MarkdownSaver",
                    "tool_input": f"Article from step {last_writer_idx+1}",
                    "step_type": "NEEDS_SAVE",
                }
                steps.insert(last_writer_idx + 1, markdown_step)

        # 用 step 的 description、step_name 和 tool 初始化 todo（排除 MarkdownSaver）
        todo_items = []
        step_execution_info = {}  # 记录每个 step 的执行信息

        for step in steps:
            tool = step.get("tool", "")
            # 跳过 MarkdownSaver 步骤，不添加到 todo 中
            if tool == "MarkdownSaver":
                continue
            step_name = step.get("step_name", "")
            description = step.get("description", "")
            todo_item = f"{step_name} ({tool}): {description}"
            todo_items.append(todo_item)

            # 初始化 step 执行信息
            step_execution_info[step_name] = {
                "tool": tool,
                "description": description,
                "status": "pending",
                "result": "",
                "execution_time": 0,
            }

        # 如果当前没有 task，则创建新任务，并用 steps 初始化 todo
        if (
            self.agent_context is not None
            and not self.agent_context.get_current_task_id()
        ):
            self.agent_context.create_new_task(
                title=task, description=task, todo_items=todo_items
            )
            # 删除：将 step 执行信息保存到 context scratchpad
            # self.agent_context.add_scratchpad_entry(
            #     f"步骤执行信息: {json.dumps(step_execution_info, ensure_ascii=False)}"
            # )

        # 删除：将任务描述写入 context scratchpad
        # if self.agent_context is not None:
        #     self.agent_context.add_scratchpad_entry(f"任务描述: {task}")
        # 删除：将分解的步骤写入 context scratchpad
        # if self.agent_context is not None:
        #     for i, step in enumerate(steps):
        #         self.agent_context.add_scratchpad_entry(
        #             f"Step {i+1}: {step.get('description', '')}"
        #         )
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

        # 初始化 result 变量
        result = ""

        try:
            if tool == "Search":
                # 检查搜索查询是否包含相对时间词汇，如果是则先处理时间
                if self._contains_relative_time_terms(tool_input):
                    # 先获取当前时间信息
                    self._execute_time("current")
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
                result = self._execute_topic(tool_input, state.get("task"))
                if self.agent_context is not None:
                    self.agent_context.add_summary_entry("选题", str(result))
            elif tool == "Summary":
                result = self._execute_summary(tool_input)
                # 记录 summary 结果到 summary
                if self.agent_context is not None:
                    self.agent_context.add_summary_entry("内容摘要", str(result))
            elif tool == "Outline":
                # 尝试从之前步骤的结果中获取选题信息
                topic_info = _results.get("selected_topic", "")
                if not topic_info:
                    # 如果没有找到选题信息，尝试从其他可能的结果中获取
                    for k, v in _results.items():
                        if "topic" in k.lower() or "Topic" in k:
                            topic_info = v
                            break

                # 如果找到了选题信息，使用它；否则使用 tool_input
                actual_topic = topic_info if topic_info else tool_input
                result = self._execute_outline(actual_topic)
                # 移除大纲结果到 summary 的写入
                # if self.agent_context is not None:
                #     self.agent_context.add_summary_entry("文章大纲", str(result))
            elif tool == "ArticleWriter":
                # 自动拼接选题、摘要、搜索信息（如果有）
                topic_info = _results.get("selected_topic", "")
                summary_info = _results.get("Summarize research findings", "")
                search_info = _results.get("Research AI trends", "")
                outline_info = _results.get("Generate article outline", "")
                if topic_info:
                    tool_input = f"Topic: {topic_info}\n"
                if summary_info:
                    tool_input += f"Summary: {summary_info}\n"
                if search_info:
                    tool_input += f"Search: {search_info}\n"
                if outline_info:
                    tool_input += f"Outline: {outline_info}\n"
                # 继续后续 ArticleWriter 步骤逻辑
                print("--------------------------------")
                print(f"ArticleWriter _results: {_results}")
                print("--------------------------------")
                print(f"ArticleWriter 工具输入: {tool_input}")

                result = self._execute_article_writer(tool_input)
                # 移除写作结果到 summary 的写入
                # if self.agent_context is not None:
                #     self.agent_context.add_summary_entry("写作结果", str(result))
            elif tool == "Writer":
                # 保持向后兼容
                result = self._execute_writer(tool_input)
                # 移除写作结果到 summary 的写入
                # if self.agent_context is not None:
                #     self.agent_context.add_summary_entry("写作结果", str(result))
            elif tool == "Time":
                result = self._execute_time(tool_input)
                # 只在时间工具时写入 summary
                if self.agent_context is not None:
                    self.agent_context.add_summary_entry(
                        f"时间工具[{tool_input}]", str(result)
                    )
            elif tool == "MarkdownSaver":
                # 获取上一步 ArticleWriter 的内容
                writer_result = None
                # 尝试从 _results 中获取上一步 ArticleWriter 的输出
                for step in reversed(state["steps"][: _step - 1]):
                    if step.get("tool") == "ArticleWriter":
                        writer_result = _results.get(step.get("step_name"), None)
                        if writer_result:
                            break
                article_content = writer_result or tool_input
                filename = f"{state.get('task', 'article')}.md"
                print(f"将保存 markdown 文件: {filename}")
                print(f"内容预览: {str(article_content)[:100]}")
                if self.markdown_saver:
                    path = self.markdown_saver.save(str(article_content), filename)
                    print(f"已保存到: {path}")
                    result = f"Markdown saved to: {path}"
                else:
                    result = "MarkdownSaver not initialized"
            else:
                # 处理未知的工具类型
                result = f"Unknown tool: {tool}"
        except Exception as e:
            result = f"Error executing {tool}: {str(e)}"

        execution_time = time.time() - start_time
        print("execute_step result:", result)
        print(f"Execution time: {execution_time:.2f}s")

        # 存储结果
        _results[current_step["step_name"]] = str(result)

        # 记录步骤执行完成后的最终信息
        if self.agent_context is not None:
            step_name = current_step.get("step_name", "")
            step_description = current_step.get("description", "")

            # 更新 todo 进度 - 标记当前步骤为完成
            if step_description:
                try:
                    self.agent_context.update_todo_progress([step_description])
                    print(f"✓ 更新 todo 进度: {step_description}")
                except Exception as e:
                    print(f"Warning: Failed to update todo progress: {e}")

            # 记录步骤执行完成信息（除 ArticleWriter 步骤外）
            if tool != "ArticleWriter":
                step_completion_info = {
                    "step_name": step_name,
                    "tool": tool,
                    "description": step_description,
                    "status": "completed",
                    "result": str(result)[:500],  # 限制结果长度
                    "execution_time": round(execution_time, 2),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                # 以文本和 JSON 两种形式追加到 todo.md
                todo_append_text = f"\n---\n步骤完成: {step_name} ({tool})\n描述: {step_description}\n状态: completed\n结果: {str(result)[:200]}...\n执行时间: {round(execution_time, 2)}s\n时间: {step_completion_info['timestamp']}\nJSON: {json.dumps(step_completion_info, ensure_ascii=False)}\n"
                # 追加到 todo.md
                agent_id = self.agent_context.agent_id
                task_id = self.agent_context.get_current_task_id()
                if agent_id and task_id:
                    self.agent_context.context_manager.append_to_task_file(
                        agent_id, task_id, "todo", todo_append_text
                    )

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

    def _execute_topic(self, requirement: str, user_query: Optional[str] = None) -> str:
        if self.topic_generator is not None:
            if isinstance(requirement, dict):
                requirement_str = requirement.get("requirement", str(requirement))
            else:
                requirement_str = str(requirement)
            topics = self.topic_generator.generate_topics(
                requirement_str, user_query or ""
            )
            print(f"_execute_topic Topic 工具结果: {topics}")
            if not topics:
                raise RuntimeError("未生成选题，程序终止")
            print("\n可选主题：")
            for i, topic in enumerate(topics, 1):
                print(f"{i}. {topic.title} - {topic.description}")
            while True:
                try:
                    user_input = input(f"请选择主题 (1-{len(topics)}): ").strip()
                    if not user_input:  # 如果用户直接按回车（空输入），则重新提示
                        continue  # 忽略回车，继续循环

                    idx = int(user_input) - 1  # 尝试转换为整数
                    if 0 <= idx < len(topics):  # 检查索引是否有效
                        selected_topic = topics[idx]
                        break  # 输入有效，退出循环
                    else:
                        print(f"请输入 1-{len(topics)} 之间的数字！")
                except ValueError:  # 如果输入的不是数字
                    print("请输入有效的数字！")
                except Exception as e:  # 其他未知错误
                    print(f"发生错误: {e}")
                    selected_topic = (
                        topics[0] if topics else None
                    )  # 出错时默认选择第一个
                    break
            if selected_topic:
                print(f"用户选择了: {selected_topic.title}")
                topic_str = f"标题: {selected_topic.title}\n描述: {selected_topic.description}\n关键词: {selected_topic.keywords}\n目标受众: {selected_topic.target_audience}\n内容类型: {selected_topic.content_type}"
                return topic_str
            else:
                raise RuntimeError("用户选择失败，程序终止")
        else:
            raise RuntimeError("未初始化 topic_generator，程序终止")

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
                return "Summary tool not initialized"

        except Exception as e:
            return f"Summary error: {str(e)}"

    def _execute_outline(self, topic: str) -> str:
        """执行大纲生成"""
        try:
            if self.outline_tool is not None:
                # 确保 topic 是字符串类型
                if isinstance(topic, dict):
                    topic_str = topic.get("topic", str(topic))
                else:
                    topic_str = str(topic)

                # 提取选题标题（如果包含完整选题信息）
                if "标题:" in topic_str:
                    lines = topic_str.split("\n")
                    for line in lines:
                        if line.startswith("标题:"):
                            topic_str = line.replace("标题:", "").strip()
                            break

                # 生成大纲
                print(f"_execute_outline Outline 工具输入: {topic_str}")
                outline = self.outline_tool.create_outline(topic_str)

                # 显示大纲并等待用户确认
                print("\n=== 生成的文章大纲 ===")
                print(f"标题: {outline.title}")
                print(f"引言: {outline.introduction}")
                print("\n章节结构:")
                for i, section in enumerate(outline.sections, 1):
                    print(f"  {i}. {section.get('title', '')}")
                    print(f"     {section.get('description', '')}")
                print(f"\n结论: {outline.conclusion}")

                # 用户确认
                while True:
                    user_input = input("\n是否确认使用此大纲？(y/n): ").strip().lower()
                    if user_input in ["y", "yes", "是", "确认"]:
                        print("✓ 大纲已确认，继续执行...")
                        return f"Confirmed outline for '{topic_str}': {outline.title}"
                    elif user_input in ["n", "no", "否", "不"]:
                        print("✗ 大纲被拒绝，需要重新生成")
                        return f"Outline rejected for '{topic_str}'"
                    else:
                        print("请输入 y/yes/是/确认 或 n/no/否/不")
            else:
                return "Outline tool not initialized"
        except Exception as e:
            return f"Outline generation error: {str(e)}"

    def _execute_article_writer(self, topic: str) -> str:
        """执行文章写作"""
        try:
            if self.article_writer_tool is not None:
                # 确保 topic 是字符串类型
                if isinstance(topic, dict):
                    topic_str = topic.get("topic", str(topic))
                else:
                    topic_str = str(topic)

                # 从上下文获取大纲信息
                outline_info = ""
                if self.agent_context is not None:
                    # 尝试从 summary 中获取大纲信息
                    summary_content = self.agent_context.get_task_file_content(
                        "summary"
                    )
                    if summary_content and "文章大纲" in summary_content:
                        outline_info = summary_content

                # 如果没有大纲信息，使用默认大纲
                if not outline_info:
                    outline = (
                        self.outline_tool.create_outline(topic_str)
                        if self.outline_tool
                        else None
                    )
                    if outline:
                        outline_info = (
                            f"Outline: {outline.title}\n{outline.introduction}\n"
                        )
                        for section in outline.sections:
                            outline_info += f"- {section.get('title', '')}: {section.get('description', '')}\n"
                        outline_info += f"Conclusion: {outline.conclusion}"

                # 写文章
                article = self.article_writer_tool.write_article_from_topic(topic_str)
                return f"Article for '{topic_str}': {article}"
            else:
                return "ArticleWriter tool not initialized"
        except Exception as e:
            return f"Article writing error: {str(e)}"

    def _execute_writer(self, topic: str) -> str:
        """执行文章写作（向后兼容）"""
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
                return "Writer tool not initialized"
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
                return "Time tool not initialized"
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
