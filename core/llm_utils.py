import inspect
from functools import wraps
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChatMessage:
    text: str
    attachments: list = field(default_factory=list)
    type: Optional[str] = ""


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
