import json
import inspect
from functools import wraps


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

    def __str__(self):
        return f"🤖 System Prompt: {self.get_system_prompt()}\n\n👤 User Prompt: {self.get_user_prompt()}\n\n✨ Kwargs: {self._kwargs}"


class ToolPrompt(Prompt):
    def __init__(self, user_prompt_template):
        super().__init__(
            user_prompt_template,
            system_prompt_template=f"""In this environment you have access to a set of tools you can use to answer the user's question.
    If you wish to use the tool your response should start and end with xml tool_invoke tag and nothing else. 
    Only invoke one function at a time and wait for the results before invoking another function:
    <tool_invoke>
    <tool_name>$TOOL_NAME</tool_name>
    <parameters>
    <$PARAMETER_NAME>$PARAMETER_VALUE</$PARAMETER_NAME>
    ...
    </parameters>
    </tool_invoke>

    If you cannot respond back using the tools just mention that you can't provide the answer using the available tools. 
    Do not make up answers.

    <tools>
    {"\n".join([x['description'] for x in LLMFNS])}
    </tools>
    """,
        )
        self.resultPrompt = Prompt(
            f"User: {user_prompt_template}\n\nYou:{{tool_invoke}} \n\nTool: {{tool_response}}\n\n You: ",
            system_prompt_template=f"Complete the conversation using the response from Tool's <output> xml tag, If you see any error response from the tool, let the user know that you cannot figure out the answer.",
        )

    def invoke(self, api, tokens=1024):
        result = api.invoke(self, tokens=tokens)
        if "tool_invoke" in result["parsed_objects"]:
            result["tool_invocation"] = result["raw_content"]
            tool_name = result["parsed_objects"]["tool_invoke"]["tool_name"]
            params = result["parsed_objects"]["tool_invoke"]["parameters"]
            result["invocation"] = {
                "tool_name": tool_name,
                "params": params,
                "result": None,
            }
            for tool in LLMFNS:
                if tool["tool_name"] == tool_name:
                    tool_function = tool["function"]
                    tool_result = tool_function(**params)
                    result["invocation"]["result"] = tool_result
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


# Global variable to store function descriptions
LLMFNS = []


def llm_tool(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get the function signature
        signature = inspect.signature(func)
        bound_arguments = signature.bind(*args, **kwargs)
        bound_arguments.apply_defaults()

        # Type cast the arguments
        for name, value in bound_arguments.arguments.items():
            param_type = signature.parameters[name].annotation
            if param_type != inspect.Parameter.empty:
                bound_arguments.arguments[name] = param_type(value)

        try:
            # Call the function with type-cast arguments
            func_output = func(*bound_arguments.args, **bound_arguments.kwargs)
            func_error = ""
        except Exception as e:
            func_error = str(e)
            func_output = ""
        return f"""
        <tool_output>
        <tool_name>{func.__name__}</tool_name>
        <output>{str(func_output)}</output>
        <error>{func_error}</error>
        </tool_output>
        """

    # Extract function metadata
    func_name = func.__name__
    docstring = func.__doc__.strip() if func.__doc__ else func.__name__

    # Extract parameter information
    signature = inspect.signature(func)
    parameters = signature.parameters

    # Construct XML description
    xml_description = f"<tool><description>{docstring}</description>"
    xml_description += f"<tool_name>{func_name}</tool_name><parameters>"

    for param_name, param in parameters.items():
        param_type = param.annotation if param.annotation != param.empty else "unknown"
        xml_description += f"<parameter><variable_name>{param_name}</variable_name><type>{param_type}</type></parameter>"

    xml_description += "</parameters></tool>"

    # Store the description in the global LLMFNS variable
    LLMFNS.append(
        {
            "function": wrapper,
            "description": xml_description,
            "tool_name": func.__name__,
        }
    )

    return wrapper
