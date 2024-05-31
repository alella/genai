import gradio as gr
from core.claude import Claude
from core.prompts import Prompt

api = Claude("anthropic.claude-3-haiku-20240307-v1:0")


def llm_response(prompt):
    prompt_obj = Prompt(prompt, "")
    return api.invoke(prompt_obj)["raw_content"]


with gr.Blocks() as demo:
    chatbot = gr.Chatbot()
    msg = gr.Textbox()
    clear = gr.ClearButton([msg, chatbot])

    def respond(message, chat_history):
        bot_message = llm_response(message)
        chat_history.append((message, bot_message))
        return "", chat_history

    msg.submit(respond, [msg, chatbot], [msg, chatbot])

demo.launch()
