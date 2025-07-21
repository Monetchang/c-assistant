# 基于文件系统的Agent上下文管理系统

## 概述

本项目实现了一个基于文件系统的Agent上下文管理方案，充分利用文件系统的优势，实现高效、可扩展、可恢复的上下文管理。通过将Agent的重要信息、任务进度、历史对话、外部资源等以文件形式存储和管理，突破了传统上下文窗口的限制。

## 核心特性

### 1. 结构化分层存储
- **根目录**: 每个Agent有独立的工作空间（如 `/agent_x/`）
- **任务分层**: 每个任务/子任务一个文件夹（如 `/agent_x/task_20240601/`）
- **文件类型**: 
  - `todo.md` - 任务目标、进度、待办事项
  - `history.md` - 对话历史、决策记录
  - `resource_links.txt` - 外部资源URL、引用
  - `summary.md` - 阶段性总结、要点
  - `scratchpad.md` - 临时笔记、推理过程

### 2. 可恢复的压缩与引用
- **信息压缩**: 对大文档、网页等，仅存储URL或摘要，必要时再拉取原文
- **引用机制**: Agent在上下文中引用文件路径或URL，按需"解压"内容
- **自动摘要**: Agent可自动生成摘要文件，快速回顾关键信息

### 3. 版本控制与协作
- **版本快照**: 每次重要变更自动保存快照，支持回溯和对比
- **多Agent协作**: 通过共享文件夹实现信息共享、任务分工
- **变更日志**: 记录每次文件修改的原因和内容，便于追踪

### 4. Agent主动"用文件"思维
- **任务规划**: Agent自动生成和维护 `todo.md`，随时更新目标和进度
- **目标复述**: 每次推理前从 `todo.md` 读取目标，防止"迷失"
- **阶段总结**: 任务完成后自动生成 `summary.md`，为后续任务提供参考
- **自我纠错**: 通过对比不同版本的文件，发现并修正推理偏差

## 系统架构

```
app/
├── core/
│   └── context/
│       ├── __init__.py
│       ├── file_context_manager.py    # 文件系统上下文管理器
│       ├── agent_context.py           # Agent上下文管理类
│       └── context_tools.py           # 上下文管理工具
├── models/
│   └── chat_message_enhanced.py       # 增强的聊天消息模型
├── crud/
│   └── crud_chat_message_enhanced.py  # 增强的CRUD操作
└── schemas/
    └── chat_message.py                # 聊天消息模式
```

## 核心组件

### 1. FileContextManager
文件系统上下文管理器，负责：
- 创建和管理Agent工作空间
- 管理任务文件夹结构
- 处理文件的创建、更新、版本控制
- 提供上下文数据的持久化

### 2. AgentContext
Agent上下文管理类，提供：
- 高级上下文管理功能
- 任务创建和加载
- 聊天消息管理
- 进度跟踪和状态更新

### 3. ContextTools
上下文管理工具，提供：
- 关键词提取和摘要生成
- Markdown格式解析
- 上下文压缩和验证
- 数据导入导出功能

### 4. 增强的数据模型
- `ChatMessageEnhanced`: 增强的聊天消息模型
- `ThreadEnhanced`: 增强的线程模型
- `ContextSnapshot`: 上下文快照模型
- `TaskProgress`: 任务进度模型
- `ContextFileReference`: 上下文文件引用模型

## 使用方法

### 基本使用

```python
from app.core.context import FileContextManager, AgentContext

# 创建上下文管理器
context_manager = FileContextManager("./agent_contexts")

# 创建Agent上下文
agent_context = AgentContext("agent_001", context_manager)

# 创建新任务
task_id = agent_context.create_new_task(
    title="研究项目",
    description="进行某项研究"
)

# 添加聊天消息
agent_context.add_chat_message("user", "请帮我分析这个问题")
agent_context.add_chat_message("assistant", "好的，我来帮您分析")

# 更新进度
agent_context.update_todo_progress(["开始分析", "收集数据"])

# 添加资源
agent_context.add_resource_link(
    title="相关论文",
    url="https://example.com/paper",
    description="重要参考资料"
)
```

### 高级功能

```python
# 获取上下文摘要
summary = agent_context.get_context_summary()

# 获取聊天历史
history = agent_context.get_recent_chat_history(10)

# 获取待办事项
todos = agent_context.get_task_todo_items()

# 标记待办事项完成
agent_context.mark_todo_completed("分析数据")

# 导出上下文
context_data = agent_context.export_task_context()

# 导入上下文
new_agent_context.import_task_context(context_data)
```

### 工具函数使用

```python
from app.core.context import ContextTools

# 关键词提取
keywords = ContextTools.extract_keywords("这是一段文本", max_keywords=5)

# 摘要生成
summary = ContextTools.generate_summary("长文本内容", max_length=200)

# 上下文压缩
compressed = ContextTools.compress_context(context_data, max_size=10000)

# 上下文验证
is_valid, errors = ContextTools.validate_context_structure(context_data)
```

## 文件结构示例

