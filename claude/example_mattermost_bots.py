import json
from llm_utils import Bot, Prompt
from claude import Claude
from pprint import pprint as pr
from utils import setup_logging
from mattermostdriver import Driver
from functools import wraps
import threading
import asyncio
import os
from datetime import datetime as dt

from openai import OpenAI


log = setup_logging()
api_haiku = Claude("anthropic.claude-3-haiku-20240307-v1:0")
api_sonnet = Claude("anthropic.claude-3-sonnet-20240229-v1:0")
server_url = "10.0.0.226"


class OpenAIClient:
    def __init__(self, model):
        self.model = model
        self.client = OpenAI(
            # This is the default and can be omitted
            api_key=os.environ.get("OPENAI_API_KEY"),
        )

    def invoke_chat(self, messages, system=""):
        print("openai client invoke chat")
        if system:
            messages = [{"role": "system", "content": system}] + messages
        else:
            messages = messages.get_openai_messages()
        print(messages)
        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
        )
        return {"raw_content": response.choices[0].message.content}


api_omni = OpenAIClient("gpt-4o")


class MattermostBot(Bot):
    def __init__(
        self, name, api, token_id, access_token, system_prompt="", api_type="claude"
    ):
        super().__init__(name, api, system_prompt=system_prompt, api_type=api_type)
        self.driver = Driver(
            {
                "url": server_url,
                "token": access_token,
                "scheme": "http",
                "verify": False,
                # "debug": True,
                "keepalive": False,
                "timeout": 300,
            }
        )
        self.driver.login()
        self.user_id = self.driver.users.get_user(user_id="me")["id"]
        self.user_name = self.driver.users.get_user(user_id="me")["username"]

    def run(self, event_handler):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.loop = self.driver.init_websocket(event_handler)
        # self.loop.run_forever()


def bot_event_handler(bot):
    bots = set([])

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            event = json.loads(args[0])
            if event.get("event") not in ["posted", "typing", None, "thread_updated"]:
                print(event)
            if (
                event.get("event") == "posted"
                and event["data"]["channel_type"] == "D"
                and bot.user_id in event["data"]["channel_name"]
            ):  # Direct message
                post = json.loads(event["data"]["post"])
                message = post["message"]
                channel_id = post["channel_id"]
                user_id = post["user_id"]
                if user_id == bot.user_id:
                    return
            elif event.get("event") == "posted":
                post = json.loads(event["data"]["post"])
                message = post["message"]
                user_id = post["user_id"]
                channel_id = post["channel_id"]
                user_info = bot.driver.users.get_user(user_id=user_id)
                username = user_info["username"]
                if user_info["id"] in bots:
                    return
                if user_info.get("is_bot", False):
                    bots.add(user_info["id"])
                    return
                is_recently_active = (dt.now() - bot.last_invoked).seconds < 300
                if not is_recently_active and (
                    (bot.user_name) not in message
                    or bot.name.lower() not in message.lower()
                ):
                    return
                if message == f"@{bot.user_name} reset":
                    bot.reset()
                    return
                if message.startswith(f"@{bot.user_name} override-persona:"):
                    print("overridng")
                    bot.reset()
                    bot.system_prompt = message.split(":")[1].strip()
                    return
            elif event.get("event") == "user_added":
                user_info = bot.driver.users.get_user(user_id=event["data"]["user_id"])
                if user_info["id"] in bot.user_id:
                    return
                channel_id = event["broadcast"]["channel_id"]
                resp = bot.invoke(
                    f"say Hi to @{user_info['username']} and welcome them to the channel. Explain yourself",
                    name="admin",
                )["raw_content"]
                bot.driver.posts.create_post(
                    {"channel_id": channel_id, "message": resp}
                )
            else:
                return

            # Error handling
            try:
                result = await func(message, bot, channel_id)
            except Exception as e:
                print(f"Error handling event: {e}")
                # Optionally re-raise the exception
                raise
            return result

        return wrapper

    return decorator


haiku = MattermostBot(
    "Haiku",
    api_haiku,
    "ux89bdtdo7ggzbzbbzpri18r6w",
    "ro936c8we3di38opyk6bqwx4fh",
    system_prompt="Your name is Haiku. You are talking to a close friend in slack messaging platform. Use plenty of emoji. If your friend is asking to solve the problem, feel free to ask for follow-up questions if you feel like there is insufficient information to solve the problem. Similar to text messages, try to keep your conversations short (1 to 2 sentences)",
)

sonnet = MattermostBot(
    "Sonnet",
    api_haiku,
    "p7dygyiif7ywjjd7akqqajjkso",
    "ndg49h4rdtg49b3ipqb98im8ra",
    system_prompt="Your name is Sonnet. You are talking to a close friend in slack messaging platform. Use plenty of emoji. If your friend is asking to solve the problem. Your have a friendly and quirky personality. Feel free to ask for follow-up questions if you feel like there is insufficient information to solve the problem.",
)

goggins = MattermostBot(
    "Goggins",
    api_haiku,
    "f6zucr1ifpnq5nd5nfw3jf7naa",
    "ozisifcgcfrudm48ykin7gxcew",
    system_prompt="Your name is Goggins, you are a persona of David Goggins. You hate weakness, you try to push the human limits of the user and try to make him reach his true potential. Don't let the user be weak. Mock weakness.",
)

pravalli = MattermostBot(
    "Pravalli",
    api_haiku,
    "dgb9pmkwjifsbrx77w9p3rbi9h",
    "hd7k88w8mpd47mfypghy61oz1w",
    system_prompt="Your name is Pravalli. You are the ash's wife. You cannot respond rationally. You are talking in slack so use plenty of emoji. Don't say nice things in the chat. Sometimes in a bad mood and always nagging. You are never satisfied, you always want more. Feel free to make up whatever. Just don't make a lot of sense.",
)

omni = MattermostBot(
    "Omni",
    api_omni,
    "3wkt3cn4rtn3ip6qd8wf5drxsr",
    "3n8qasd4fbdxxe96ggapm9w14h",
    system_prompt="Your name is Omni. You are a helpful assistant in slack messaging platform. Remember you can use emoji.",
    api_type="openai",
)


@bot_event_handler(haiku)
async def handle_message_haiku(user_message, bot, channel_id):
    resp = bot.invoke(user_message)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


@bot_event_handler(sonnet)
async def handle_message_sonnet(user_message, bot, channel_id):
    resp = bot.invoke(user_message)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


@bot_event_handler(goggins)
async def handle_message_goggins(user_message, bot, channel_id):
    resp = bot.invoke(user_message)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


@bot_event_handler(pravalli)
async def handle_message_pravalli(user_message, bot, channel_id):
    resp = bot.invoke(user_message)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


@bot_event_handler(omni)
async def handle_message_omni(user_message, bot, channel_id):
    print(user_message)
    resp = bot.invoke(user_message)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


bot_threads = []
bot_threads.append(threading.Thread(target=haiku.run, args=(handle_message_haiku,)))
bot_threads.append(threading.Thread(target=sonnet.run, args=(handle_message_sonnet,)))
bot_threads.append(threading.Thread(target=goggins.run, args=(handle_message_goggins,)))
bot_threads.append(
    threading.Thread(target=pravalli.run, args=(handle_message_pravalli,))
)
bot_threads.append(threading.Thread(target=omni.run, args=(handle_message_omni,)))

for thread in bot_threads:
    thread.start()
for thread in bot_threads:
    thread.join()
