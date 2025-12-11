import os
try:
    from langchain_groq import ChatGroq
    HAS_GROQ = True
except Exception:
    HAS_GROQ = False

from langchain_openai import ChatOpenAI

class AgentBuilder:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

    def build(self):
        if self.groq_key and HAS_GROQ:
            return ChatGroq(api_key=self.groq_key, model="llama3-groq-70b-8192", temperature=0)
        if self.openai_key:
            return ChatOpenAI(api_key=self.openai_key, model="gpt-4o-mini", temperature=0)
        return None
