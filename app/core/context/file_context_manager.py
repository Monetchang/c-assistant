"""
文件系统上下文管理器
实现基于文件系统的Agent上下文管理
"""

import hashlib
import json
import os
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class ContextFile:
    """上下文文件结构"""

    name: str
    content: str
    file_type: str  # todo, history, resource, summary, scratchpad
    created_at: datetime
    updated_at: datetime
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        pass


@dataclass
class TaskContext:
    """任务上下文结构"""

    task_id: str
    title: str
    description: str
    status: str  # pending, in_progress, completed, failed
    created_at: datetime
    updated_at: datetime
    files: Dict[str, ContextFile] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        pass


class FileContextManager:
    """文件系统上下文管理器"""

    def __init__(self, base_path: str = "./agent_contexts"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    def _get_agent_path(self, agent_id: str) -> Path:
        """获取Agent工作空间路径"""
        agent_path = self.base_path / f"agent_{agent_id}"
        agent_path.mkdir(exist_ok=True)
        return agent_path

    def _get_task_path(self, agent_id: str, task_id: str) -> Path:
        """获取任务路径"""
        task_path = self._get_agent_path(agent_id) / f"task_{task_id}"
        task_path.mkdir(exist_ok=True)
        return task_path

    def _get_shared_path(self) -> Path:
        """获取共享文件夹路径"""
        shared_path = self.base_path / "shared"
        shared_path.mkdir(exist_ok=True)
        return shared_path

    def create_task_context(
        self, agent_id: str, task_id: str, title: str, description: str, todo_items: Optional[List[str]] = None
    ) -> TaskContext:
        """创建新的任务上下文"""
        task_path = self._get_task_path(agent_id, task_id)

        # 创建任务上下文
        task_context = TaskContext(
            task_id=task_id,
            title=title,
            description=description,
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 初始化基础文件
        self._create_todo_file(task_context, task_path, todo_items=todo_items)
        self._create_history_file(task_context, task_path)
        self._create_resource_file(task_context, task_path)
        self._create_summary_file(task_context, task_path)
        self._create_scratchpad_file(task_context, task_path)

        # 保存任务元数据
        self._save_task_metadata(task_context, task_path)

        return task_context

    def _create_todo_file(self, task_context: TaskContext, task_path: Path, todo_items: Optional[List[str]] = None):
        """创建待办事项文件"""
        todo_content = f"""# 任务待办事项

## 任务信息
- 任务ID: {task_context.task_id}
- 标题: {task_context.title}
- 描述: {task_context.description}
- 状态: {task_context.status}
- 创建时间: {task_context.created_at}

## 目标
{task_context.description}

## 待办事项
"""
        if todo_items and isinstance(todo_items, list) and len(todo_items) > 0:
            for item in todo_items:
                todo_content += f"- [ ] {item}\n"
        else:
            todo_content += "- [ ] 分析任务需求\n- [ ] 制定执行计划\n- [ ] 收集必要信息\n- [ ] 执行任务\n- [ ] 总结结果\n"
        todo_content += f"""

## 进度记录
- {task_context.created_at}: 任务创建
"""

        todo_file = ContextFile(
            name="todo.md",
            content=todo_content,
            file_type="todo",
            created_at=task_context.created_at,
            updated_at=task_context.updated_at,
        )

        task_context.files["todo"] = todo_file
        self._save_file(todo_file, task_path / "todo.md")

    def _create_history_file(self, task_context: TaskContext, task_path: Path):
        """创建历史记录文件"""
        history_content = f"""# 任务历史记录

## 任务信息
- 任务ID: {task_context.task_id}
- 标题: {task_context.title}

## 对话历史
### {task_context.created_at}: 任务创建
任务已创建，开始执行。

## 决策记录
### {task_context.created_at}: 初始化
- 创建任务上下文
- 初始化基础文件结构
"""

        history_file = ContextFile(
            name="history.md",
            content=history_content,
            file_type="history",
            created_at=task_context.created_at,
            updated_at=task_context.updated_at,
        )

        task_context.files["history"] = history_file
        self._save_file(history_file, task_path / "history.md")

    def _create_resource_file(self, task_context: TaskContext, task_path: Path):
        """创建资源链接文件"""
        resource_content = f"""# 外部资源链接

## 任务信息
- 任务ID: {task_context.task_id}
- 标题: {task_context.title}

## 资源链接
<!-- 在此添加相关的外部资源链接 -->

## 文档引用
<!-- 在此添加文档引用和摘要 -->

## 工具配置
<!-- 在此添加使用的工具配置信息 -->
"""

        resource_file = ContextFile(
            name="resource_links.txt",
            content=resource_content,
            file_type="resource",
            created_at=task_context.created_at,
            updated_at=task_context.updated_at,
        )

        task_context.files["resource"] = resource_file
        self._save_file(resource_file, task_path / "resource_links.txt")

    def _create_summary_file(self, task_context: TaskContext, task_path: Path):
        """创建总结文件"""
        summary_content = f"""# 任务总结

## 任务信息
- 任务ID: {task_context.task_id}
- 标题: {task_context.title}
- 描述: {task_context.description}

## 执行摘要
<!-- 在此记录任务执行的关键信息和结果 -->

## 关键要点
<!-- 在此记录重要的发现和结论 -->

## 后续行动
<!-- 在此记录需要后续处理的事项 -->
"""

        summary_file = ContextFile(
            name="summary.md",
            content=summary_content,
            file_type="summary",
            created_at=task_context.created_at,
            updated_at=task_context.updated_at,
        )

        task_context.files["summary"] = summary_file
        self._save_file(summary_file, task_path / "summary.md")

    def _create_scratchpad_file(self, task_context: TaskContext, task_path: Path):
        """创建临时笔记文件"""
        scratchpad_content = f"""# 临时笔记

## 任务信息
- 任务ID: {task_context.task_id}
- 标题: {task_context.title}

## 推理过程
<!-- 在此记录推理过程和临时想法 -->

## 临时计算
<!-- 在此记录临时计算和实验 -->

## 待验证想法
<!-- 在此记录需要验证的想法和假设 -->
"""

        scratchpad_file = ContextFile(
            name="scratchpad.md",
            content=scratchpad_content,
            file_type="scratchpad",
            created_at=task_context.created_at,
            updated_at=task_context.updated_at,
        )

        task_context.files["scratchpad"] = scratchpad_file
        self._save_file(scratchpad_file, task_path / "scratchpad.md")

    def _save_file(self, context_file: ContextFile, file_path: Path):
        """保存文件到磁盘"""
        file_path.write_text(context_file.content, encoding="utf-8")

    def _save_task_metadata(self, task_context: TaskContext, task_path: Path):
        """保存任务元数据"""
        metadata_path = task_path / "metadata.json"
        metadata = {
            "task_id": task_context.task_id,
            "title": task_context.title,
            "description": task_context.description,
            "status": task_context.status,
            "created_at": task_context.created_at.isoformat(),
            "updated_at": task_context.updated_at.isoformat(),
            "files": {
                name: {
                    "name": file.name,
                    "file_type": file.file_type,
                    "created_at": file.created_at.isoformat(),
                    "updated_at": file.updated_at.isoformat(),
                    "version": file.version,
                    "metadata": file.metadata,
                }
                for name, file in task_context.files.items()
            },
            "metadata": task_context.metadata,
        }

        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load_task_context(self, agent_id: str, task_id: str) -> Optional[TaskContext]:
        """加载任务上下文"""
        task_path = self._get_task_path(agent_id, task_id)
        metadata_path = task_path / "metadata.json"

        if not metadata_path.exists():
            return None

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

            # 重建任务上下文
            task_context = TaskContext(
                task_id=metadata["task_id"],
                title=metadata["title"],
                description=metadata["description"],
                status=metadata["status"],
                created_at=datetime.fromisoformat(metadata["created_at"]),
                updated_at=datetime.fromisoformat(metadata["updated_at"]),
                metadata=metadata.get("metadata", {}),
            )

            # 加载文件
            for name, file_info in metadata["files"].items():
                file_path = task_path / file_info["name"]
                if file_path.exists():
                    content = file_path.read_text(encoding="utf-8")
                    context_file = ContextFile(
                        name=file_info["name"],
                        content=content,
                        file_type=file_info["file_type"],
                        created_at=datetime.fromisoformat(file_info["created_at"]),
                        updated_at=datetime.fromisoformat(file_info["updated_at"]),
                        version=file_info["version"],
                        metadata=file_info.get("metadata", {}),
                    )
                    task_context.files[name] = context_file

            return task_context

        except Exception as e:
            print(f"加载任务上下文失败: {e}")
            return None

    def update_file_content(
        self,
        agent_id: str,
        task_id: str,
        file_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """更新文件内容，只保留最新版本，不保存历史版本"""
        if metadata is None:
            metadata = {}
        task_context = self.load_task_context(agent_id, task_id)
        if not task_context:
            return False

        if file_type not in task_context.files:
            return False

        # 只更新当前版本，不保存旧版本
        old_file = task_context.files[file_type]
        new_file = ContextFile(
            name=old_file.name,
            content=content,
            file_type=old_file.file_type,
            created_at=old_file.created_at,
            updated_at=datetime.utcnow(),
            version=old_file.version + 1,
            metadata=metadata if metadata is not None else old_file.metadata or {},
        )

        # 只保存当前版本
        task_context.files[file_type] = new_file
        task_context.updated_at = datetime.utcnow()

        # 保存文件
        task_path = self._get_task_path(agent_id, task_id)
        self._save_file(new_file, task_path / new_file.name)
        self._save_task_metadata(task_context, task_path)

        return True

    def add_chat_message(self, agent_id: str, task_id: str, role: str, content: str):
        """添加聊天消息到历史记录"""
        task_context = self.load_task_context(agent_id, task_id)
        if not task_context:
            return False

        history_file = task_context.files.get("history")
        if not history_file:
            return False

        # 添加新消息到历史记录
        new_content = (
            history_file.content
            + f"""

### {datetime.utcnow()}: {role}
{content}
"""
        )

        return self.update_file_content(agent_id, task_id, "history", new_content)

    def update_todo_progress(
        self, agent_id: str, task_id: str, progress_updates: List[str]
    ):
        """更新待办事项进度"""
        task_context = self.load_task_context(agent_id, task_id)
        if not task_context:
            return False

        todo_file = task_context.files.get("todo")
        if not todo_file:
            return False

        # 读取当前 todo 内容
        lines = todo_file.content.split('\n')
        new_lines = []
        
        # 处理每一行
        for line in lines:
            # 检查是否是待办事项行
            if line.strip().startswith('- [ ]'):
                # 检查是否匹配任何进度更新
                item_text = line.strip()[4:].strip()  # 移除 "- [ ] "
                should_mark_complete = False
                
                for update in progress_updates:
                    # 简单的匹配逻辑：如果更新文本包含在待办事项中，或者待办事项包含在更新中
                    if (update.lower() in item_text.lower() or 
                        item_text.lower() in update.lower() or
                        any(word in item_text.lower() for word in update.lower().split() if len(word) > 3)):
                        should_mark_complete = True
                        break
                
                if should_mark_complete:
                    # 标记为完成
                    new_lines.append(line.replace('- [ ]', '- [x]'))
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # 添加进度记录
        new_content = '\n'.join(new_lines)
        new_content += f"""

## 进度记录
"""
        for update in progress_updates:
            new_content += f"- {datetime.utcnow()}: {update}\n"

        return self.update_file_content(agent_id, task_id, "todo", new_content)

    def add_resource_link(
        self, agent_id: str, task_id: str, title: str, url: str, description: str = ""
    ):
        """添加资源链接"""
        task_context = self.load_task_context(agent_id, task_id)
        if not task_context:
            return False

        resource_file = task_context.files.get("resource")
        if not resource_file:
            return False

        # 添加新资源链接
        new_content = (
            resource_file.content
            + f"""

## {title}
- URL: {url}
- 描述: {description}
- 添加时间: {datetime.utcnow()}
"""
        )

        return self.update_file_content(agent_id, task_id, "resource", new_content)

    def add_summary_entry(
        self, agent_id: str, task_id: str, section: str, content: str
    ):
        """添加总结条目"""
        task_context = self.load_task_context(agent_id, task_id)
        if not task_context:
            return False

        summary_file = task_context.files.get("summary")
        if not summary_file:
            return False

        # 添加总结条目
        new_content = (
            summary_file.content
            + f"""

## {section}
{content}

---
更新时间: {datetime.utcnow()}
"""
        )

        return self.update_file_content(agent_id, task_id, "summary", new_content)

    def add_scratchpad_entry(self, agent_id: str, task_id: str, content: str):
        """添加临时笔记"""
        task_context = self.load_task_context(agent_id, task_id)
        if not task_context:
            return False

        scratchpad_file = task_context.files.get("scratchpad")
        if not scratchpad_file:
            return False

        # 添加临时笔记
        new_content = (
            scratchpad_file.content
            + f"""

### {datetime.utcnow()}: 临时笔记
{content}
"""
        )

        return self.update_file_content(agent_id, task_id, "scratchpad", new_content)

    def get_context_summary(self, agent_id: str, task_id: str) -> Dict[str, Any]:
        """获取上下文摘要"""
        task_context = self.load_task_context(agent_id, task_id)
        if not task_context:
            return {}

        summary = {
            "task_id": task_context.task_id,
            "title": task_context.title,
            "status": task_context.status,
            "created_at": task_context.created_at.isoformat(),
            "updated_at": task_context.updated_at.isoformat(),
            "files": {},
        }

        for name, file in task_context.files.items():
            # 只返回文件的基本信息和内容摘要
            summary["files"][name] = {
                "name": file.name,
                "file_type": file.file_type,
                "content_length": len(file.content),
                "content_preview": (
                    file.content[:200] + "..."
                    if len(file.content) > 200
                    else file.content
                ),
                "updated_at": file.updated_at.isoformat(),
                "version": file.version,
            }

        return summary

    def list_agent_tasks(self, agent_id: str) -> List[Dict[str, Any]]:
        """列出Agent的所有任务"""
        agent_path = self._get_agent_path(agent_id)
        tasks = []

        for task_dir in agent_path.iterdir():
            if task_dir.is_dir() and task_dir.name.startswith("task_"):
                task_id = task_dir.name[5:]  # 移除 "task_" 前缀
                metadata_path = task_dir / "metadata.json"

                if metadata_path.exists():
                    try:
                        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                        tasks.append(
                            {
                                "task_id": task_id,
                                "title": metadata["title"],
                                "status": metadata["status"],
                                "created_at": metadata["created_at"],
                                "updated_at": metadata["updated_at"],
                            }
                        )
                    except Exception as e:
                        print(f"读取任务元数据失败 {task_id}: {e}")

        return sorted(tasks, key=lambda x: x["updated_at"], reverse=True)

    def cleanup_old_versions(self, agent_id: str, task_id: str, keep_versions: int = 5):
        """清理旧版本文件"""
        task_path = self._get_task_path(agent_id, task_id)

        for file_path in task_path.iterdir():
            if file_path.name.endswith(".md") and "_v" in file_path.name:
                # 解析版本号
                try:
                    base_name, version_part = file_path.name.rsplit("_v", 1)
                    version_num = int(version_part.replace(".md", ""))

                    # 保留最新的几个版本
                    if version_num > keep_versions:
                        file_path.unlink()
                except (ValueError, IndexError):
                    continue

    def summarize_file_with_llm(
        self, agent_id: str, task_id: str, file_type: str, llm, max_length: int = 200
    ) -> bool:
        """对指定文件用LLM生成摘要并覆盖内容（或生成新版本）"""
        task_context = self.load_task_context(agent_id, task_id)
        if not task_context or file_type not in task_context.files:
            return False
        file_obj = task_context.files[file_type]
        summary = None
        try:
            from app.core.context.context_tools import ContextTools

            summary = ContextTools.generate_llm_summary(
                file_obj.content, llm, max_length=max_length
            )
        except Exception as e:
            print(f"LLM摘要失败: {e}")
            return False
        if summary:
            return self.update_file_content(agent_id, task_id, file_type, summary)
        return False

    def summarize_task_context_with_llm(
        self, agent_id: str, task_id: str, llm, max_size: int = 10000
    ) -> bool:
        """对整个任务上下文所有文件用LLM摘要，自动压缩"""
        from app.core.context.context_tools import ContextTools

        context_data = self.get_context_summary(agent_id, task_id)
        compressed = ContextTools.compress_context_with_llm(
            context_data, llm, max_size=max_size
        )
        # 更新所有被压缩的文件内容
        files = compressed.get("files", {})
        for file_type, file_data in files.items():
            if file_data.get("compressed"):
                self.update_file_content(
                    agent_id, task_id, file_type, file_data["content"]
                )
        return True
