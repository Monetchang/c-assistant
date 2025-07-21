#!/usr/bin/env python3
"""
基于文件系统的Agent上下文管理示例
演示如何使用文件系统上下文管理系统
"""

import asyncio
import uuid
from datetime import datetime

from app.core.agent.planning import PlanningAgent
from app.core.context import AgentContext, ContextTools, FileContextManager


async def demo_basic_context_management():
    """演示基本的上下文管理功能"""
    print("=== 基本上下文管理演示 ===")

    # 创建上下文管理器
    context_manager = FileContextManager("./demo_contexts")
    agent_id = "demo_agent_001"

    # 创建Agent上下文
    agent_context = AgentContext(agent_id, context_manager)

    # 创建新任务
    task_id = agent_context.create_new_task(
        title="研究人工智能最新发展",
        description="分析2021-2023年人工智能领域的主要技术突破和发展趋势",
    )
    print(f"创建任务: {task_id}")

    # 添加聊天消息
    agent_context.add_chat_message("user", "请帮我研究一下人工智能的最新发展")
    agent_context.add_chat_message(
        "assistant", "好的，我来帮您分析人工智能的最新发展。首先让我收集一些相关信息。"
    )

    # 更新待办事项进度
    agent_context.update_todo_progress(
        ["开始分析任务需求", "制定研究计划", "收集相关资料"]
    )

    # 添加资源链接
    agent_context.add_resource_link(
        title="OpenAI GPT-4论文",
        url="https://arxiv.org/abs/2303.08774",
        description="GPT-4技术报告",
    )

    agent_context.add_resource_link(
        title="Google PaLM 2论文",
        url="https://arxiv.org/abs/2305.10403",
        description="PaLM 2技术报告",
    )

    # 添加总结条目
    agent_context.add_summary_entry(
        "主要发现",
        "1. 大语言模型在2023年取得重大突破\n2. 多模态AI技术快速发展\n3. AI在科学计算领域应用广泛",
    )

    # 添加临时笔记
    agent_context.add_scratchpad_entry(
        "需要进一步研究的方向：\n- 大语言模型的训练方法\n- 多模态融合技术\n- AI安全性问题"
    )

    # 获取上下文摘要
    summary = agent_context.get_context_summary()
    print(f"任务状态: {summary['status']}")
    print(f"文件数量: {len(summary['files'])}")

    # 获取最近的聊天历史
    history = agent_context.get_recent_chat_history(5)
    print(f"聊天历史数量: {len(history)}")

    # 获取待办事项
    todos = agent_context.get_task_todo_items()
    print(f"待办事项数量: {len(todos)}")

    # 获取资源列表
    resources = agent_context.get_task_resources()
    print(f"资源数量: {len(resources)}")

    return agent_context, task_id


async def demo_context_persistence():
    """演示上下文持久化功能"""
    print("\n=== 上下文持久化演示 ===")

    context_manager = FileContextManager("./demo_contexts")
    agent_id = "demo_agent_002"

    # 创建任务
    agent_context = AgentContext(agent_id, context_manager)
    task_id = agent_context.create_new_task(
        title="代码重构项目", description="重构现有代码库，提高代码质量和可维护性"
    )

    # 添加一些内容
    agent_context.add_chat_message("user", "我需要重构一个Python项目")
    agent_context.add_chat_message("assistant", "我来帮您制定重构计划")
    agent_context.update_todo_progress(["分析现有代码结构", "识别重构机会"])

    # 模拟重新加载上下文
    print("模拟重新加载上下文...")
    new_agent_context = AgentContext(agent_id, context_manager)
    loaded = new_agent_context.load_task(task_id)

    if loaded:
        print("成功重新加载任务上下文")
        summary = new_agent_context.get_context_summary()
        print(f"重新加载后的任务状态: {summary['status']}")

        # 继续添加内容
        new_agent_context.add_chat_message("user", "重构过程中遇到了依赖问题")
        new_agent_context.add_chat_message("assistant", "让我帮您解决依赖问题")
        new_agent_context.add_scratchpad_entry("需要检查requirements.txt文件")
    else:
        print("重新加载失败")


