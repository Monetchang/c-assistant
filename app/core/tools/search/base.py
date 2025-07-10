from typing import List, Optional
from pydantic import BaseModel, Field

class SearchItem(BaseModel):
    title: str
    link: str
    summary: Optional[str] = Field(
        default=None, description="A description or snippet of the search result"
    )

class WebSearchBase(BaseModel):
    def perform_search(
        self, query: str, num_results: int = 10, *args, **kwargs
    ) -> List[SearchItem]:
       raise NotImplementedError