import os
from core.document_types import MarqoDoc
from core.utils import hash_this


class FileParserBase:
    def __init__(self, extensions=[".md"]):
        self.extensions = extensions

    def is_picked(self, file_path: str):
        if os.path.splitext(file_path)[1] in self.extensions:
            return True
        return False

    def parse(self, file_path: str, raw_content: str) -> MarqoDoc:
        raise NotImplementedError("parse method must be implemented in subclasses")


class SimpleTextParser(FileParserBase):
    def __init__(self, extensions=[".txt"]):
        super().__init__(extensions)

    def parse(self, file_path: str, raw_content: str) -> MarqoDoc:
        return MarqoDoc(
            _id=hash_this(file_path),
            content=raw_content,
            filename=file_path,
        )
