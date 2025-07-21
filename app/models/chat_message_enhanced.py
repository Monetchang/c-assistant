"""
增强的聊天消息模型
集成文件系统上下文管理功能
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field, field_serializer


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info=None):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)


class ChatMessageEnhanced(BaseModel):
    """增强的聊天消息模型"""

    id: Optional[PyObjectId] = Field(alias="_id")
    thread_id: str
    role: str  # user, assistant, system
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # 上下文管理相关字段
    context_task_id: Optional[str] = None  # 关联的任务ID
    context_agent_id: Optional[str] = None  # 关联的Agent ID
    context_file_type: Optional[str] = (
        None  # 关联的文件类型 (todo, history, resource, summary, scratchpad)
    )
    context_file_version: Optional[int] = None  # 文件版本

    # 元数据字段
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 消息类型和状态
    message_type: str = "text"  # text, file, image, audio, etc.
    status: str = "sent"  # sent, delivered, read, failed

    # 关联信息
    parent_message_id: Optional[str] = None  # 父消息ID（用于回复链）
    reply_chain: List[str] = Field(default_factory=list)  # 回复链

    # 上下文摘要
    context_summary: Optional[str] = None  # 消息发送时的上下文摘要

    @field_serializer("id")
    def serialize_id(self, id, _info):
        return str(id) if id is not None else None

    class Config:
        arbitrary_types_allowed = True


class ThreadEnhanced(BaseModel):
    """增强的线程模型"""

    id: Optional[PyObjectId] = Field(alias="_id")
    title: str
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    is_active: bool = True

    # 上下文管理相关字段
    context_agent_id: Optional[str] = None  # 关联的Agent ID
    current_task_id: Optional[str] = None  # 当前任务ID
    task_history: List[str] = Field(default_factory=list)  # 任务历史

    # 线程元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 线程状态
    status: str = "active"  # active, paused, completed, archived

    # 上下文摘要
    context_summary: Optional[str] = None  # 线程的上下文摘要

    @field_serializer("id")
    def serialize_id(self, id, _info):
        return str(id) if id is not None else None

    class Config:
        arbitrary_types_allowed = True


class ContextSnapshot(BaseModel):
    """上下文快照模型"""

    id: Optional[PyObjectId] = Field(alias="_id")
    thread_id: str
    task_id: str
    agent_id: str
    snapshot_type: str  # task_start, task_progress, task_complete, manual
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # 快照内容
    context_data: Dict[str, Any] = Field(default_factory=dict)

    # 快照元数据
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # 版本信息
    version: int = 1
    parent_snapshot_id: Optional[str] = None

    @field_serializer("id")
    def serialize_id(self, id, _info):
        return str(id) if id is not None else None

    class Config:
        arbitrary_types_allowed = True


class TaskProgress(BaseModel):
    """任务进度模型"""

    id: Optional[PyObjectId] = Field(alias="_id")
    task_id: str
    thread_id: str
    agent_id: str

    # 进度信息
    status: str  # pending, in_progress, completed, failed, paused
    progress_percentage: float = 0.0  # 0-100
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    completed_steps: int = 0

    # 时间信息
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

    # 进度详情
    step_history: List[Dict[str, Any]] = Field(default_factory=list)
    current_actions: List[str] = Field(default_factory=list)

    # 错误信息
    error_message: Optional[str] = None
    retry_count: int = 0

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_serializer("id")
    def serialize_id(self, id, _info):
        return str(id) if id is not None else None

    class Config:
        arbitrary_types_allowed = True


class ContextFileReference(BaseModel):
    """上下文文件引用模型"""

    id: Optional[PyObjectId] = Field(alias="_id")
    thread_id: str
    task_id: str
    agent_id: str
    file_type: str  # todo, history, resource, summary, scratchpad
    file_name: str
    file_path: str  # 文件系统路径

    # 文件信息
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    mime_type: Optional[str] = None

    # 版本信息
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # 引用信息
    referenced_by: List[str] = Field(default_factory=list)  # 引用此文件的消息ID列表
    reference_count: int = 0

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_serializer("id")
    def serialize_id(self, id, _info):
        return str(id) if id is not None else None

    class Config:
        arbitrary_types_allowed = True
