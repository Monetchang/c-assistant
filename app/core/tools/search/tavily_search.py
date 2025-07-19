from typing import List
from app.core.tools.search.base import SearchItem
from langchain_core.tools import tool
from langchain_community.tools import TavilySearchResults
from app.core.config import settings


class TavilySearchEngine:
    """Tavily搜索引擎"""
    
    @staticmethod
    @tool()
    def perform_search(
        query: str, num_results: int = 10, *args, **kwargs
    ) -> List[SearchItem]:
        """
        执行Tavily搜索
        
        Args:
            query: 搜索查询
            num_results: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        try:
            # 使用Tavily搜索工具
            search_tool = TavilySearchResults(
                api_key=settings.TAVILY_API_KEY,
                max_results=num_results
            )
            
            # 执行搜索
            search_results = search_tool.invoke({"query": query})
            
            # 转换结果为SearchItem格式
            results = []
            for item in search_results:
                results.append(SearchItem(
                    title=item.get('title', 'No title'),
                    link=item.get('url', ''),
                    summary=item.get('content', '')
                ))
            
            return results
            
        except Exception as e:
            # 处理错误
            return [SearchItem(
                title="Search Error",
                link="",
                summary=f"Tavily search error: {str(e)}"
            )] 