import os
from app.core.config import settings
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, MessagesState, START, END
from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
from typing import Any, Literal, Optional
from typing_extensions import TypedDict
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from app.db.mongodb import get_database
from app.api.deps import get_message_collection
from app.crud.crud_chat_message_mongo import CRUDChatMessageMongo

os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY

llm = ChatDeepSeek(model="deepseek-chat")

members = ["chat"]
options = ["chat", "FINISH"]

class AgentState(MessagesState):
    next: str

class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH"""
    next: Literal["chat", "FINISH"]

def supervisor(state: AgentState):
    system_prompt = (
        "You are a supervisor tasked with managing a conversation between the"
        f" following workers: {members}.\n\n"
        "Each worker has a specific role:\n"
        "- chat: Responds directly to user inputs using natural language.\n"
        "Given the following user request, respond with the worker to act next."
        " Each worker will perform a task and respond with their results and status."
        " When finished, respond with FINISH."
    )

    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = llm.with_structured_output(Router).invoke(messages)

    next_ = response["next"]
    
    if next_ == "FINISH":
        next_ = END
    
    return {"next": next_}

def chat(state: AgentState):
    messages = state["messages"][-1]
    model_response = llm.invoke([messages])
    return {"messages": [model_response]}

def create_graph():
    builder = StateGraph(AgentState)
    
    builder.add_node("supervisor", supervisor)
    builder.add_node("chat", chat)

    for member in members:
        builder.add_edge(member, "supervisor")

    builder.add_conditional_edges("supervisor", lambda state: state["next"])
    builder.add_edge(START, "supervisor")
    
    return builder.compile()

async def save_chat_to_mongodb(
    *,
    thread_id: str, 
    user_input: str, 
    assistant_response: str,
    collection: AsyncIOMotorCollection = Depends(get_message_collection),
) -> Any:
    """保存聊天记录到 MongoDB"""
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

async def async_start_chat(
    *,
    user_input: str, 
    thread_id: str,
    collection: AsyncIOMotorCollection = Depends(get_message_collection),
) -> str:
    """启动聊天并持久化到 MongoDB"""
    try:
        # 获取同 thread_id 的所有历史消息
        crud_message = CRUDChatMessageMongo(collection)
        history_messages = await crud_message.get_by_chat(thread_id)
        
        # 构建完整的消息列表
        all_messages = []
        
        # 添加历史消息
        for msg in history_messages:
            if msg.role == "user":
                all_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                all_messages.append(SystemMessage(content=msg.content))
        
        # 添加当前用户输入
        current_user_message = HumanMessage(content=user_input)
        all_messages.append(current_user_message)
        
        # 创建图并编译
        graph = create_graph()
        
        # 流式处理聊天，传入完整的历史消息
        final_response = ""
        for chunk in graph.stream(
            {"messages": all_messages, "next": ""},
            stream_mode="values"
        ):
            if "messages" in chunk and chunk["messages"]:
                last_message = chunk["messages"][-1]
                if hasattr(last_message, 'content'):
                    final_response = last_message.content
                    print(f"Chat response: {final_response}")

        # 保存聊天记录到 MongoDB
        if final_response and collection is not None:
            await save_chat_to_mongodb(
                thread_id = thread_id, 
                user_input = user_input, 
                assistant_response = final_response, 
                collection = collection
            )
        return final_response
        
    except Exception as e:
        print(f"Error in start_chat: {e}")
        return f"Error: {str(e)}"
