from langchain_openai import ChatOpenAI

class AgentBuilder:
    def __init__(self, api_key=None, model_name="gpt-4o-mini"):
        self.api_key = api_key
        self.model_name = model_name

    def build(self):
        if not self.api_key:
            return None
        return ChatOpenAI(api_key=self.api_key, model=self.model_name, temperature=0)
