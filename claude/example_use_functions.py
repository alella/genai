from llm_utils import llm_tool, ToolPrompt, LLMFNS
from claude import Claude
from pprint import pprint as pr
from utils import setup_logging

log = setup_logging()


@llm_tool
def multiply(a: int, b: int) -> int:
    """
    Multiply a number 'a' with a number 'b' and return the output as integer.
    """
    return a * b


@llm_tool
def add(a: int, b: int) -> int:
    """
    Add two numbers 'a' and 'b' and return the output as integer.
    """
    return a + b


@llm_tool
def hash(a: int, b: int) -> int:
    """
    computes a unique has using the integers 'a' and 'b'
    """
    return str(a) + str(b)


@llm_tool
def file_length(filename: str) -> int:
    return len(filename) * 10


@llm_tool
def string_length(filename: str) -> int:
    return len(filename)


api = Claude("anthropic.claude-3-haiku-20240307-v1:0")

questions = [
    "What is the hash of 22 and 25?",
    "What is the sum of 22 and 25?",
    "what is 10 times 33?",
    "what is 20 - 23?",
    "what is the length of the file 'numbers.txt'",
    "how big is earth?",
    "how long is 'earth'?",
]
for q in questions:
    print(f"User : {q}")
    prompt = ToolPrompt(q)
    result = prompt.invoke(api, tokens=1024)
    print(f'AI   : {result["raw_content"]}')
