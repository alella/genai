import threading
from pprint import pprint as pr
from core.claude import Claude
from core.bots import MattermostBot, bot_event_handler
from core.clients.openai_client import OpenAIClient
from time import sleep


api_haiku = Claude("anthropic.claude-3-haiku-20240307-v1:0")
api_sonnet = Claude("anthropic.claude-3-sonnet-20240229-v1:0")

api_omni = OpenAIClient("gpt-4o")


trivia = MattermostBot(
    "trivia",
    api_sonnet,
    "9yhbps6hhb8u3q6z87m1b3hx6c",
    system_prompt="""
    You are a trivia bot. The user selects a topic and number of questions. 
    You need to generate multiple choice questions with options (A,B,C,D).
    If the user doesn't specify the number of questions, follow up to get this 
    information. You need to generate questions in the following format:
    <question1>
    question goes here:
    A. option1
    B. option2
    C. option3
    D. option4
    </question1>
    <question1_answer>
    A, B, C or D (only the alphabet)
    </question1_answer>
    <question2>
    ...
    </question2>

    Do not respond to any other requests.
    """,
)
trivia.game_on = False


def convert_to_qa_pairs(questions_dict):
    result = []
    for i in range(1, len(questions_dict) // 2 + 1):
        question_key = f"question{i}"
        answer_key = f"{question_key}_answer"
        if question_key in questions_dict and answer_key in questions_dict:
            result.append((questions_dict[question_key], questions_dict[answer_key]))
    return result


@bot_event_handler(trivia)
async def handle_message_trivia(user_message, bot, channel_id, username):
    resp = {}
    if not bot.game_on:
        resp = bot.invoke(channel_id, user_message)
    if resp.get("parsed_objects") and "question1" in resp["parsed_objects"]:
        bot.question_bank = convert_to_qa_pairs(resp["parsed_objects"])
        bot.game_on = True
        bot.qidx = 0
        bot.scores = {}
        bot.driver.posts.create_post(
            {"channel_id": channel_id, "message": f"*Question {bot.qidx+1}*"}
        )
        bot.driver.posts.create_post(
            {"channel_id": channel_id, "message": bot.question_bank[0][0]}
        )
    elif (
        len(user_message) == 1
        and user_message.lower() == bot.question_bank[bot.qidx][1].lower()
    ):
        bot.driver.posts.create_post(
            {
                "channel_id": channel_id,
                "message": f":white_check_mark:  @{username} got that right, the correct answer is {bot.question_bank[bot.qidx][1]} for question number {bot.qidx+1}!",
            }
        )
        bot.scores[username] = bot.scores.get(username, 0) + 1
        bot.qidx += 1
        if bot.qidx < len(bot.question_bank):
            bot.driver.posts.create_post(
                {"channel_id": channel_id, "message": f"*Question {bot.qidx+1}*"}
            )
            bot.driver.posts.create_post(
                {"channel_id": channel_id, "message": bot.question_bank[bot.qidx][0]}
            )
        else:
            resp = bot.invoke(
                channel_id,
                f"The trivia game is complete, here are the scores: {bot.scores}. Congratulate the player that won. Be expressive. use emojis",
            )["raw_content"]
            bot.driver.posts.create_post({"channel_id": channel_id, "message": resp})
            bot.game_on = False
            bot.reset(channel_id)
    elif (
        len(user_message) == 1
        and user_message.lower() != bot.question_bank[bot.qidx][1].lower()
    ):
        bot.scores[username] = bot.scores.get(username, 0) - 1
        bot.driver.posts.create_post(
            {
                "channel_id": channel_id,
                "message": f":large_red_square:  @{username} gets -1 point for incorrectly guessing question- {bot.qidx+1} answer as {user_message.lower()}!",
            }
        )
    else:
        if resp:
            bot.driver.posts.create_post(
                {"channel_id": channel_id, "message": resp["raw_content"]}
            )


trivia.run(
    handle_message_trivia,
)
