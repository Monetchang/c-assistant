import json
import os
from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.prompt.writer import OUTLINE_GENERATION_PROMPT, ARTICLE_WRITING_PROMPT


class ArticleOutline(BaseModel):
    """文章大纲模型"""
    title: str = Field(description="文章标题")
    introduction: str = Field(description="引言部分")
    sections: List[Dict[str, str]] = Field(description="章节列表")
    conclusion: str = Field(description="结论部分")


class ArticleContent(BaseModel):
    """文章内容模型"""
    title: str = Field(description="文章标题")
    content: str = Field(description="完整文章内容")
    word_count: int = Field(description="字数统计")
    sections: List[Dict[str, str]] = Field(description="章节内容")


class WriterTool:
    """写作工具 - 基于LLM实现"""
    
    def __init__(self):
        os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
        self.llm = ChatDeepSeek(model="deepseek-chat")
    
    def create_outline(
        self, 
        topic: str, 
        content_type: str = "article",
        target_length: str = "medium",
        *args, **kwargs
    ) -> ArticleOutline:
        """
        创建文章大纲
        
        Args:
            topic: 文章主题
            content_type: 内容类型 (article, blog, report, etc.)
            target_length: 目标长度 (short, medium, long)
            
        Returns:
            文章大纲
        """
        try:
            # 构建prompt
            prompt_content = OUTLINE_GENERATION_PROMPT.format(
                topic=topic,
                content_type=content_type,
                target_length=target_length
            )
            
            # 使用LLM生成大纲
            messages = [SystemMessage(content=prompt_content)]
            response = self.llm.invoke(messages)
            
            # 尝试解析JSON响应
            try:
                outline_data = json.loads(str(response.content))
                return ArticleOutline(
                    title=outline_data.get('title', f"{topic} - {content_type.title()}"),
                    introduction=outline_data.get('introduction', ''),
                    sections=outline_data.get('sections', []),
                    conclusion=outline_data.get('conclusion', '')
                )
            except json.JSONDecodeError:
                # 如果JSON解析失败，返回默认大纲
                return ArticleOutline(
                    title=f"{topic} - {content_type.title()}",
                    introduction=f"本文将深入探讨{topic}这一重要主题",
                    sections=[
                        {"title": "引言", "description": "介绍主题背景和重要性"},
                        {"title": "主要内容", "description": "详细阐述主题内容"},
                        {"title": "结论", "description": "总结要点和展望"}
                    ],
                    conclusion="通过以上分析，我们可以得出相关结论和启示"
                )
            
        except Exception as e:
            return ArticleOutline(
                title="大纲生成错误",
                introduction="",
                sections=[],
                conclusion=f"生成大纲时出现错误: {str(e)}"
            )
    
    def write_article(
        self, 
        outline: ArticleOutline,
        additional_info: str = "",
        style: str = "professional",
        *args, **kwargs
    ) -> str:
        """
        根据大纲编写完整文章
        
        Args:
            outline: 文章大纲
            additional_info: 额外信息或参考资料
            style: 写作风格 (professional, casual, academic)
            
        Returns:
            完整文章内容字符串
        """
        try:
            # 构建prompt
            prompt_content = ARTICLE_WRITING_PROMPT.format(
                style=style,
                outline=json.dumps(outline.dict(), ensure_ascii=False, indent=2),
                additional_info=additional_info
            )
            
            # 使用LLM生成文章
            messages = [SystemMessage(content=prompt_content)]
            response = self.llm.invoke(messages)
            
            return str(response.content)
            
        except Exception as e:
            return f"文章生成错误: {str(e)}"
    
    def write_article_from_topic(
        self, 
        topic: str,
        additional_info: str = "",
        style: str = "professional",
        *args, **kwargs
    ) -> str:
        """
        根据主题直接编写文章
        
        Args:
            topic: 文章主题
            additional_info: 额外信息或参考资料
            style: 写作风格 (professional, casual, academic)
            
        Returns:
            完整文章内容字符串
        """
        try:
            # 先创建大纲
            outline = self.create_outline(topic)
            # 再写文章
            return self.write_article(outline, additional_info, style)
        except Exception as e:
            return f"文章生成错误: {str(e)}"