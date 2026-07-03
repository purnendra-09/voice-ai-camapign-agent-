import re
from collections import defaultdict
from typing import Dict, Iterable, List, Set

from .models import KnowledgeDocument


class KnowledgeIndex:
    """In-memory inverted index for cached markdown knowledge."""

    def __init__(self):
        self.documents: Dict[str, KnowledgeDocument] = {}
        self.tokens: Dict[str, Set[str]] = defaultdict(set)
        self.tags: Dict[str, Set[str]] = defaultdict(set)

    def build(self, documents: Iterable[KnowledgeDocument]) -> None:
        self.documents = {}
        self.tokens = defaultdict(set)
        self.tags = defaultdict(set)
        for document in documents:
            self.documents[document.filename] = document
            for token in self.tokenize(document.raw_text + " " + document.title):
                self.tokens[token].add(document.filename)
            for tag in document.tags:
                self.tags[tag.lower()].add(document.filename)

    def search(self, query: str, tags: Iterable[str], limit: int = 6) -> List[KnowledgeDocument]:
        scores = defaultdict(int)
        for token in self.tokenize(query):
            for filename in self.tokens.get(token, set()):
                scores[filename] += 2
        for tag in tags:
            for filename in self.tags.get(tag.lower(), set()):
                scores[filename] += 4
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return [self.documents[filename] for filename, _score in ranked[:limit]]

    def get(self, filename: str) -> KnowledgeDocument | None:
        return self.documents.get(filename)

    def all(self) -> List[KnowledgeDocument]:
        return list(self.documents.values())

    def token_count(self) -> int:
        return sum(len(document.sections) for document in self.documents.values())

    def tokenize(self, text: str) -> List[str]:
        return [
            token
            for token in re.split(r"[^a-zA-Z0-9]+", (text or "").lower())
            if len(token) > 2
        ]
