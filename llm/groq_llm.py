import os
from groq import Groq


class GroqLLMWrapper:
    def __init__(self, model_name="llama-3.3-70b-versatile", temperature=0.0):
        self.model_name = model_name
        self.temperature = temperature

        api = os.getenv("GROQ_API_KEY")
        if not api:
            raise ValueError("Set GROQ_API_KEY in environment.")

        self.client = Groq(api_key=api)

    def chat(self, system_msg: str, user_msg: str):
        """
        Groq new SDK returns:
        res.choices[0].message.content   <-- correct
        NOT dict access.
        """
        try:
            res = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=self.temperature,
                max_tokens=4096,
            )

            # FIX: Correct Groq SDK access
            return res.choices[0].message.content

        except Exception as e:
            return f"LLM Error: {e}"
