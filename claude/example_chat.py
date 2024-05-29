import json
from llm_utils import llm_tool, ToolPrompt, LLMFNS, Bot
from claude import Claude
from pprint import pprint as pr
from utils import setup_logging

log = setup_logging()
api = Claude("anthropic.claude-3-haiku-20240307-v1:0")

haiku = Bot(
    "Haiku",
    api,
    system_prompt="Your name is Haiku. You are talking to a close friend. Use plenty of unicode emoji. If your friend is asking to solve the problem, feel free to ask for follow-up questions if you feel like there is insufficient information to solve the problem.",
)

while True:
    message = input("User: ")
    resp = haiku.invoke(message)
    print(f"{haiku.name}: {resp['raw_content']}")
