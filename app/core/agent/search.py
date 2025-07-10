
from app.core.agent.base import AgentBase
from langchain.agents import create_react_agent

class SearchAgent(AgentBase):
    def __init__(self):
        super().__init__()  # 调用基类的 __init__

    def initialize_agent(self):
        db_agent = create_react_agent(
            self.llm, 
            tools=[], 
            state_modifier="You use to perform database operations while should provide accurate data for the code_generator to use"
        )
