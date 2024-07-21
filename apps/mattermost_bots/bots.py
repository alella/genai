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
import shutil
import tempfile
import requests
import os
import PyPDF2
import docx

api_haiku = Claude("anthropic.claude-3-haiku-20240307-v1:0")
api_sonnet = Claude("anthropic.claude-3-sonnet-20240229-v1:0")
api_omni = OpenAIClient("gpt-4o")
api_llama = OllamaClient("llama3")
MAX_TOKENS = 4096


def attachments_to_text(attachments, token):
    # Create a temporary directory to store the attachments
    tmp_dir = tempfile.mkdtemp()
    attachment_text = ""

    for attachment in attachments:
        filename = f"{tmp_dir}/{attachment['name']}"
        with open(filename, "wb") as fp:
            response = requests.get(
                f"http://mattermost.prash.xyz/api/v4/files/{attachment['id']}?download=1",
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
    system_prompt="Your name is Llama. You are a helpful assistant in slack messaging platform. Remember you can use emoji.",
    api_type="ollama",
)


@bot_event_handler(haiku)
async def handle_message_haiku(chat_message: ChatMessage, bot, channel_id, _username):
    resp = bot.invoke(channel_id, chat_message.text)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


@bot_event_handler(sonnet)
async def handle_message_sonnet(chat_message: ChatMessage, bot, channel_id, _username):
    resp = bot.invoke(channel_id, chat_message.text)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


@bot_event_handler(omni)
async def handle_message_omni(chat_message: ChatMessage, bot, channel_id, _username):
    resp = bot.invoke(channel_id, chat_message.text)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


@bot_event_handler(llama)
async def handle_message_llama(chat_message: ChatMessage, bot, channel_id, _username):
    if chat_message.attachments:
        attachment_text = attachments_to_text(
            chat_message.attachments, bot.access_token
        )
        chat_message.text += f"\n-----\n\nThis message contains the following file attachments. This is the content of the uploaded files:\n{attachment_text}"
        print(chat_message.text)
    resp = bot.invoke(channel_id, chat_message.text)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


bot_threads = []
bot_threads.append(threading.Thread(target=haiku.run, args=(handle_message_haiku,)))
bot_threads.append(threading.Thread(target=sonnet.run, args=(handle_message_sonnet,)))
# bot_threads.append(
#     threading.Thread(target=pravalli.run, args=(handle_message_pravalli,))
# )
# bot_threads.append(threading.Thread(target=ashbot.run, args=(handle_message_ashbot,)))
bot_threads.append(threading.Thread(target=omni.run, args=(handle_message_omni,)))
bot_threads.append(threading.Thread(target=llama.run, args=(handle_message_llama,)))

for thread in bot_threads:
    thread.start()
for thread in bot_threads:
    thread.join()
