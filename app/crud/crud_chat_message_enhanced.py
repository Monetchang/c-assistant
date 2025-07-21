"""
增强的聊天消息CRUD操作
集成文件系统上下文管理功能
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.core.context import AgentContext, ContextTools, FileContextManager
from app.models.chat_message_enhanced import (
    ChatMessageEnhanced,
    ContextFileReference,
    ContextSnapshot,
    TaskProgress,
    ThreadEnhanced,
)
from app.schemas.chat_message import ChatMessage


class CRUDChatMessageEnhanced:
    """增强的聊天消息CRUD操作类"""

    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        context_manager: Optional[FileContextManager] = None,
    ):
        self.collection = collection
        self.context_manager = context_manager or FileContextManager()

    async def get_by_chat(
        self, thread_id: str, skip: int = 0, limit: int = 100
    ) -> List[ChatMessage]:
        """获取聊天消息"""
        cursor = (
            self.collection.find({"thread_id": thread_id})
            .skip(skip)
            .limit(limit)
            .sort("created_at", 1)
        )
        return [ChatMessage(**{**doc, "id": str(doc["_id"])}) async for doc in cursor]

    async def create_with_chat(
        self, obj_in: dict, thread_id: str
    ) -> ChatMessageEnhanced:
        """创建聊天消息"""
        obj_in["thread_id"] = thread_id
        obj_in["created_at"] = datetime.utcnow()

        # 如果有关联的上下文信息，更新文件系统
        if obj_in.get("context_task_id") and obj_in.get("context_agent_id"):
            await self._update_context_files(obj_in)

        result = await self.collection.insert_one(obj_in)
        doc = await self.collection.find_one({"_id": result.inserted_id})
        return ChatMessageEnhanced.parse_obj(doc)

    async def create_with_context(
        self,
        thread_id: str,
        role: str,
        content: str,
        agent_id: str,
        task_id: str,
        file_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessageEnhanced:
        """创建带上下文的聊天消息"""
        # 创建消息对象
        message_data = {
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "context_agent_id": agent_id,
            "context_task_id": task_id,
            "context_file_type": file_type,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
        }

        # 更新文件系统上下文
        if file_type:
            await self._update_context_file(agent_id, task_id, file_type, content)

        # 添加到历史记录
        self.context_manager.add_chat_message(agent_id, task_id, role, content)

        # 保存到数据库
        result = await self.collection.insert_one(message_data)
        doc = await self.collection.find_one({"_id": result.inserted_id})
        return ChatMessageEnhanced.parse_obj(doc)

    async def get_context_messages(
        self,
        thread_id: str,
        agent_id: str,
        task_id: str,
        file_type: Optional[str] = None,
    ) -> List[ChatMessageEnhanced]:
        """获取上下文相关的消息"""
        query = {
            "thread_id": thread_id,
            "context_agent_id": agent_id,
            "context_task_id": task_id,
        }

        if file_type:
            query["context_file_type"] = file_type

        cursor = self.collection.find(query).sort("created_at", 1)
        return [ChatMessageEnhanced.parse_obj(doc) async for doc in cursor]

    async def get_context_summary(self, agent_id: str, task_id: str) -> Dict[str, Any]:
        """获取上下文摘要"""
        return self.context_manager.get_context_summary(agent_id, task_id)

    async def create_context_snapshot(
        self,
        thread_id: str,
        agent_id: str,
        task_id: str,
        snapshot_type: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> ContextSnapshot:
        """创建上下文快照"""
        # 获取当前上下文数据
        context_data = self.context_manager.get_context_summary(agent_id, task_id)

        # 创建快照对象
        snapshot_data = {
            "thread_id": thread_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "snapshot_type": snapshot_type,
            "context_data": context_data,
            "description": description,
            "tags": tags or [],
            "created_at": datetime.utcnow(),
        }

        # 保存到数据库
        result = await self.collection.insert_one(snapshot_data)
        doc = await self.collection.find_one({"_id": result.inserted_id})
        return ContextSnapshot.parse_obj(doc)

    async def get_context_snapshots(
        self,
        thread_id: str,
        agent_id: str,
        task_id: str,
        snapshot_type: Optional[str] = None,
    ) -> List[ContextSnapshot]:
        """获取上下文快照"""
        query = {"thread_id": thread_id, "agent_id": agent_id, "task_id": task_id}

        if snapshot_type:
            query["snapshot_type"] = snapshot_type

        cursor = self.collection.find(query).sort("created_at", -1)
        return [ContextSnapshot.parse_obj(doc) async for doc in cursor]

    async def update_task_progress(
        self,
        task_id: str,
        thread_id: str,
        agent_id: str,
        status: str,
        progress_percentage: float = 0.0,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> TaskProgress:
        """更新任务进度"""
        # 查找现有进度记录
        existing = await self.collection.find_one(
            {"task_id": task_id, "thread_id": thread_id, "agent_id": agent_id}
        )

        if existing:
            # 更新现有记录
            update_data = {
                "status": status,
                "progress_percentage": progress_percentage,
                "current_step": current_step,
                "error_message": error_message,
                "updated_at": datetime.utcnow(),
            }

            if status == "in_progress" and not existing.get("started_at"):
                update_data["started_at"] = datetime.utcnow()
            elif status in ["completed", "failed"]:
                update_data["completed_at"] = datetime.utcnow()

            await self.collection.update_one(
                {"_id": existing["_id"]}, {"$set": update_data}
            )

            # 更新文件系统上下文
            if current_step:
                self.context_manager.update_todo_progress(
                    agent_id, task_id, [f"当前步骤: {current_step}"]
                )

            doc = await self.collection.find_one({"_id": existing["_id"]})
            return TaskProgress.parse_obj(doc)
        else:
            # 创建新记录
            progress_data = {
                "task_id": task_id,
                "thread_id": thread_id,
                "agent_id": agent_id,
                "status": status,
                "progress_percentage": progress_percentage,
                "current_step": current_step,
                "error_message": error_message,
                "created_at": datetime.utcnow(),
            }

            if status == "in_progress":
                progress_data["started_at"] = datetime.utcnow()

            result = await self.collection.insert_one(progress_data)
            doc = await self.collection.find_one({"_id": result.inserted_id})
            return TaskProgress.parse_obj(doc)

    async def get_task_progress(
        self, task_id: str, thread_id: str, agent_id: str
    ) -> Optional[TaskProgress]:
        """获取任务进度"""
        doc = await self.collection.find_one(
            {"task_id": task_id, "thread_id": thread_id, "agent_id": agent_id}
        )

        if doc:
            return TaskProgress.parse_obj(doc)
        return None

    async def add_context_file_reference(
        self,
        thread_id: str,
        task_id: str,
        agent_id: str,
        file_type: str,
        file_name: str,
        file_path: str,
        message_id: Optional[str] = None,
    ) -> ContextFileReference:
        """添加上下文文件引用"""
        # 查找现有引用
        existing = await self.collection.find_one(
            {
                "thread_id": thread_id,
                "task_id": task_id,
                "agent_id": agent_id,
                "file_type": file_type,
                "file_name": file_name,
            }
        )

        if existing:
            # 更新现有引用
            update_data = {
                "updated_at": datetime.utcnow(),
                "reference_count": existing.get("reference_count", 0) + 1,
            }

            if message_id and message_id not in existing.get("referenced_by", []):
                update_data["referenced_by"] = existing.get("referenced_by", []) + [
                    message_id
                ]

            await self.collection.update_one(
                {"_id": existing["_id"]}, {"$set": update_data}
            )

            doc = await self.collection.find_one({"_id": existing["_id"]})
            return ContextFileReference.parse_obj(doc)
        else:
            # 创建新引用
            reference_data = {
                "thread_id": thread_id,
                "task_id": task_id,
                "agent_id": agent_id,
                "file_type": file_type,
                "file_name": file_name,
                "file_path": file_path,
                "referenced_by": [message_id] if message_id else [],
                "reference_count": 1,
                "created_at": datetime.utcnow(),
            }

            result = await self.collection.insert_one(reference_data)
            doc = await self.collection.find_one({"_id": result.inserted_id})
            return ContextFileReference.parse_obj(doc)

    async def get_context_file_references(
        self,
        thread_id: str,
        task_id: str,
        agent_id: str,
        file_type: Optional[str] = None,
    ) -> List[ContextFileReference]:
        """获取上下文文件引用"""
        query = {"thread_id": thread_id, "task_id": task_id, "agent_id": agent_id}

        if file_type:
            query["file_type"] = file_type

        cursor = self.collection.find(query).sort("created_at", -1)
        return [ContextFileReference.parse_obj(doc) async for doc in cursor]

    async def _update_context_files(self, message_data: Dict[str, Any]):
        """更新上下文文件"""
        agent_id = message_data.get("context_agent_id")
        task_id = message_data.get("context_task_id")
        file_type = message_data.get("context_file_type")
        content = message_data.get("content", "")
        role = message_data.get("role", "")

        if agent_id and task_id:
            # 添加到历史记录
            self.context_manager.add_chat_message(agent_id, task_id, role, content)

            # 如果指定了文件类型，更新对应文件
            if file_type:
                await self._update_context_file(agent_id, task_id, file_type, content)

    async def _update_context_file(
        self, agent_id: str, task_id: str, file_type: str, content: str
    ):
        """更新特定类型的上下文文件"""
        if file_type == "todo":
            self.context_manager.update_todo_progress(agent_id, task_id, [content])
        elif file_type == "summary":
            self.context_manager.add_summary_entry(
                agent_id, task_id, "自动摘要", content
            )
        elif file_type == "scratchpad":
            self.context_manager.add_scratchpad_entry(agent_id, task_id, content)
        elif file_type == "resource":
            # 假设content包含URL和描述
            lines = content.split("\n")
            title = lines[0] if lines else "资源"
            url = lines[1] if len(lines) > 1 else ""
            description = "\n".join(lines[2:]) if len(lines) > 2 else ""
            self.context_manager.add_resource_link(
                agent_id, task_id, title, url, description
            )

    async def export_context_data(self, agent_id: str, task_id: str) -> Dict[str, Any]:
        """导出上下文数据"""
        # 获取文件系统上下文
        context_data = self.context_manager.get_context_summary(agent_id, task_id)

        # 获取数据库中的相关数据
        messages = await self.get_context_messages("", agent_id, task_id)
        snapshots = await self.get_context_snapshots("", agent_id, task_id)
        progress = await self.get_task_progress(task_id, "", agent_id)
        references = await self.get_context_file_references("", task_id, agent_id)

        return {
            "context_data": context_data,
            "messages": [msg.dict() for msg in messages],
            "snapshots": [snap.dict() for snap in snapshots],
            "progress": progress.dict() if progress else None,
            "references": [ref.dict() for ref in references],
            "exported_at": datetime.utcnow().isoformat(),
        }

    async def import_context_data(
        self, agent_id: str, task_id: str, data: Dict[str, Any]
    ) -> bool:
        """导入上下文数据"""
        try:
            # 导入文件系统上下文
            if "context_data" in data:
                context_data = data["context_data"]
                if context_data.get("task_id") == task_id:
                    # 创建新任务或更新现有任务
                    title = context_data.get("title", "Imported Task")
                    description = context_data.get("description", "")

                    # 这里需要实现导入逻辑
                    pass

            # 导入数据库数据
            if "messages" in data:
                for msg_data in data["messages"]:
                    msg_data["context_agent_id"] = agent_id
                    msg_data["context_task_id"] = task_id
                    await self.collection.insert_one(msg_data)

            if "snapshots" in data:
                for snap_data in data["snapshots"]:
                    snap_data["agent_id"] = agent_id
                    snap_data["task_id"] = task_id
                    await self.collection.insert_one(snap_data)

            if "progress" in data and data["progress"]:
                progress_data = data["progress"]
                progress_data["agent_id"] = agent_id
                progress_data["task_id"] = task_id
                await self.collection.insert_one(progress_data)

            if "references" in data:
                for ref_data in data["references"]:
                    ref_data["agent_id"] = agent_id
                    ref_data["task_id"] = task_id
                    await self.collection.insert_one(ref_data)

            return True
        except Exception as e:
            print(f"导入上下文数据失败: {e}")
            return False
