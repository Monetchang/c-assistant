"""
Agent上下文类
集成文件系统上下文管理器，提供高级上下文管理功能
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .file_context_manager import ContextFile, FileContextManager, TaskContext


class AgentContext:
    """Agent上下文管理类"""

    def __init__(
        self, agent_id: str, context_manager: Optional[FileContextManager] = None
    ):
        self.agent_id = agent_id
        self.context_manager = context_manager or FileContextManager()
        self.current_task_id: Optional[str] = None
        self.current_task_context: Optional[TaskContext] = None

    def create_new_task(
        self, title: str, description: str, task_id: Optional[str] = None, todo_items: Optional[List[str]] = None
    ) -> str:
        """创建新任务"""
        if task_id is None:
            task_id = str(uuid.uuid4())

        self.current_task_context = self.context_manager.create_task_context(
            self.agent_id, task_id, title, description, todo_items=todo_items
        )
        self.current_task_id = task_id

        return task_id

    def load_task(self, task_id: str) -> bool:
        """加载指定任务"""
        task_context = self.context_manager.load_task_context(self.agent_id, task_id)
        if task_context:
            self.current_task_context = task_context
            self.current_task_id = task_id
            return True
        return False

    def get_current_task_id(self) -> Optional[str]:
        """获取当前任务ID"""
        return self.current_task_id

    def get_current_task_context(self) -> Optional[TaskContext]:
        """获取当前任务上下文"""
        return self.current_task_context

    def add_chat_message(self, role: str, content: str) -> bool:
        """添加聊天消息"""
        if not self.current_task_id:
            return False

        return self.context_manager.add_chat_message(
            self.agent_id, self.current_task_id, role, content
        )

    def update_todo_progress(self, progress_updates: List[str]) -> bool:
        """更新待办事项进度"""
        if not self.current_task_id:
            return False

        return self.context_manager.update_todo_progress(
            self.agent_id, self.current_task_id, progress_updates
        )

    def add_resource_link(self, title: str, url: str, description: str = "") -> bool:
        """添加资源链接"""
        if not self.current_task_id:
            return False

        return self.context_manager.add_resource_link(
            self.agent_id, self.current_task_id, title, url, description
        )

    def add_summary_entry(self, section: str, content: str) -> bool:
        """添加总结条目"""
        if not self.current_task_id:
            return False

        return self.context_manager.add_summary_entry(
            self.agent_id, self.current_task_id, section, content
        )

    def add_scratchpad_entry(self, content: str) -> bool:
        """添加临时笔记"""
        if not self.current_task_id:
            return False

        return self.context_manager.add_scratchpad_entry(
            self.agent_id, self.current_task_id, content
        )

    def get_context_summary(self) -> Dict[str, Any]:
        """获取当前任务上下文摘要"""
        if not self.current_task_id:
            return {}

        return self.context_manager.get_context_summary(
            self.agent_id, self.current_task_id
        )

    def list_all_tasks(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        return self.context_manager.list_agent_tasks(self.agent_id)

    def get_task_file_content(self, file_type: str) -> Optional[str]:
        """获取指定类型文件的内容"""
        if not self.current_task_context:
            return None

        file_obj = self.current_task_context.files.get(file_type)
        if file_obj:
            return file_obj.content
        return None

    def update_task_status(self, status: str) -> bool:
        """更新任务状态"""
        if not self.current_task_context or not self.current_task_id:
            return False

        self.current_task_context.status = status
        self.current_task_context.updated_at = datetime.utcnow()

        # 更新元数据
        task_path = self.context_manager._get_task_path(
            self.agent_id, self.current_task_id
        )
        self.context_manager._save_task_metadata(self.current_task_context, task_path)

        return True

    def get_recent_chat_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取最近的聊天历史"""
        if not self.current_task_context:
            return []

        history_file = self.current_task_context.files.get("history")
        if not history_file:
            return []

        # 简单的历史解析（可以根据需要改进）
        lines = history_file.content.split("\n")
        chat_history = []
        current_role = None
        current_content = []

        for line in lines:
            if line.startswith("### ") and ":" in line:
                # 保存之前的消息
                if current_role and current_content:
                    chat_history.append(
                        {
                            "role": current_role,
                            "content": "\n".join(current_content).strip(),
                        }
                    )

                # 解析新消息
                parts = line.split(":", 2)
                if len(parts) >= 2:
                    current_role = parts[1].strip()
                    current_content = []
            elif line.strip() and current_role:
                current_content.append(line)

        # 添加最后一条消息
        if current_role and current_content:
            chat_history.append(
                {"role": current_role, "content": "\n".join(current_content).strip()}
            )

        return chat_history[-limit:]

    def get_task_todo_items(self) -> List[str]:
        """获取待办事项列表"""
        if not self.current_task_context:
            return []

        todo_file = self.current_task_context.files.get("todo")
        if not todo_file:
            return []

        # 简单的待办事项解析
        lines = todo_file.content.split("\n")
        todo_items = []

        for line in lines:
            if line.strip().startswith("- [ ]"):
                todo_items.append(line.strip()[4:].strip())

        return todo_items

    def mark_todo_completed(self, item_text: str) -> bool:
        """标记待办事项为完成"""
        if not self.current_task_context or not self.current_task_id:
            return False

        todo_file = self.current_task_context.files.get("todo")
        if not todo_file:
            return False

        # 更新待办事项状态
        lines = todo_file.content.split("\n")
        updated_lines = []

        for line in lines:
            if line.strip().startswith("- [ ]") and item_text in line:
                # 标记为完成
                updated_lines.append(line.replace("- [ ]", "- [x]"))
            else:
                updated_lines.append(line)

        new_content = "\n".join(updated_lines)
        return self.context_manager.update_file_content(
            self.agent_id, self.current_task_id, "todo", new_content
        )

    def get_task_resources(self) -> List[Dict[str, str]]:
        """获取任务资源列表"""
        if not self.current_task_context:
            return []

        resource_file = self.current_task_context.files.get("resource")
        if not resource_file:
            return []

        # 简单的资源解析
        lines = resource_file.content.split("\n")
        resources = []
        current_resource = {}

        for line in lines:
            line = line.strip()
            if line.startswith("## ") and not line.startswith("## 任务信息"):
                # 保存之前的资源
                if current_resource:
                    resources.append(current_resource)

                # 开始新资源
                current_resource = {"title": line[3:].strip()}
            elif line.startswith("- URL:") and current_resource:
                current_resource["url"] = line[6:].strip()
            elif line.startswith("- 描述:") and current_resource:
                current_resource["description"] = line[5:].strip()

        # 添加最后一个资源
        if current_resource:
            resources.append(current_resource)

        return resources

    def summarize_current_file_with_llm(
        self, file_type: str, llm, max_length: int = 200
    ) -> bool:
        """对当前任务的指定文件用LLM生成摘要"""
        if not self.current_task_id:
            return False
        return self.context_manager.summarize_file_with_llm(
            self.agent_id, self.current_task_id, file_type, llm, max_length=max_length
        )

    def summarize_current_task_context_with_llm(
        self, llm, max_size: int = 10000
    ) -> bool:
        """对当前任务的所有文件用LLM自动压缩摘要"""
        if not self.current_task_id:
            return False
        return self.context_manager.summarize_task_context_with_llm(
            self.agent_id, self.current_task_id, llm, max_size=max_size
        )

    def cleanup_old_versions(self, keep_versions: int = 5) -> bool:
        """清理旧版本文件"""
        if not self.current_task_id:
            return False

        self.context_manager.cleanup_old_versions(
            self.agent_id, self.current_task_id, keep_versions
        )
        return True

    def export_task_context(self) -> Dict[str, Any]:
        """导出任务上下文"""
        if not self.current_task_context:
            return {}

        return {
            "task_id": self.current_task_context.task_id,
            "title": self.current_task_context.title,
            "description": self.current_task_context.description,
            "status": self.current_task_context.status,
            "created_at": self.current_task_context.created_at.isoformat(),
            "updated_at": self.current_task_context.updated_at.isoformat(),
            "files": {
                name: {
                    "name": file.name,
                    "content": file.content,
                    "file_type": file.file_type,
                    "version": file.version,
                    "metadata": file.metadata,
                }
                for name, file in self.current_task_context.files.items()
            },
            "metadata": self.current_task_context.metadata,
        }

    def import_task_context(self, context_data: Dict[str, Any]) -> bool:
        """导入任务上下文"""
        try:
            # 创建新任务
            task_id = context_data.get("task_id", str(uuid.uuid4()))
            title = context_data.get("title", "Imported Task")
            description = context_data.get("description", "")

            self.create_new_task(title, description, task_id)

            # 导入文件内容
            files_data = context_data.get("files", {})
            for file_type, file_data in files_data.items():
                content = file_data.get("content", "")
                if content:
                    self.context_manager.update_file_content(
                        self.agent_id, task_id, file_type, content
                    )

            return True
        except Exception as e:
            print(f"导入任务上下文失败: {e}")
            return False
