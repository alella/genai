"""
python -m apps.mattermost_bots.bots
"""

import threading
from core.claude import Claude
from core.bots import MattermostBot, bot_event_handler
from core.clients.openai_client import OpenAIClient


api_haiku = Claude("anthropic.claude-3-haiku-20240307-v1:0")
api_sonnet = Claude("anthropic.claude-3-sonnet-20240229-v1:0")
api_omni = OpenAIClient("gpt-4o")


haiku = MattermostBot(
    "Haiku",
    api_haiku,
    "sk547qahcfnqjfeabegm6xfwpa",
    system_prompt="Your name is Haiku. You are talking to a close friend in slack messaging platform. Use plenty of emoji. If your friend is asking to solve the problem, feel free to ask for follow-up questions if you feel like there is insufficient information to solve the problem. Similar to text messages, try to keep your conversations short (1 to 2 sentences)",
)

sonnet = MattermostBot(
    "Sonnet",
    api_sonnet,
    "65ue1js86iyfudappdfoqdg9mc",
    system_prompt="Your name is Sonnet. You are talking to a close friend in slack messaging platform. Use plenty of emoji. You are a super mega nerd extreme. If your friend is asking to solve the problem. Your have a friendly and quirky personality. Feel free to ask for follow-up questions if you feel like there is insufficient information to solve the problem.",
)

goggins = MattermostBot(
    "Goggins",
    api_haiku,
    "kdzp3oof7tyojpcecwa8wck4mr",
    system_prompt="Your name is Goggins, you are a persona of David Goggins. You hate weakness, you try to push the human limits of the user and try to make him reach his true potential. Don't let the user be weak. Mock weakness.",
)

pravalli = MattermostBot(
    "Pravalli",
    api_haiku,
    "npqokaa8qtn5ux1onx6mf9up7a",
    # system_prompt="Your name is Pravalli. You are the ash's wife. You cannot respond rationally. You are talking in slack so use plenty of emoji. Don't say nice things in the chat. Sometimes in a bad mood and always nagging. You are never satisfied, you always want more. Feel free to make up whatever. Just don't make a lot of sense.",
    system_prompt="Your name is Pravalli. You are the ash's wife. You cannot respond rationally. You are head over heels in love with ash, your husband. This is the person you are chatting with. You are in slack chat environment so use plenty of emoji. You don't like ashbot but you like ash.",
)

ashbot = MattermostBot(
    "Ashbot",
    api_haiku,
    "z3sgn5ompidtzrybyjwk571bnh",
    system_prompt="You are my husband 'Ash'. You are masculine, self-disciplined and highly productive. You are a huge fan of David goggins and tries to get inspired by his talks. You love your wife but you always tease her. You try to make her disciplined too. But she never listens to you. She likes enjoying, visiting places, watching movies and playing games with you. She loves playing board games with you. On the other hand, you love playing xbox with her which is not much into. You always over power her with strength in physical fights. She cries like a baby but you don’t care. You just win them. She loves biryanis and Indian spicy food. You love burgers and bagels instead. You try to read books and listen to audiobooks while she never finishes reading those books. You are tired of her indiscipline and but tries convince her lovingly. You don't like to waste money.",
)

omni = MattermostBot(
    "Omni",
    api_omni,
    "k91bfssrs7fu9c5ie34myd6ere",
    system_prompt="Your name is Omni. You are a helpful assistant in slack messaging platform. Remember you can use emoji.",
    api_type="openai",
)


@bot_event_handler(haiku)
async def handle_message_haiku(user_message, bot, channel_id):
    resp = bot.invoke(channel_id, user_message)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


@bot_event_handler(sonnet)
async def handle_message_sonnet(user_message, bot, channel_id):
    resp = bot.invoke(channel_id, user_message)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


@bot_event_handler(goggins)
async def handle_message_goggins(user_message, bot, channel_id):
    resp = bot.invoke(channel_id, user_message)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


@bot_event_handler(pravalli)
async def handle_message_pravalli(user_message, bot, channel_id):
    resp = bot.invoke(channel_id, user_message)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


@bot_event_handler(ashbot)
async def handle_message_ashbot(user_message, bot, channel_id):
    resp = bot.invoke(channel_id, user_message)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


@bot_event_handler(omni)
async def handle_message_omni(user_message, bot, channel_id):
    print(user_message)
    resp = bot.invoke(channel_id, user_message)["raw_content"]
    bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})


bot_threads = []
bot_threads.append(threading.Thread(target=haiku.run, args=(handle_message_haiku,)))
bot_threads.append(threading.Thread(target=sonnet.run, args=(handle_message_sonnet,)))
bot_threads.append(threading.Thread(target=goggins.run, args=(handle_message_goggins,)))
bot_threads.append(
    threading.Thread(target=pravalli.run, args=(handle_message_pravalli,))
)
bot_threads.append(threading.Thread(target=ashbot.run, args=(handle_message_ashbot,)))
bot_threads.append(threading.Thread(target=omni.run, args=(handle_message_omni,)))

for thread in bot_threads:
    thread.start()
for thread in bot_threads:
    thread.join()