```
agent_contexts/
├── agent_001/
│   ├── task_20240601_001/
│   │   ├── metadata.json
│   │   ├── todo.md
│   │   ├── history.md
│   │   ├── resource_links.txt
│   │   ├── summary.md
│   │   ├── scratchpad.md
│   │   ├── todo_v1.md
│   │   └── history_v1.md
│   └── task_20240601_002/
│       └── ...
├── agent_002/
│   └── ...
└── shared/
    └── common_resources/
```

## 典型工作流

### 1. 新任务启动
```python
# 创建新任务
task_id = agent_context.create_new_task(
    title="数据分析项目",
    description="分析用户行为数据"
)

# 自动创建基础文件结构
# - todo.md: 包含任务目标和待办事项
# - history.md: 记录任务创建
# - resource_links.txt: 准备收集资源
# - summary.md: 准备记录总结
# - scratchpad.md: 准备记录临时想法
```

### 2. 信息收集
```python
# 添加外部资源（仅存储URL）
agent_context.add_resource_link(
    title="用户行为数据集",
    url="https://example.com/dataset",
    description="包含用户点击、浏览等行为数据"
)

# 重要内容摘要写入summary.md
agent_context.add_summary_entry(
    "数据概览",
    "数据集包含100万用户的行为记录，时间跨度3个月"
)
```

### 3. 任务推进
```python
# 每步决策、对话写入history.md
agent_context.add_chat_message("assistant", "开始数据预处理")

# 进度更新同步到todo.md
agent_context.update_todo_progress(["数据清洗完成", "特征工程进行中"])

# 临时想法记录到scratchpad.md
agent_context.add_scratchpad_entry("发现数据中存在异常值，需要处理")
```

### 4. 上下文恢复
```python
# 需要回顾时，按需读取相关文件
todo_content = agent_context.get_task_file_content("todo")
history_content = agent_context.get_task_file_content("history")
```

### 5. 任务完成
```python
# 生成最终总结
agent_context.add_summary_entry(
    "项目总结",
    "成功完成了用户行为分析，发现了关键模式"
)

# 更新任务状态
agent_context.update_task_status("completed")
```

## 优势特点

### 1. 无限扩展
- 不受传统上下文窗口大小限制
- 可以存储任意数量的历史信息
- 支持大文档和复杂任务

### 2. 结构化管理
- 清晰的文件组织结构
- 类型化的内容管理
- 便于检索和导航

### 3. 可恢复性
- 完整的版本历史
- 支持断点续传
- 数据备份和恢复

### 4. 可协作性
- 多Agent共享信息
- 支持团队协作
- 版本冲突解决

### 5. 智能管理
- Agent主动维护文件
- 自动摘要和压缩
- 智能引用和链接

## 性能优化

### 1. 懒加载
- 按需读取文件内容
- 避免一次性加载所有数据
- 支持增量更新

### 2. 压缩策略
- 自动压缩大文件
- 保留关键信息
- 平衡存储和性能

### 3. 缓存机制
- 热点数据缓存
- 减少文件I/O
- 提高响应速度

## 扩展性

### 1. 插件系统
- 支持自定义文件类型
- 可扩展的解析器
- 灵活的存储后端

### 2. 多后端支持
- 本地文件系统
- 云存储（S3、OSS等）
- 分布式文件系统

### 3. 集成能力
- 与现有系统集成
- 支持多种数据格式
- 提供标准API

## 最佳实践

### 1. 文件命名
- 使用有意义的文件名
- 遵循命名约定
- 避免特殊字符

### 2. 版本管理
- 定期创建快照
- 保留重要版本
- 清理旧版本

### 3. 数据备份
- 定期备份重要数据
- 使用多种备份策略
- 测试恢复流程

### 4. 性能监控
- 监控文件大小
- 跟踪访问模式
- 优化热点操作

## 故障排除

### 常见问题

1. **文件权限错误**
   - 检查目录权限
   - 确保有写入权限

2. **磁盘空间不足**
   - 清理旧版本文件
   - 压缩大文件
   - 扩展存储空间

3. **数据损坏**
   - 使用备份恢复
   - 验证数据完整性
   - 重新生成损坏文件

### 调试技巧

1. **启用详细日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **检查文件结构**
   ```python
   # 列出所有任务
   tasks = agent_context.list_all_tasks()
   print(tasks)
   ```

3. **验证上下文数据**
   ```python
   # 验证上下文结构
   is_valid, errors = ContextTools.validate_context_structure(context_data)
   if not is_valid:
       print(f"验证错误: {errors}")
   ```

## 未来规划

### 1. 功能增强
- 支持更多文件格式
- 增强搜索功能
- 添加可视化界面

### 2. 性能优化
- 实现智能缓存
- 优化文件操作
- 支持并行处理

### 3. 集成扩展
- 支持更多存储后端
- 提供REST API
- 支持WebSocket实时更新

## 贡献指南

欢迎贡献代码和想法！请遵循以下步骤：

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交Issue
- 发送邮件
- 参与讨论

---

通过这个基于文件系统的Agent上下文管理系统，Agent可以像人类一样"整理文件夹"，实现**无限扩展、结构化、可恢复、可协作**的上下文管理，极大提升智能体的长期记忆和任务执行能力。 