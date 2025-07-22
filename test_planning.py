#!/usr/bin/env python3
"""
测试 Planning Agent 的脚本
"""

import os
import sys
from langchain_core.messages import HumanMessage

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.agent.planning import PlanningAgent
from app.core.context import AgentContext, FileContextManager


def test_planning_agent():
    """批量测试 Planning Agent"""
    # 使用测试专用目录，避免污染正式数据
    context_manager = FileContextManager("./test_agent_contexts")
    agent_context = AgentContext(agent_id="test_agent", context_manager=context_manager)
    planning_agent = PlanningAgent(agent_context=agent_context)
    test_tasks = [
        "帮我写一份 RAG 的博客"
    ]
    
    print("=" * 60)
    print("Planning Agent 批量测试")
    print("=" * 60)
    
    for i, task in enumerate(test_tasks, 1):
        print(f"\n测试 {i}: {task}")
        try:
            # 只传递任务描述，planning 内部自动创建 context 任务
            result = planning_agent.test_async_start_chat(task)
            print(f"规划结果:\n{result}\n")
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    test_planning_agent()