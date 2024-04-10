# https://github.com/marqo-ai/marqo/blob/mainline/examples/GPT-examples/article/article.md

import marqo
from utils import setup_logging
import json
from claude import Claude

logger = setup_logging()
mq = marqo.Client(url="http://localhost:8882")

RAG_PROMPT = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
Use three sentences maximum and keep the answer as concise as possible.
Always say "thanks for asking!" at the end of the answer. The context starts with the word "Context:"

Context:
{context}

Question: {question}

Helpful Answer:"""

RAG_PROMPT = """Use the following pieces of context to answer the question at the end. The context 
consists of my journal entries and thoughts. My name is Ashoka.
At the end rate how confident are you about the answer on a scale of 1 to 10.
Use three sentences maximum and keep the answer as concise as possible.
Always say "thanks for asking!" at the end of the answer. The context starts with the word "Context:"

Context:
{context}

Question: {question}

Helpful Answer:"""


def get_context(query, body, window_length):
    start_index = body.lower().find(query.lower())
    if start_index == -1:
        return query

    # Find the start and end indices of the context window
    start_word = max(0, start_index - window_length // 2)
    end_word = min(len(body) - 1, start_index + len(query) + window_length // 2)

    return body[start_word:end_word]


question = "Can you immitate Ashoka and write a journal entry? Try writing about waking up and about working out and write about office work (mention how many pomodoros) and evening activities with Pravalli and then sleeping routine. Feel free to makeup scenarios and dont be vauge. Write in 400 words or more."
# question = "Does Ashoka enjoys cycling? What type of rides does he like?"
results = mq.index("journal").search(q=question, limit=8)
results = [t for t in results["hits"] if t["_score"] > 0.8]
logger.info(json.dumps(results, indent=2))
results = [
    get_context(t["_highlights"][0]["Content"], t["Content"], 500) for t in results
]
logger.info("Results from db query")
prompt = RAG_PROMPT.format(
    context="\n\n\n-----\n\n\n".join(results),
    question=question,
)
logger.info(f"Generated prompt (length={len(prompt)})")
logger.info(prompt)
llm = Claude("anthropic.claude-3-haiku-20240307-v1:0")
resp = llm.invoke(prompt, "output.md")
logger.info("Response from Claude")
logger.info(resp["content"])
