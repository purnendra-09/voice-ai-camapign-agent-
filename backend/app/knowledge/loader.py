from pathlib import Path
from typing import List

from app.utils import get_logger

from .index import KnowledgeIndex
from .models import KnowledgeDocument
from .parser import MarkdownKnowledgeParser
from .tagger import KnowledgeTagger

logger = get_logger(__name__)


class KnowledgeLoader:
    """Load and cache markdown knowledge documents from disk."""

    def __init__(self, knowledge_path: Path):
        self.knowledge_path = Path(knowledge_path)
        self.parser = MarkdownKnowledgeParser()
        self.tagger = KnowledgeTagger()
        self.index = KnowledgeIndex()
        self._last_signature = None

    def load(self) -> KnowledgeIndex:
        documents = []
        for path in sorted(self.knowledge_path.glob("*.md")):
            raw_text = path.read_text(encoding="utf-8")
            if not raw_text.strip():
                logger.warning(f"Skipping empty knowledge file: {path.name}")
                continue
            tags = self.tagger.tags_for(path, raw_text)
            documents.append(
                self.parser.parse(
                    path=path,
                    raw_text=raw_text,
                    tags=tags,
                    modified_at=path.stat().st_mtime,
                )
            )
        self._validate(documents)
        self.index.build(documents)
        self._last_signature = self._signature()
        logger.info(
            "Knowledge base loaded",
            extra={
                "extra_data": {
                    "loaded_files": [document.filename for document in documents],
                    "document_count": len(documents),
                    "section_count": sum(len(document.sections) for document in documents),
                }
            },
        )
        return self.index

    def reload_if_changed(self) -> KnowledgeIndex:
        if self._last_signature != self._signature():
            return self.load()
        return self.index

    def _signature(self) -> List[tuple[str, float, int]]:
        return [
            (path.name, path.stat().st_mtime, path.stat().st_size)
            for path in sorted(self.knowledge_path.glob("*.md"))
        ]

    def _validate(self, documents: List[KnowledgeDocument]) -> None:
        if not documents:
            raise ValueError(f"No markdown knowledge files found in {self.knowledge_path}")
        missing_titles = [document.filename for document in documents if not document.title]
        if missing_titles:
            raise ValueError(f"Knowledge files missing titles: {missing_titles}")
