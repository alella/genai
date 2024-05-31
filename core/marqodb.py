import os
import marqo
import logging

from core.file_parsers import FileParserBase

logger = logging.getLogger(__name__)


class MarqoIndexer:
    def __init__(self, url="http://localhost:8882"):
        self.url = os.environ.get("MARQO_DB_URL", url)
        self.mq = marqo.Client(url=self.url)

    def index_directory(
        self,
        directory_path: str,
        index_name: str,
        parser: FileParserBase,
        overwrite_idx=False,
    ):
        if overwrite_idx:
            self.mq.delete_index(index_name)
        if not index_name in [x["indexName"] for x in self.mq.get_indexes()["results"]]:
            logger.info(f"Creating index {index_name} as it doesn't exist")
            self.mq.create_index(index_name)

        ctr = 0
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if ctr > 10:
                    break
                file_path = os.path.join(root, file)
                if parser.is_picked(file_path):
                    ctr += 1
                    logger.info(
                        f"Parsing file {file_path} with parser {parser.__class__.__name__}"
                    )
                    with open(file_path, "r") as f:
                        raw_content = f.read()
                    doc = parser.parse(file_path, raw_content)
                    self.mq.index(index_name).add_documents(
                        [doc.encode()], tensor_fields=["content"]
                    )
                else:
                    logger.info(f"Ignoring file {file_path}")


class MarqoSearcher:
    def __init__(self, url="http://localhost:8882"):
        self.url = os.environ.get("MARQO_DB_URL", url)
        self.mq = marqo.Client(url=self.url)

    def get_context(self, query, body, window_length):
        start_index = body.lower().find(query.lower())
        if start_index == -1:
            return query

        # Find the start and end indices of the context window
        start_word = max(0, start_index - window_length // 2)
        end_word = min(len(body) - 1, start_index + len(query) + window_length // 2)

        return body[start_word:end_word]

    def search(
        self, index_name, query, limit=8, score_threshold=0.8, result_window_length=500
    ):
        results = self.mq.index(index_name).search(q=query, limit=limit)
        results = [t for t in results["hits"] if t["_score"] > score_threshold]
        results = [
            self.get_context(
                t["_highlights"][0]["content"], t["content"], result_window_length
            )
            for t in results
        ]
        return results
