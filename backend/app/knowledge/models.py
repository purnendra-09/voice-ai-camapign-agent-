from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class KnowledgeSection:
    heading: str
    content: str
    bullets: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


@dataclass
class KnowledgeDocument:
    filename: str
    title: str
    raw_text: str
    sections: List[KnowledgeSection]
    bullets: List[str]
    examples: List[str]
    metadata: Dict[str, str]
    tags: List[str]
    path: Path
    modified_at: float


@dataclass
class KnowledgeSelection:
    documents: List[KnowledgeDocument]
    selected_files: List[str]
    prompt_section: str
    prompt_size: int
