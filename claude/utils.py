from rich.logging import RichHandler
from rich.console import Console
import logging


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
