import os
from core.document_types import MarqoDoc
from core.utils import hash_this
import PyPDF2
from typing import List
import math


class FileParserBase:
    def __init__(self, extensions=[".md"]):
        self.extensions = extensions

    def is_picked(self, file_path: str):
        if os.path.splitext(file_path)[1] in self.extensions:
            return True
        return False

    def parse(self, file_path: str) -> List[MarqoDoc]:
        raise NotImplementedError("parse method must be implemented in subclasses")


class SimpleTextParser(FileParserBase):
    def __init__(self, extensions=[".txt"]):
        super().__init__(extensions)

    def parse(self, file_path: str) -> List[MarqoDoc]:
        with open(file_path, "r") as f:
            raw_content = f.read()
        return [
            MarqoDoc(
                _id=hash_this(file_path),
                content=raw_content,
                filename=file_path,
            )
        ]


class SimplePDFParser(FileParserBase):
    def __init__(self, extensions=[".pdf"], max_page_count=100):
        super().__init__(extensions)
        self.max_page_count = max_page_count

    def parse(self, file_path: str) -> List[MarqoDoc]:
        with open(file_path, "rb") as pdf_file_obj:
            pdf_reader = PyPDF2.PdfReader(pdf_file_obj)
            num_pages = len(pdf_reader.pages)
            documents = []

            for i in range(math.ceil(num_pages / self.max_page_count)):
                print(i)
                start_page = i * self.max_page_count
                end_page = min((i + 1) * self.max_page_count, num_pages)
                text = ""
                for page in range(start_page, end_page):
                    page_obj = pdf_reader.pages[page]
                    text += page_obj.extract_text()

                documents.append(
                    MarqoDoc(
                        _id=f"{hash_this(file_path)}_{i}",
                        content=text,
                        filename=f"{file_path}_{i}",
                    )
                )

        return documents
