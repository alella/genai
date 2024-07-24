import re
from core.clients.ollama_client import OllamaClient
from core.bots import MattermostBot

llama = OllamaClient("llama3.1")
bot = MattermostBot(
    "Llama",
    llama,
    "zu1o64cobffmbq9so331riq4mc",
    max_message_count=20,
    system_prompt="Your name is Llama. You are a helpful assistant in slack messaging platform. Remember you can use emoji.",
    api_type="ollama",
)

p1 = """
Write a chapter by chapter arc for a short story based on this description. 

A science fiction story about a mission to Mars that goes wrong while humans return to Earth.
The space ship alters course and accidentally is on the path to Washington DC. NASA team is on fire 
and tries to cordinate between astronauts in spaceship and hope for a safe landing. Elon Musk keeps
a close eye on the while situation, swoops in and saves the data with SpaceX technology.
Think of cool names for Musk's team an NASA's team.

Use 20 chapters.

Use the following format for output:
<chapter1>
Title
Description or Summary
</chapter1>
<chapter2>
Title
Description or Summary
</chapter2>
...
"""
print("=====" * 30)
outline = llama.invoke(p1)["raw_content"]


def parse_xml_tags(text):
    pattern = r"<([^<>]+)>"
    matches = re.finditer(pattern, text)
    tags = []
    i = 0
    j = 0
    for match in matches:
        tag = match.group(1).strip()
        if tag.startswith("/"):
            j = text.index(match.group(0))
            tags[-1][-1] = text[i:j]
            continue  # Skip closing tags
        else:
            i = text.index(match.group(0)) + len(match.group(0))
        tags.append([tag, None])
    return tags


tags = parse_xml_tags(outline)


for i, chapters in enumerate(tags):
    chapter, text = chapters
    book = []
    if i == 0:
        p2 = f"""
        Instructions: Complete {chapter} following the guide below, 
        it should be as long as possible and in Neil Gaiman's narrative. 
        Your output should only contain the content of {chapter}.
        Output should be in markdown format.

        Guide: {text}
        """
        chapter1_story = llama.invoke(p2)["raw_content"]
        print(chapter)
        print(chapter1_story)
        bot.driver.posts.create_post(
            {"channel_id": "358udwdorpf1ipjkhh7ro7qdua", "message": chapter1_story}
        )
        book.append(chapter1_story)
        summary = llama.invoke(
            f"Read the chapter content and summarize it. Don't leave any important details. Be as detailed as possible. Include a section that tells how the story so far stops. List all characters in the story and describe them. \n<chapter>\n{chapter1_story}\n</chapter>"
        )["raw_content"]
        # print(summary)
        continue
    p4 = f"""
    Instructions: complete the {chapter} using the previous story <summary>, <previous_story> and the current chapter <guide>. 
    Do not repeat what is already in summary or in <previous_chapter> but try to continue the story.
    It is not necessary to stick to the guide. The output should be as long as possible and in Neil Gaiman's narrative. 
    This is the {i+1} chapter of the book. Output should be in markdown format.

    <guide>\n{text}\n</guide>

    <summary> \n{summary}\n</summary>
    <previous_chapter> \n{summary}\n</previous_chapter>
    """
    chaptern_story = llama.invoke(p4)["raw_content"]
    print("-" * 20)
    print(chapter)
    print(chaptern_story)
    bot.driver.posts.create_post(
        {"channel_id": "358udwdorpf1ipjkhh7ro7qdua", "message": chaptern_story}
    )
    book.append(chaptern_story)
    summary = llama.invoke(
        f"Read the story so far and summarize it. Don't leave any important details. Be as detailed as possible. Include a section that tells how the story so far stops. List all characters in the story and describe them. \n <previous_summary>\n{summary}\n</previous_summary>\n\n \n<chapter>\n{chaptern_story}\n</chapter>"
    )["raw_content"]
    # print(summary)


# print(llama.invoke(p1)["raw_content"])

with open("book.md", "w") as w:
    for b in book:
        w.write(b)
