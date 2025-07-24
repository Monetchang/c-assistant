from typing import List
from app.core.tools.search.base import SearchItem
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from app.core.config import settings
import os
import getpass


class TavilySearchEngine:
    """Tavily搜索引擎"""
    
    @staticmethod
    @tool()
    def perform_search(
        query: str, num_results: int = 2, *args, **kwargs
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
            os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY
  
            # 使用Tavily搜索工具
            search_tool = TavilySearch(
                max_results=num_results,
                topic="general",
            )
            
            # 执行搜索
            search_results = search_tool.invoke({"query": query})
            
            # 解析TavilySearch返回的结果
            if isinstance(search_results, dict):
                # 如果返回的是字典，提取results数组
                results_list = search_results.get('results', [])
                results = []
                for item in results_list:
                    if isinstance(item, dict):
                        results.append(SearchItem(
                            title=item.get('title', 'No title'),
                            link=item.get('url', ''),
                            summary=item.get('content', '')
                        ))
                    else:
                        results.append(SearchItem(
                            title="Search Result",
                            link="",
                            summary=str(item)
                        ))
                return results
            elif isinstance(search_results, str):
                # 如果返回的是字符串，直接返回
                return [SearchItem(
                    title="Search Results",
                    link="",
                    summary=search_results
                )]
            elif isinstance(search_results, list):
                # 如果返回的是列表，转换结果为SearchItem格式
                results = []
                for item in search_results:
                    if isinstance(item, dict):
                        results.append(SearchItem(
                            title=item.get('title', 'No title'),
                            link=item.get('url', ''),
                            summary=item.get('content', '')
                        ))
                    else:
                        results.append(SearchItem(
                            title="Search Result",
                            link="",
                            summary=str(item)
                        ))
                return results
            else:
                # 其他情况，返回原始结果
                return [SearchItem(
                    title="Search Results",
                    link="",
                    summary=str(search_results)
                )]
            
        except Exception as e:
            # 处理错误
            return [SearchItem(
                title="Search Error",
                link="",
                summary=f"Tavily search error: {str(e)}"
            )] 