from typing import List
from search.base import WebSearchBase, SearchItem
import requests
import json
from app.core.config import settings

class GoogleSearch(WebSearchBase):
    """
        Google search.

        Returns results formatted according to SearchItem model.
    """
    def perform_search(
        self, query: str, num_results: int = 10, *args, **kwargs
    ) -> List[SearchItem]:
        url = "https://google.serper.dev/search"

        payload = json.dumps({
            "q": "apple inc"
        })
        headers = {
            'X-API-KEY': settings.GOOGLE_API_KEY,
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        data = json.loads(response.text)  # 将返回的JSON字符串转换为字典
        
        if 'organic' in data:
            return json.dumps(data['organic'],  ensure_ascii=False)  # 返回'organic'部分的JSON字符串
        else:
            return json.dumps({"error": "No organic results found"},  ensure_ascii=False)  # 如果没有'organic'键，返回错误信息