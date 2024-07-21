import os
from openai import OpenAI


class OpenAIClient:
    def __init__(self, model):
        self.model = model
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
        )

    def invoke_chat(self, messages, system="", tokens=None):
        if system:
            messages = [{"role": "system", "content": system}] + messages
        else:
            messages = messages.get_openai_messages()
        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
        )
        debug_info = (
            f"\n**Completion Tokens**: {response.usage.completion_tokens}"
            f"\n**Prompt Tokens**: {response.usage.prompt_tokens}"
            f"\n**Total Tokens**: {response.usage.total_tokens}"
        )
        return {"raw_content": response.choices[0].message.content, "debug": debug_info}
