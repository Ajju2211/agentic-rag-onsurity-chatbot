from langchain.chat_models import ChatOpenAI
from langchain.tools.base import Tool
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain import hub
import logging

logger = logging.getLogger(__name__)

class AgentBuilder:
    def __init__(self, llm: ChatOpenAI, tools: list, prompt_name: str = 'hwchase17/openai-functions-agent'):
        self.llm = llm
        try:
            self.prompt = hub.pull(prompt_name)
        except Exception as e:
            logger.warning('Hub prompt load failed: %s', e)
            self.prompt = None
        self.tools = tools

    def build(self) -> AgentExecutor:
        agent = create_openai_tools_agent(llm=self.llm, tools=self.tools, prompt=self.prompt)
        return AgentExecutor(agent=agent, tools=self.tools, verbose=False)
