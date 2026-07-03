import re
from pathlib import Path
from typing import Dict, List

from .models import KnowledgeDocument, KnowledgeSection


class MarkdownKnowledgeParser:
    """Parse markdown files into lightweight structured knowledge documents."""

    def parse(self, path: Path, raw_text: str, tags: List[str], modified_at: float) -> KnowledgeDocument:
        lines = raw_text.splitlines()
        title = self._title(lines, path.stem)
        sections = self._sections(lines, title)
        bullets = self._bullets(lines)
        examples = self._examples(lines)
        metadata = self._metadata(lines)
        return KnowledgeDocument(
            filename=path.name,
            title=title,
            raw_text=raw_text.strip(),
            sections=sections,
            bullets=bullets,
            examples=examples,
            metadata=metadata,
            tags=tags,
            path=path,
            modified_at=modified_at,
        )

    def _title(self, lines: List[str], fallback: str) -> str:
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return fallback.replace("_", " ").title()

    def _sections(self, lines: List[str], title: str) -> List[KnowledgeSection]:
        sections = []
        current_heading = title
        current_lines = []
        for line in lines:
            heading = re.match(r"^(#{1,3})\s+(.+)$", line)
            if heading:
                if current_lines:
                    sections.append(self._make_section(current_heading, current_lines))
                current_heading = heading.group(2).strip()
                current_lines = []
            else:
                current_lines.append(line)
        if current_lines:
            sections.append(self._make_section(current_heading, current_lines))
        return [section for section in sections if section.content or section.bullets or section.examples]

    def _make_section(self, heading: str, lines: List[str]) -> KnowledgeSection:
        content = "\n".join(line for line in lines if line.strip()).strip()
        return KnowledgeSection(
            heading=heading,
            content=content,
            bullets=self._bullets(lines),
            examples=self._examples(lines),
        )

    def _bullets(self, lines: List[str]) -> List[str]:
        bullets = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("- ", "* ", "-   ", "*   ")):
                bullets.append(stripped.lstrip("-* ").strip())
        return bullets

    def _examples(self, lines: List[str]) -> List[str]:
        examples = []
        capture = False
        buffer = []
        for line in lines:
            if re.match(r"^#{1,3}\s+(Examples|Good|Bad)", line, re.IGNORECASE):
                capture = True
            if capture:
                buffer.append(line)
        if buffer:
            examples.append("\n".join(buffer).strip())
        return examples

    def _metadata(self, lines: List[str]) -> Dict[str, str]:
        metadata = {}
        for line in lines:
            match = re.match(r"^([A-Za-z][A-Za-z ]+):\s+(.+)$", line.strip())
            if match:
                metadata[match.group(1).strip().lower().replace(" ", "_")] = match.group(2).strip()
        return metadata
