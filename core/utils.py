from rich.logging import RichHandler
import logging
import hashlib
import re
import xml.etree.ElementTree as ET


def setup_logging():
    # Set up the logger
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s][%(asctime)s][%(module)s|%(funcName)s] %(message)s",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                show_time=True,
                show_level=True,
                show_path=True,
            ),
        ],
    )

    return logging.getLogger(__name__)


def hash_this(input_str):
    hash_value = hashlib.sha256(input_str.encode()).hexdigest()
    return "".join(re.findall(r"[a-zA-Z0-9]", hash_value))[:20]


def xml_to_json(input_str):
    def _xml_to_dict(element):
        if len(element) == 0:  # if the element has no children
            return element.text
        d = {}
        for child in element:
            if child.tag not in d:
                d[child.tag] = _xml_to_dict(child)
            else:
                if isinstance(d[child.tag], list):
                    d[child.tag].append(_xml_to_dict(child))
                else:
                    d[child.tag] = [d[child.tag]] + [_xml_to_dict(child)]
        return d

    data = {
        tag: text.strip()
        for tag, text in re.findall(r"<(\w+)>(.*?)<\/\1>", input_str, re.DOTALL)
    }
    if "tool_invoke" in data:
        root = ET.fromstring("<x>" + data["tool_invoke"] + "</x>")
        data["tool_invoke"] = _xml_to_dict(root)
        if isinstance(data["tool_invoke"]["invoke"], list):
            data["tool_invoke"] = data["tool_invoke"]["invoke"]
        if isinstance(data["tool_invoke"], dict):
            data["tool_invoke"] = [data["tool_invoke"]["invoke"]]

    if "dag" in data:
        root = ET.fromstring("<x>" + data["dag"] + "</x>")
        children = _xml_to_dict(root)["node"]
        for child in children:
            if "children" in child:
                child["children"] = [x.strip() for x in child["children"].split(",")]
            if "previous" in child and child["previous"] == "None":
                child["previous"] = []
            if "previous" in child and isinstance(child["previous"], str):
                child["previous"] = [x.strip() for x in child["previous"].split(",")]
        data["dag"] = children

    return data
