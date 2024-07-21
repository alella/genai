import os
from ollama import Client

class OllamaClient:
    def __init__(self, model):
        self.model = model
        self.client = Client(host='http://10.0.0.9:11434')

    def invoke_chat(self, messages, system="", tokens=1024):
        if system:
            messages = [{"role": "system", "content": system}] + messages
        else:
            messages = messages.get_ollama_messages()
        response = self.client.chat(
            model=self.model,
            messages=messages
        )
        return {"raw_content": response['message']['content']}
