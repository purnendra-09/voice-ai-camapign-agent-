import json
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape

from app.utils import get_logger

from .index import KnowledgeIndex
from .models import KnowledgeDocument, KnowledgeSelection
from .retriever import KnowledgeRetriever

logger = get_logger(__name__)


class KnowledgeContextBuilder:
    """Build structured, relevant knowledge context for each LLM turn."""

    def __init__(self, index: KnowledgeIndex):
        self.index = index
        self.retriever = KnowledgeRetriever(index)

    def build(
        self,
        patient_message: str,
        memory: Dict[str, Any],
        conversation_state: Optional[str],
        detected_intent: Optional[str],
        current_goal: Optional[str],
        model: Optional[str] = None,
    ) -> KnowledgeSelection:
        documents = self.retriever.retrieve(
            patient_message=patient_message,
            memory=memory,
            state=conversation_state,
            intent=detected_intent,
            goal=current_goal,
        )
        prompt_section = self._render(documents)
        selection = KnowledgeSelection(
            documents=documents,
            selected_files=[document.filename for document in documents],
            prompt_section=prompt_section,
            prompt_size=len(prompt_section),
        )
        logger.info(
            "Knowledge context selected",
            extra={
                "extra_data": {
                    "patient_intent": detected_intent,
                    "selected_knowledge_files": selection.selected_files,
                    "conversation_state": conversation_state,
                    "memory_summary": memory.get("conversation_summary"),
                    "prompt_size": selection.prompt_size,
                    "llm_model": model,
                }
            },
        )
        return selection

    def _render(self, documents: List[KnowledgeDocument]) -> str:
        rendered = []
        for document in documents:
            body = {
                "file": document.filename,
                "title": document.title,
                "tags": document.tags,
                "metadata": document.metadata,
                "sections": [
                    {
                        "heading": section.heading,
                        "content": self._truncate(section.content, 900),
                        "bullets": section.bullets[:8],
                        "examples": [self._truncate(example, 500) for example in section.examples[:2]],
                    }
                    for section in document.sections[:4]
                ],
            }
            rendered.append(json.dumps(body, ensure_ascii=True, separators=(",", ":")))
        return "<RelevantKnowledge>\n" + escape("\n".join(rendered)) + "\n</RelevantKnowledge>"

    def _truncate(self, text: str, limit: int) -> str:
        text = text or ""
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."
