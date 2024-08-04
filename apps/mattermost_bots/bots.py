"""
python -m apps.mattermost_bots.bots
"""

import threading
from pprint import pprint as pr
from core.claude import Claude
from core.bots import MattermostBot, bot_event_handler
from core.clients.openai_client import OpenAIClient
from core.clients.ollama_client import OllamaClient
from core.llm_utils import ChatMessage
from core.marqodb import MarqoIndexer, MarqoSearcher
from core.utils import xml_to_json
from core.brave import brave_search_str
import shutil
import tempfile
import json
import requests
import os
import PyPDF2
import docx

api_haiku = Claude("anthropic.claude-3-haiku-20240307-v1:0")
api_sonnet = Claude("anthropic.claude-3-sonnet-20240229-v1:0")
api_omni = OpenAIClient("gpt-4o")
api_llama = OllamaClient("llama3.1")
MAX_TOKENS = 4096


def attachments_to_text(attachments, token):
    # Create a temporary directory to store the attachments
    tmp_dir = tempfile.mkdtemp()
    attachment_text = ""

    for attachment in attachments:
        filename = f"{tmp_dir}/{attachment['name']}"
        with open(filename, "wb") as fp:
            response = requests.get(
                f"http://10.0.0.226:8065/api/v4/files/{attachment['id']}?download=1",
                timeout=60,
                headers={"Authorization": f"Bearer {token}"},
            )
            for chunk in response.iter_content():
                fp.write(chunk)

        if attachment["extension"] in ["txt", "md", "log"]:
            with open(filename, "r") as fp:
                content = fp.read()
        elif attachment["extension"] == "pdf":
            with open(filename, "rb") as fp:
                pdf_reader = PyPDF2.PdfReader(fp)
                content = "".join(
                    [
                        pdf_reader.pages[i].extract_text()
                        for i in range(len(pdf_reader.pages))
                    ]
                )
        elif attachment["extension"] in ["doc", "docx"]:
            doc = docx.Document(filename)
            fullText = []
            for para in doc.paragraphs:
                fullText.append(para.text)
            content = "\n".join(fullText)
        attachment_text += f"<file:{os.path.basename(filename)}>\n{content}\n</file:{os.path.basename(filename)}>\n\n"
    shutil.rmtree(tmp_dir)

    return attachment_text


haiku = MattermostBot(
    "Haiku",
    api_haiku,
    "ar3uwj1d5tgkjmozt1crqnkawh",
    system_prompt="Your name is Haiku. You are talking to a close friend in slack messaging platform. Use plenty of emoji. If your friend is asking to solve the problem, feel free to ask for follow-up questions if you feel like there is insufficient information to solve the problem. Similar to text messages, try to keep your conversations short (1 to 2 sentences)",
)

sonnet = MattermostBot(
    "Sonnet",
    api_sonnet,
    "utn1kw4g4tgntprrdxs1meg3jy",
    system_prompt="Your name is Sonnet. You are talking to a close friend in slack messaging platform. Use plenty of emoji. You are a super mega nerd extreme. If your friend is asking to solve the problem. Your have a friendly and quirky personality. Feel free to ask for follow-up questions if you feel like there is insufficient information to solve the problem.",
)

omni = MattermostBot(
    "Omni",
    api_omni,
    "9qu1izhzjinb5bd4k5bwf5tmky",
    system_prompt="Your name is Omni. You are a helpful assistant in slack messaging platform. Remember you can use emoji.",
    api_type="openai",
)

llama = MattermostBot(
    "Llama",
    api_llama,
    "zu1o64cobffmbq9so331riq4mc",
    max_message_count=20,
    system_prompt="Your name is Llama. You are a talking to your friend in slack messaging platform. Remember you can use emoji.",
    api_type="ollama",
)

nemo = MattermostBot(
    "nemo",
    api_llama,
    "5mmmj6tp17bxjpdftugeh6rjqy",
    max_message_count=3,
    system_prompt="Your name is nemo. Your assist other chat agents with user specific memory.",
    api_type="ollama",
)


@bot_event_handler(haiku)
async def handle_message_haiku(chat_message: ChatMessage, bot, channel_id, _username):
    if chat_message.type != "text":
        return
    resp = bot.invoke(channel_id, chat_message.text)
    debug_info = (
        f"\n**Cost**: {resp['cost_str']}"
        f"\n**Input Tokens**: {resp['input_tokens']} tokens"
        f"\n**Max Output Tokens set**: {resp['max_output_tokens']} tokens"
        f"\n**Output Tokens**: {resp['output_tokens']} tokens"
        f"\n**Session Cost**: {resp['session_cost']:.3f} USD"
        f"\n**Session Start time**: {resp['session_start_time']}"
    )
    root = bot.driver.posts.create_post(
        {"channel_id": channel_id, "message": resp["raw_content"]}
    )
    bot.driver.posts.create_post(
        {"channel_id": channel_id, "message": debug_info, "root_id": root["id"]}
    )


