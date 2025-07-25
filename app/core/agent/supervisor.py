import os
from typing import Any, Dict, List, Literal, Optional, Sequence

from fastapi import Depends
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, MessagesState, StateGraph
from motor.motor_asyncio import AsyncIOMotorCollection
from typing_extensions import TypedDict

from app.api.deps import get_message_collection
from app.core.agent.base import AgentBase
from app.core.agent.planning import WriterPlanningAgent
from app.core.agent.search import SearchAgent
from app.core.config import settings
from app.core.prompt.supervisor import SYSTEM_PROMPT
from app.crud.crud_chat_message_mongo import CRUDChatMessageMongo

# 定义常量
MEMBERS = ["chat", "search", "writer_planning"]
OPTIONS = ["chat", "search", "writer_planning", "FINISH"]


class AgentState(MessagesState):
    """代理状态类，继承自MessagesState并添加next字段"""

    next: str


class Router(TypedDict):
    """路由器类型定义，用于决定下一步操作"""

    next: Literal["chat", "search", "planning", "FINISH"]


class Supervisor(AgentBase):
    """监督者代理类，负责协调不同工作节点的执行"""

    graph: Optional[Any] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure deepseek_llm is initialized
        if self.deepseek_llm is None:
            os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
            self.deepseek_llm = ChatDeepSeek(model="deepseek-chat")
        self.graph = self.initialize_agent()

    def initialize_agent(self) -> Any:
        """
        初始化代理图

        Returns:
            编译后的状态图
        """
        builder = StateGraph(AgentState)

        # 添加节点
        builder.add_node("supervisor", self.supervisor)
        builder.add_node("chat", self.chat)
        builder.add_node("search", SearchAgent().initialize_agent())
        builder.add_node("writer_planning", self.writer_planning)

        # 添加边
        for member in MEMBERS:
            builder.add_edge(member, "supervisor")

        # 添加条件边
        builder.add_conditional_edges("supervisor", lambda state: state["next"])
        builder.add_edge(START, "supervisor")

        return builder.compile()

    async def async_start_chat(
        self,
        *,
        user_input: str,
        thread_id: str,
        collection: AsyncIOMotorCollection = Depends(get_message_collection),
    ) -> str:
        """
        启动聊天并持久化到 MongoDB

        Args:
            user_input: 用户输入
            thread_id: 线程ID
            collection: MongoDB集合

        Returns:
            助手的回复
        """
        try:
            # 获取历史消息
            crud_message = CRUDChatMessageMongo(collection)
            history_messages = await crud_message.get_by_chat(thread_id)

            # 构建完整的消息列表
            all_messages = self._build_message_list(history_messages, user_input)

            # 创建图并编译
            if not self.graph:
                self.graph = self.initialize_agent()

            # 流式处理聊天
            final_response = await self._process_chat_stream(all_messages)

            # 保存聊天记录
            if final_response and collection is not None:
                await self._save_chat_to_mongodb(
                    thread_id=thread_id,
                    user_input=user_input,
                    assistant_response=final_response,
                    collection=collection,
                )

            return final_response

        except Exception as e:
            print(f"Error in start_chat: {e}")
            return f"Error: {str(e)}"

    def _build_message_list(
        self, history_messages: List[Any], user_input: str
    ) -> List[AnyMessage]:
        """
        构建消息列表

        Args:
            history_messages: 历史消息
            user_input: 用户输入

        Returns:
            完整的消息列表
        """
        all_messages = []

        # 添加历史消息
        for msg in history_messages:
            if msg.role == "user":
                all_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                all_messages.append(AIMessage(content=msg.content))

        # 添加当前用户输入
        all_messages.append(HumanMessage(content=user_input))

        return all_messages

    async def _process_chat_stream(self, all_messages: List[AnyMessage]) -> str:
        """
        处理聊天流

        Args:
            all_messages: 所有消息

        Returns:
            最终回复
        """
        final_response = ""

        # 创建初始状态，包含next字段
        initial_state = AgentState(
            messages=all_messages, next="supervisor"  # 设置初始next值
        )

        if self.graph:
            for chunk in self.graph.stream(
                initial_state, stream_mode="values", print_mode="debug"
            ):
                if "messages" in chunk and chunk["messages"]:
                    last_message = chunk["messages"][-1]
                    if hasattr(last_message, "content"):
                        final_response = last_message.content

        return final_response

    async def _save_chat_to_mongodb(
        self,
        *,
        thread_id: str,
        user_input: str,
        assistant_response: str,
        collection: AsyncIOMotorCollection,
    ) -> None:
        """
        保存聊天记录到 MongoDB

        Args:
            thread_id: 线程ID
            user_input: 用户输入
            assistant_response: 助手回复
            collection: MongoDB集合
        """
        try:
            crud_message = CRUDChatMessageMongo(collection)

            # 保存用户消息
            user_message = {
                "role": "user",
                "content": user_input,
            }
            await crud_message.create_with_chat(user_message, thread_id)

            # 保存助手回复
            assistant_message = {
                "role": "assistant",
                "content": assistant_response,
            }
            await crud_message.create_with_chat(assistant_message, thread_id)

            print(f"Chat saved to MongoDB for thread: {thread_id}")

        except Exception as e:
            print(f"Error saving chat to MongoDB: {e}")

    def supervisor(self, state: AgentState) -> Dict[str, str]:
        """
        监督者节点，决定下一步操作

        Args:
            state: 当前状态

        Returns:
            包含下一步操作的状态
        """
        system_prompt = SYSTEM_PROMPT
        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        assert self.deepseek_llm is not None, "deepseek_llm should be initialized"
        response = self.deepseek_llm.with_structured_output(Router).invoke(messages)

        next_ = response["next"]

        if next_ == "FINISH":
            next_ = END

        return {"next": next_}

    def chat(self, state: AgentState) -> Dict[str, Sequence[AnyMessage]]:
        """
        聊天节点，生成回复

        Args:
            state: 当前状态

        Returns:
            包含回复消息的状态
        """
        assert self.deepseek_llm is not None, "deepseek_llm should be initialized"
        model_response = self.deepseek_llm.invoke(state["messages"])
        final_response = [HumanMessage(content=model_response.content, name="chat")]
        return {"messages": final_response}

    def writer_planning(self, state: AgentState) -> Dict[str, Sequence[AnyMessage]]:
        """
        创作规划节点，处理复杂的创作类任务

        Args:
            state: 当前状态

        Returns:
            包含创作规划结果的状态
        """
        try:
            # 获取用户输入
            user_input = ""
            for message in state["messages"]:
                if isinstance(message, HumanMessage):
                    user_input = message.content
                    break

            if not user_input:
                return {
                    "messages": [
                        AIMessage(content="No user input found", name="planning")
                    ]
                }

            # 创建创作规划代理并执行任务
            planning_agent = WriterPlanningAgent()

            # 使用创作规划代理的测试方法
            execution_result = planning_agent.test_async_start_chat(str(user_input))

            if execution_result:
                # 生成最终回复
                final_response = f"创作任务完成: {execution_result}"
            else:
                final_response = "创作任务执行失败"

            return {
                "messages": [AIMessage(content=final_response, name="writer_planning")]
            }

        except Exception as e:
            error_message = f"创作规划过程中出现错误: {str(e)}"
            return {
                "messages": [AIMessage(content=error_message, name="writer_planning")]
            }

    def _generate_planning_response(
        self, execution_result: Dict[str, Any], original_task: str
    ) -> str:
        """
        根据执行结果生成最终回复

        Args:
            execution_result: 执行结果
            original_task: 原始任务

        Returns:
            格式化的回复
        """
        try:
            results = execution_result.get("results", {})

            # 构建回复内容
            response_parts = [f"任务完成: {original_task}\n"]

            for step_name, step_result in results.items():
                if step_result.get("status") == "success":
                    if "output" in step_result:
                        response_parts.append(
                            f"**{step_name}**: {step_result['output']}\n"
                        )
                    elif "results" in step_result:
                        response_parts.append(
                            f"**{step_name}**: 搜索完成，找到相关信息\n"
                        )
                else:
                    response_parts.append(
                        f"**{step_name}**: 执行失败 - {step_result.get('error', '未知错误')}\n"
                    )

            return "\n".join(response_parts)

        except Exception as e:
            return f"生成回复时出现错误: {str(e)}"
