# https://github.com/marqo-ai/marqo/blob/mainline/examples/GPT-examples/article/article.md

from core.claude import Claude
from core.prompts import Prompt
from core.marqodb import MarqoSearcher


ms = MarqoSearcher()
llm = Claude("anthropic.claude-3-haiku-20240307-v1:0")
rag_prompt = Prompt(
    "{question}",
    system_prompt_template="""Use the following pieces of context to address the user request. The context 
(in xml tag) consists  of my journal entries and thoughts. My name is Ashoka.
At the end rate how confident are you about the answer on a scale of 1 to 10.
Use three sentences maximum and keep the answer as concise as possible.

<context>
{context}
</context>


Helpful Answer:""",
)


question = "tell me about cycling and Ashoka"
results = ms.search("journal", question)
rag_prompt.set_kwargs(question=question, context="\n\n---\n\n".join(results))
resp = rag_prompt.invoke(llm)
print(resp["raw_content"])
