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


def test_planning_agent():
    """批量测试 Planning Agent"""
    
    planning_agent = PlanningAgent()
    test_tasks = [
        "帮我写一份关于人工智能发展趋势的报告"
    ]
    
    print("=" * 60)
    print("Planning Agent 批量测试")
    print("=" * 60)
    
    for i, task in enumerate(test_tasks, 1):
        print(f"\n测试 {i}: {task}")
        try:
            result = planning_agent.test_async_start_chat(task)
            print(f"规划结果:\n{result}\n")
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    test_planning_agent()