import getpass
import os
from langchain_deepseek import ChatDeepSeek

os.environ["DEEPSEEK_API_KEY"] = ""

llm = ChatDeepSeek(model_name="deepseek-chat")