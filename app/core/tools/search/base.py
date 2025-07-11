from typing import List, Optional
from pydantic import BaseModel, Field


class SearchItem(BaseModel):
    """搜索结果项模型"""
    title: str
    link: str
    summary: Optional[str] = Field(
        default=None, description="A description or snippet of the search result"
    )