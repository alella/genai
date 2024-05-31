import json
from core.llm_utils import LLMFNS


class Messages:

    def __init__(self, max_count=20):
        self._messages = []
        self.max_count = max_count

    def push(self, role, text, name=""):
        self._messages.append({"role": role, "text": text})
        if name:
            self._messages[-1]["name"] = name
        if len(self._messages) > self.max_count:
            self._messages = self._messages[1:]
            if self._messages and self._messages[0]["role"] == "assistant":
                self._messages = self._messages[1:]

    def get_claude_messsages(self, user="", count=20):
        messages = []
        for msg in self._messages:
            if user and msg.get("name") not in [user, "assistant"]:
                continue
            messages.append(
                {
                    "role": msg["role"],
                    "content": [{"type": "text", "text": msg["text"]}],
                }
            )
            if len(messages) >= count:
                break
        return messages

    def get_openai_messages(self):
        messages = []
        for msg in self._messages:
            messages.append({"role": msg["role"], "content": msg["text"]})
        return messages

    def get_messages(self, count=20):
        messages = ""
        for msg in self._messages[-count:]:
            messages += f"{msg['name']}: {msg['text']}\n"
        return messages


class Prompt:
    def __init__(self, user_prompt_template, system_prompt_template=""):
        self.system_prompt_template = system_prompt_template
        self.user_prompt_template = user_prompt_template
        self._kwargs = {}

    def set_kwargs(self, **kwargs):
        self._kwargs = kwargs

    def get_system_prompt(self):
        if self._kwargs:
            return self.system_prompt_template.format(**self._kwargs)
        else:
            return self.system_prompt_template

    def get_user_prompt(self):
        if self._kwargs:
            return self.user_prompt_template.format(**self._kwargs)
        else:
            return self.user_prompt_template

    def invoke(self, api, tokens=1024):
        return api.invoke(self, tokens=tokens)

    def __str__(self):
        return f"🤖 System Prompt: {self.get_system_prompt()}\n\n👤 User Prompt: {self.get_user_prompt()}\n\n✨ Kwargs: {self._kwargs}"


class ToolPrompt(Prompt):
    def __init__(self, user_prompt_template, system_prompt_template=""):
        if not system_prompt_template:
            system_prompt_template = f"""In this environment you have access to a set of tools you can use to answer the user's question.
                You will be able to answer the user's question in the next step.
                If you wish to use the tool, your response should start and end with xml tool_invoke tag and nothing else. 
                Never invoke more than 3 tools at a time.

                The tool_invoke tag should look like this:
                <tool_invoke>
                <invoke>
                <tool_name>$TOOL_NAME</tool_name>
                <parameters>
                <$PARAMETER_NAME>$PARAMETER_VALUE</$PARAMETER_NAME>
                ...
                </parameters>
                </invoke>
                <invoke>
                ...
                </invoke>
                </tool_invoke>

                If you cannot respond back using the tools just mention that you can't provide the answer using the available tools. 
                Do not make up answers.

                <tools>
                {"\n".join([x['description'] for x in LLMFNS])}
                </tools>
                """

        super().__init__(
            user_prompt_template, system_prompt_template=system_prompt_template
        )
        self.resultPrompt = Prompt(
            f"User: {user_prompt_template}\n\nAssistant:{{tool_invoke}} \n\nTool: {{tool_response}}\n\n Assistant: ",
            system_prompt_template="Complete the conversation using the response from Tool's <output> xml tag, If you see any error response from the tool, let the user know that you cannot figure out the answer.",
        )

    def invoke(self, api, tokens=1024):
        result = api.invoke(self, tokens=tokens)
        if "tool_invoke" in result["parsed_objects"]:
            result["intermediate_response"] = result["raw_content"]

            tools_to_invoke = result["parsed_objects"]["tool_invoke"]
            result["invocation_results"] = {}
            for tool in tools_to_invoke:
                tool_name = tool["tool_name"]
                params = tool["parameters"]
                result["invocation_results"][tool_name] = {
                    "tool_name": tool_name,
                    "params": params,
                    "result": None,
                }
            for tool in LLMFNS:
                if tool["tool_name"] == tool_name:
                    tool_function = tool["function"]
                    tool_result = tool_function(**params)
                    result["invocation_results"][tool_name]["result"] = tool_result
                    self.resultPrompt.set_kwargs(
                        tool_response=tool_result,
                        tool_invoke=json.dumps(result["parsed_objects"]),
                    )
                    t_result = api.invoke(self.resultPrompt, tokens=tokens)
                    t_result["cost"] += result["cost"]
                    result["parsed_objects"].update(t_result["parsed_objects"])
                    result["raw_content"] = t_result["raw_content"]
                    break
        return result