async def demo_context_tools():
    """演示上下文工具功能"""
    print("\n=== 上下文工具演示 ===")

    # 测试关键词提取
    text = (
        "人工智能在2023年取得了重大突破，包括大语言模型、多模态AI和AI安全等领域的发展。"
    )
    keywords = ContextTools.extract_keywords(text, max_keywords=5)
    print(f"提取的关键词: {keywords}")

    # 测试摘要生成
    long_text = """
    人工智能技术在2023年经历了前所未有的发展。大语言模型如GPT-4、Claude-2等展现了强大的自然语言处理能力，
    在多个基准测试中超越了人类水平。多模态AI技术也取得了重要进展，能够同时处理文本、图像、音频等多种数据类型。
    在AI安全方面，研究人员提出了新的对齐方法和安全框架，以确保AI系统的可控性和安全性。
    """
    summary = ContextTools.generate_summary(long_text, max_length=100)
    print(f"生成的摘要: {summary}")

    # 测试Markdown解析
    todo_content = """
    - [ ] 分析代码结构
    - [x] 制定重构计划
    - [ ] 实施重构
    """
    todos = ContextTools.parse_markdown_todo(todo_content)
    print(f"解析的待办事项: {todos}")


async def demo_context_export_import():
    """演示上下文导出导入功能"""
    print("\n=== 上下文导出导入演示 ===")

    context_manager = FileContextManager("./demo_contexts")
    agent_id = "demo_agent_003"

    # 创建任务并添加内容
    agent_context = AgentContext(agent_id, context_manager)
    task_id = agent_context.create_new_task(
        title="机器学习项目", description="开发一个机器学习模型来预测股票价格"
    )

    agent_context.add_chat_message("user", "我想开发一个股票预测模型")
    agent_context.add_chat_message("assistant", "好的，我来帮您设计机器学习模型")
    agent_context.update_todo_progress(["数据收集", "特征工程", "模型训练"])

    # 导出上下文
    context_data = agent_context.export_task_context()
    print(f"导出的上下文数据大小: {len(str(context_data))} 字符")

    # 创建新任务并导入上下文
    new_agent_id = "demo_agent_004"
    new_agent_context = AgentContext(new_agent_id, context_manager)

    success = new_agent_context.import_task_context(context_data)
    if success:
        print("成功导入上下文数据")
        summary = new_agent_context.get_context_summary()
        print(f"导入后的任务标题: {summary['title']}")
    else:
        print("导入失败")


async def demo_context_compression():
    """演示上下文压缩功能（使用 deepseek LLM）"""
    print("\n=== 上下文压缩演示（LLM版） ===")

    # 创建大量上下文数据
    context_data = {
        "task_id": "compression_demo",
        "title": "大数据分析项目",
        "description": "分析大规模数据集",
        "status": "in_progress",
        "files": {
            "history": {
                "content": "这是一个非常长的历史记录文件，包含了很多详细的对话内容。"
                * 100,
                "file_type": "history",
            },
            "summary": {"content": "这是总结文件的内容。" * 50, "file_type": "summary"},
        },
    }

    # 计算原始大小
    original_size = ContextTools.calculate_context_size(context_data)
    print(f"原始上下文大小: {original_size} 字符")

    # 获取 deepseek_llm 实例
    deepseek_llm = PlanningAgent().deepseek_llm

    # 使用 deepseek_llm 压缩上下文
    compressed_data = ContextTools.compress_context_with_llm(
        context_data, deepseek_llm, max_size=1000
    )
    compressed_size = ContextTools.calculate_context_size(compressed_data)
    print(f"压缩后大小: {compressed_size} 字符")
    print(f"压缩率: {(1 - compressed_size / original_size) * 100:.1f}%")


async def demo_context_validation():
    """演示上下文验证功能"""
    print("\n=== 上下文验证演示 ===")

    # 测试有效上下文
    valid_context = {
        "task_id": "valid_task",
        "title": "有效任务",
        "description": "这是一个有效的任务",
        "status": "pending",
        "files": {"todo": {"content": "待办事项内容", "file_type": "todo"}},
    }

    is_valid, errors = ContextTools.validate_context_structure(valid_context)
    print(f"有效上下文验证结果: {is_valid}")
    if errors:
        print(f"错误: {errors}")

    # 测试无效上下文
    invalid_context = {
        "task_id": "invalid_task",
        # 缺少必需字段
        "files": {"todo": "不是字典类型"},
    }

    is_valid, errors = ContextTools.validate_context_structure(invalid_context)
    print(f"无效上下文验证结果: {is_valid}")
    if errors:
        print(f"错误: {errors}")


async def main():
    """主函数"""
    print("基于文件系统的Agent上下文管理演示")
    print("=" * 50)

    try:
        # 运行各种演示
        await demo_basic_context_management()
        await demo_context_persistence()
        await demo_context_tools()
        await demo_context_export_import()
        await demo_context_compression()
        await demo_context_validation()

        print("\n" + "=" * 50)
        print("所有演示完成！")
        print("请查看 ./demo_contexts 目录中的文件结构")

    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
