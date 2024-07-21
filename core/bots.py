import asyncio
import json
from datetime import datetime as dt
from mattermostdriver import Driver
from functools import wraps
from core.llm_utils import ChatMessage
import pprint

from core.prompts import Messages


class Bot:
    def __init__(
        self,
        name,
        api,
        system_prompt="",
        max_message_count=8,
        api_type="claude",
    ):
        self.name = name
        self.api = api
        self.system_prompt = system_prompt
        self.max_message_count = max_message_count
        self.history = {}
        self.last_invoked = dt.strptime("01/01/1970", "%d/%m/%Y")
        self.api_type = api_type

    def invoke(self, context: str, message: str, tokens=1024):
        context_hash = hash(context)
        if context_hash not in self.history:
            self.history[context_hash] = Messages(max_count=self.max_message_count)

        self.history[context_hash].push("user", message)
        if self.api_type == "openai":
            messages = self.history[context_hash].get_openai_messages()
        elif self.api_type == "ollama":
            messages = self.history[context_hash].get_ollama_messages()
        else:
            messages = self.history[context_hash].get_claude_messsages()

        resp = self.api.invoke_chat(messages, self.system_prompt, tokens=tokens)
        self.history[context_hash].push("assistant", resp["raw_content"])
        self.last_invoked = dt.now()
        return resp

    def reset(self, context: str):
        context_hash = hash(context)
        if context_hash in self.history:
            self.history[context_hash] = Messages(max_count=self.max_message_count)
        self.last_invoked = dt.strptime("01/01/1970", "%d/%m/%Y")


class MattermostBot(Bot):
    def __init__(
        self,
        name,
        api,
        access_token,
        max_message_count=8,
        system_prompt="",
        api_type="claude",
        server_url="10.0.0.226",
    ):
        super().__init__(
            name,
            api,
            system_prompt=system_prompt,
            api_type=api_type,
            max_message_count=max_message_count,
        )
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
        self.access_token = access_token
        self.user_id = self.driver.users.get_user(user_id="me")["id"]
        self.user_name = self.driver.users.get_user(user_id="me")["username"]

    def run(self, event_handler):
        print(f"running loop for {self.name}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.driver.init_websocket(event_handler)


def bot_event_handler(bot):
    bots = set([])

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                event = json.loads(args[0])

                if event.get("event") not in [
                    "posted",
                    "typing",
                    None,
                    "thread_updated",
                    "hello",
                    "status_change",
                    "user_added",
                    "post_detected",
                    "reaction_added",
                ]:
                    print(event)
                if (
                    event.get("event") == "posted"
                    and event["data"]["channel_type"] == "D"
                    and bot.user_id in event["data"]["channel_name"]
                ):  # Direct message
                    post = json.loads(event["data"]["post"])
                    message = ChatMessage(post["message"])
                    channel_id = post["channel_id"]
                    user_id = post["user_id"]
                    username = bot.driver.users.get_user(user_id=user_id)["username"]
                    if user_id == bot.user_id:
                        return
                elif event.get("event") == "posted":
                    post = json.loads(event["data"]["post"])
                    message = ChatMessage(post["message"])
                    user_id = post["user_id"]
                    channel_id = post["channel_id"]
                    user_info = bot.driver.users.get_user(user_id=user_id)
                    username = user_info["username"]
                    if user_info["id"] in bots:
                        return
                    if user_info.get("is_bot", False):
                        bots.add(user_info["id"])
                        return
                    is_recently_active = (dt.now() - bot.last_invoked).seconds < 600
                    if not is_recently_active and (
                        (bot.user_name).lower() not in message.text
                        or bot.name.lower() not in message.text.lower()
                    ):
                        return
                    if (
                        message.text == f"@{bot.user_name} reset"
                        or message.text == "reset"
                    ):
                        bot.reset(channel_id)
                        return
                    if message.text.startswith(f"@{bot.user_name} override-persona:"):
                        print("overridng")
                        bot.reset(channel_id)
                        bot.system_prompt = message.text.split(":")[1].strip()
                        return
                elif event.get("event") == "user_added":
                    user_info = bot.driver.users.get_user(
                        user_id=event["data"]["user_id"]
                    )
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

                # Look for attachments
                if "metadata" in post and "files" in post["metadata"]:
                    message.attachments = []
                    for file in post["metadata"]["files"]:
                        message.attachments.append(file)

                # Error handling
                try:
                    params = {
                        "user_id": bot.user_id,
                        "post_id": post["id"],
                        "emoji_name": "thinking_face",
                    }
                    bot.driver.reactions.create_reaction(options=params)
                    result = await func(message, bot, channel_id, username)
                    params["emoji_name"] = "white_check_mark"
                    bot.driver.reactions.create_reaction(options=params)
                except Exception as e:
                    print(f"Error handling event: {e}")
                    # Optionally re-raise the exception
                    raise
                return result
            except Exception as e:
                print(e)

        return wrapper

    return decorator
