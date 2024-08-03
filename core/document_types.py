from dataclasses import dataclass


@dataclass
class MarqoDoc:
    content: str
    _id: str
    filename: str

    def encode(self):
        return {
            "content": self.content,
            "_id": self._id,
        }


@dataclass
class MarqoSnippet:
    content: str
    _id: str
    user: str

    def encode(self):
        return {
            "content": self.content,
            "_id": self._id,
            "user": self.user,
        }
