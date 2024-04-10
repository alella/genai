import emoji
import json
import marqo
import os
from time import sleep
import hashlib
import re
from utils import setup_logging
import markdown
from datetime import datetime as dt
from datetime import date as d


def hash(input_str):
    hash_value = hashlib.sha256(input_str.encode()).hexdigest()
    return "".join(re.findall(r"[a-zA-Z0-9]", hash_value))[:20]


logger = setup_logging()
mq = marqo.Client(url="http://localhost:8882")
md = markdown.Markdown(extensions=["full_yaml_metadata"])
# try:
#     mq.delete_index("journal")
#     sleep(30)
#     mq.create_index("journal")
# except Exception as e:
#     logger.error(e)
#     logger.info("Index already exists")

files = os.listdir("journaldocs")
files = sorted(files)
for file in files:
    logger.info(f"Processing file {file}...")
    if file.endswith(".md"):
        # read the file
        with open(f"journaldocs/{file}", "r") as f:
            content = f.read()
        md.convert(content)
        # filter
        if not md.Meta or not md:
            continue
        tags = md.Meta.get("tags", []) or []
        date = md.Meta.get("date", "unknown") or "unknown"
        if type(date) == type(d.fromisoformat("2019-12-04")):
            date = date.strftime("%Y-%m-%d")
        if not tags:
            continue
        if not ("journal" in tags or "routine" in tags or "problem" in tags):
            logger.info(f"Skipping file {file}...")
            continue
        # create a document
        document = {
            "Title": file[:-3],
            "Content": content[:90000],
            "_id": hash(file),
            "filename": file,
            "date": date,
        }

        try:
            resp = mq.index("journal").add_documents(
                [document], tensor_fields=["Content"]
            )
            if resp["errors"]:
                logger.error(f"Response: {resp}")
        except Exception as e:
            logger.error(f"Document")
            logger.error(json.dumps(document, indent=2, ensure_ascii=False))
            logger.error(e)
