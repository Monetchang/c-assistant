from typing import List
from app.core.tools.search.base import SearchItem
import requests
import json
from langchain_core.tools import tool
from app.core.config import settings


class GoogleSearchEngine:
    """Google搜索引擎"""
    
    @staticmethod
    @tool()
    def perform_search(
        query: str, num_results: int = 10, *args, **kwargs
    ) -> List[SearchItem]:
        """
        执行Google搜索
        
        Args:
            query: 搜索查询
            num_results: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        try:
            url = "https://google.serper.dev/search"

            payload = json.dumps({
                "q": query,
                "num": num_results
            })
            headers = {
                'X-API-KEY': settings.GOOGLE_API_KEY,
                'Content-Type': 'application/json'
            }

            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()  # 检查HTTP错误
            
            data = response.json()
            
            results = []
            if 'organic' in data:
                for item in data['organic'][:num_results]:
                    results.append(SearchItem(
                        title=item.get('title', 'No title'),
                        link=item.get('link', ''),
                        summary=item.get('snippet', '')
                    ))
            else:
                # 如果没有organic结果，返回错误信息
                results.append(SearchItem(
                    title="No results found",
                    link="",
                    summary="No organic results found for the query"
                ))
                
            return results
            
        except requests.RequestException as e:
            # 处理网络请求错误
            return [SearchItem(
                title="Search Error",
                link="",
                summary=f"Network error: {str(e)}"
            )]
        except Exception as e:
            # 处理其他错误
            return [SearchItem(
                title="Search Error",
                link="",
                summary=f"Error: {str(e)}"
            )]