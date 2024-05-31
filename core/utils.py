from rich.logging import RichHandler
import logging
import hashlib
import re


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