@bot_event_handler(sonnet)
async def handle_message_sonnet(chat_message: ChatMessage, bot, channel_id, _username):
    if chat_message.type != "text":
        return
    resp = bot.invoke(channel_id, chat_message.text)
    debug_info = (
        f"\n**Cost**: {resp['cost_str']}"
        f"\n**Input Tokens**: {resp['input_tokens']} tokens"
        f"\n**Max Output Tokens set**: {resp['max_output_tokens']} tokens"
        f"\n**Output Tokens**: {resp['output_tokens']} tokens"
        f"\n**Session Cost**: {resp['session_cost']:.3f} USD"
        f"\n**Session Start time**: {resp['session_start_time']}"
    )
    root = bot.driver.posts.create_post(
        {"channel_id": channel_id, "message": resp["raw_content"]}
    )
    bot.driver.posts.create_post(
        {"channel_id": channel_id, "message": debug_info, "root_id": root["id"]}
    )


@bot_event_handler(omni)
async def handle_message_omni(chat_message: ChatMessage, bot, channel_id, _username):
    if chat_message.type != "text":
        return
    resp = bot.invoke(channel_id, chat_message.text)
    root = bot.driver.posts.create_post(
        {"channel_id": channel_id, "message": resp["raw_content"]}
    )
    bot.driver.posts.create_post(
        {"channel_id": channel_id, "message": resp["debug"], "root_id": root["id"]}
    )


def format_memory(results):
    text = ""
    if results:
        results_str = "\n-".join(results)
        print(results_str)
        text += (
            f"\nHere are some memory snippets you may use to respond:\n {results_str}"
        )
    return text


def retrieve_memory(user_id, text):
    mi = MarqoSearcher()
    results = mi.search("memory", text)
    print("performing a memory search")
    text = format_memory(results)
    return text


@bot_event_handler(llama)
async def handle_message_llama(chat_message: ChatMessage, bot, channel_id, _username):
    mi = MarqoSearcher()
    if chat_message.type != "text":
        return
    if chat_message.attachments:
        attachment_text = attachments_to_text(
            chat_message.attachments, bot.access_token
        )
        chat_message.text += f"\n-----\n\nThis message contains the following file attachments. This is the content of the uploaded files:\n{attachment_text}"

    results = mi.search("memory", chat_message.text)
    if results:
        chat_message.text += format_memory(results)

    if "+brave" in chat_message.text:
        chat_message.text = chat_message.text.replace("+brave", "")
        search = brave_search_str(chat_message.text)
        chat_message.text += f"\nHere are some internet search results, use them to cite your response:\n {search}"
    resp = bot.invoke(channel_id, chat_message.text)
    root = bot.driver.posts.create_post(
        {"channel_id": channel_id, "message": resp["raw_content"]}
    )
    if results:
        resp["debug"]["memory"] = format_memory(results)
    bot.driver.posts.create_post(
        {
            "channel_id": channel_id,
            "message": "\n".join(f"**{k}** : {v}" for k, v in resp["debug"].items()),
            "root_id": root["id"],
        }
    )


@bot_event_handler(nemo)
async def handle_message_nemo(chat_message: ChatMessage, bot, channel_id, username):
    if chat_message.type == "reaction":
        reaction = json.loads(chat_message.text)
        emoji = reaction["emoji_name"]
        print(f"should I react to : {emoji}")
        if emoji in ["memo", "clipboard"]:
            mi = MarqoIndexer()
            post_id = reaction["post_id"]
            post = bot.driver.posts.get_post(post_id)
            msg = post["message"]
            username = bot.driver.users.get_user(user_id=post["user_id"])["username"]
            fact = bot.invoke(
                channel_id,
                f"""Extract the fact in the <text_message>. 
                This message is from the username @{username}. 
                Write the fact in 3rd person. Include specific details. Don't hallucinate.
                Return the fact in <fact> xml tag.\n<text_message>\n{msg}\n</text_message>""",
            )
            facts = xml_to_json(fact["raw_content"])
            print(fact)
            print(facts)
            if "fact" in facts:
                bot.driver.posts.create_post(
                    {"channel_id": channel_id, "message": facts["fact"]}
                )
                resp = mi.index_snippet("memory", reaction["user_id"], facts["fact"])
                memory_id = resp["items"][0]["_id"]
                print(memory_id)
                memory_channel_id = "5wndk8x3gtre7xjzy43d7jj8gr"
                bot.driver.posts.create_post(
                    {
                        "channel_id": memory_channel_id,
                        "message": f"`{memory_id}` :" + facts["fact"],
                    }
                )
                print(resp)
    # resp = bot.invoke(channel_id, chat_message.text)
    # root = bot.driver.posts.create_post(
    #     {"channel_id": channel_id, "message": resp["raw_content"]}
    # )


bot_threads = []
# bot_threads.append(threading.Thread(target=haiku.run, args=(handle_message_haiku,)))
# bot_threads.append(threading.Thread(target=sonnet.run, args=(handle_message_sonnet,)))
# bot_threads.append(threading.Thread(target=omni.run, args=(handle_message_omni,)))
bot_threads.append(threading.Thread(target=llama.run, args=(handle_message_llama,)))
bot_threads.append(threading.Thread(target=nemo.run, args=(handle_message_nemo,)))

for thread in bot_threads:
    thread.start()
for thread in bot_threads:
    thread.join()
