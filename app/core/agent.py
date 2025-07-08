import os
from app.core.config import settings
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
from typing import Literal
from typing_extensions import TypedDict



os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY

llm = ChatDeepSeek(model="deepseek-chat")

members = ["chat"]
options = members + ["FINISH"]

class AgentState(MessagesState):
    next: str

class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH"""
    next: Literal[*options]

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

    messages = [{"role": "system", "content": system_prompt},] + state["messages"]

    response = llm.with_structured_output(Router).invoke(messages)

    next_ = response["next"]
    
    if next_ == "FINISH":
        next_ = END
    
    return {"next": next_}

def chat(state: AgentState):
    messages = state["messages"][-1]
    model_response = llm.invoke(messages.content)
    final_response = [HumanMessage(content=model_response.content, name="chat")]   # 这里要添加名称
    return {"messages": final_response}

builder = StateGraph(AgentState)

# builder.add_edge(START, "supervisor")
builder.add_node("supervisor", supervisor)
builder.add_node("chat", chat)

for member in members:
    # 我们希望我们的工人在完成工作后总是向主管"汇报"
    builder.add_edge(member, "supervisor")

builder.add_conditional_edges("supervisor", lambda state: state["next"])

# 添加开始和节点
builder.add_edge(START, "supervisor")

# 编译图
graph = builder.compile()

# def stream_graph_updates(user_input: str):
#     all_chunk = []
#     for chunk in graph.stream({"messages": [HumanMessage(content=user_input)]}, stream_mode="values"):
#         all_chunk.append(chunk)
#     return all_chunk

def startChat(user_input: str):
    response = graph.invoke({"messages": [HumanMessage(content=user_input)], "next": ""})
    print(response['messages'][-1].content)
    ans = response['messages'][-1].content
    return ans
    # stream_graph_updates(user_input)
    # while True:
        # try:
            
        # except:
        #     print("Error: Failed to stream graph updates")
        #     break