import emoji
import json
import os
from time import sleep
import re
from core.utils import setup_logging, hash_this
import markdown
from datetime import datetime as dt
from datetime import date as d
from core.marqodb import MarqoIndexer
from core.document_types import MarqoDoc
from core.file_parsers import FileParserBase

logger = setup_logging()


class JournalsParser(FileParserBase):
    def __init__(self, extensions=[".md"]):
        self.extensions = extensions

    def is_picked(self, file_path: str) -> bool:
        if not super().is_picked(file_path):
            return False
        md = markdown.Markdown(extensions=["full_yaml_metadata"])
        with open(file_path) as f:
            md.convert(f.read())
        if not md.Meta or not md:
            return False
        tags = md.Meta.get("tags", []) or []
        if not tags:
            return False
        if not ("journal" in tags or "routine" in tags or "problem" in tags):
            return False
        return True

    def parse(self, file_path: str, raw_content: str) -> MarqoDoc:
        md = markdown.Markdown(extensions=["full_yaml_metadata"])
        raw_content = md.convert(raw_content)
        return MarqoDoc(
            content=raw_content,
            _id=hash_this(file_path),
            filename=file_path,
        )


ingestion_path = "core/journaldocs"
idxr = MarqoIndexer()
idxr.index_directory(ingestion_path, "journal", JournalsParser(), overwrite_idx=False)
