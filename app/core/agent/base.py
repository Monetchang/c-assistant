import os
from pydantic import BaseModel, Field
from app.core.config import settings
from langchain_deepseek import ChatDeepSeek

class AgentBase(BaseModel):
    def __init__(self):
        os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY

        self.llm = ChatDeepSeek(model="deepseek-chat")
        
    def initialize_agent(self) -> "BaseAgent":
        """Initialize agent with default settings if not provided."""
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(config_name=self.name.lower())
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        return self