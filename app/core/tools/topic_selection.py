import json
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class TopicOption(BaseModel):
    """选题选项模型"""
    id: int = Field(description="选项ID")
    title: str = Field(description="选题标题")
    description: str = Field(description="选题描述")
    target_audience: str = Field(description="目标受众")
    content_type: str = Field(description="内容类型")


class TopicSelectionTool:
    """选题选择工具 - 向用户展示选题选项并等待选择"""
    
    def __init__(self):
        self.current_topics: List[TopicOption] = []
        self.user_selection: Optional[int] = None
    
    def present_topics(self, topics_data: str) -> str:
        """
        向用户展示选题选项，格式为 1. {title: ..., description: ...}
        """
        try:
            # 清理输入数据，移除可能的 markdown 标记
            cleaned_data = topics_data.strip()
            if cleaned_data.startswith('```json'):
                cleaned_data = cleaned_data[7:]  # 移除 ```json
            if cleaned_data.endswith('```'):
                cleaned_data = cleaned_data[:-3]  # 移除结尾的 ```
            cleaned_data = cleaned_data.strip()
            
            # 解析选题数据
            if isinstance(cleaned_data, str):
                try:
                    topics_list = json.loads(cleaned_data)
                except json.JSONDecodeError:
                    if "error" in cleaned_data.lower() or "失败" in cleaned_data:
                        topics_list = [
                            {
                                "title": "人工智能发展趋势分析",
                                "description": "深入分析当前AI技术的主要发展方向和趋势"
                            },
                            {
                                "title": "AI在各行业的应用案例",
                                "description": "探讨人工智能在不同行业中的实际应用和效果"
                            },
                            {
                                "title": "人工智能的未来展望",
                                "description": "预测AI技术的未来发展方向和潜在影响"
                            }
                        ]
                    else:
                        topics_list = [{"title": cleaned_data, "description": ""}]
            else:
                topics_list = cleaned_data
            
            # 构建选题选项
            self.current_topics = []
            lines = []
            for i, topic in enumerate(topics_list, 1):
                title = topic.get('title', f'选题{i}') if isinstance(topic, dict) else str(topic)
                description = topic.get('description', '') if isinstance(topic, dict) else ''
                self.current_topics.append(TopicOption(
                    id=i,
                    title=title,
                    description=description,
                    target_audience=topic.get('target_audience', '') if isinstance(topic, dict) else '',
                    content_type=topic.get('content_type', 'article') if isinstance(topic, dict) else 'article'
                ))
                # 格式化为一行 JSON-like
                lines.append(f"{i}. {{title: {title}, description: {description}}}")
            
            presentation = "\n".join(lines)
            presentation += f"\n\n**请回复数字 1-{len(self.current_topics)} 来选择您喜欢的选题：**"
            return presentation
        except Exception as e:
            return f"选题展示错误: {str(e)}"
    
    def process_user_selection(self, user_input: str) -> str:
        """
        处理用户选择
        
        Args:
            user_input: 用户输入的选择（数字）
            
        Returns:
            选择结果
        """
        try:
            # 提取数字
            import re
            numbers = re.findall(r'\d+', user_input)
            if not numbers:
                return "错误：请提供有效的数字选择（1-{}）".format(len(self.current_topics))
            
            selection = int(numbers[0])
            if 1 <= selection <= len(self.current_topics):
                self.user_selection = selection
                selected_topic = self.current_topics[selection - 1]
                return f"已选择选题 {selection}: {selected_topic.title}"
            else:
                return f"错误：选择超出范围，请输入 1-{len(self.current_topics)} 之间的数字"
                
        except Exception as e:
            return f"处理用户选择时出错: {str(e)}"
    
    def get_selected_topic(self) -> Optional[TopicOption]:
        """获取用户选择的选题"""
        if self.user_selection and 1 <= self.user_selection <= len(self.current_topics):
            return self.current_topics[self.user_selection - 1]
        return None
    
    def reset(self):
        """重置工具状态"""
        self.current_topics = []
        self.user_selection = None 