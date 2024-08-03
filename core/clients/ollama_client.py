import os
from ollama import Client


class OllamaClient:
    def __init__(self, model):
        self.model = model
        self.client = Client(host="http://10.0.0.9:11434")

    def invoke_chat(self, messages, system="", tokens=1024):
        if system:
            messages = [{"role": "system", "content": system}] + messages
        else:
            messages = messages.get_ollama_messages()
        response = self.client.chat(
            model=self.model, messages=messages, options={"num_ctx": tokens}
        )

        total_duration = int(response["total_duration"]) / 1000000000
        debug_info = {
            "Done Reason": response["done_reason"],
            "Done": response["done"],
            "Total Duration": f"{total_duration:.1f} sec",
            "Output Tokens": f"{response['eval_count']} tokens",
        }

        return {
            "raw_content": response["message"]["content"],
            "debug": debug_info,
        }

    def invoke(self, message: str, system="", tokens=4096):
        if system:
            messages = [{"role": "system", "content": system}] + [
                {"role": "user", "content": message}
            ]
        else:
            messages = [{"role": "user", "content": message}]
        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={"num_ctx": tokens, "format": "json"},
        )
        return {"raw_content": response["message"]["content"]}
