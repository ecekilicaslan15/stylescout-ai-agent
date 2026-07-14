from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

STOP_WORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "for",
    "in",
    "on",
    "to",
    "of",
    "what",
    "which",
    "should",
    "i",
    "use",
    "be",
    "my",
    "me",
    "do",
    "does",
    "can",
    "with",
    "and",
    "or",
    "at",
    "it",
    "this",
    "that",
    "about",
}

SYNONYMS: dict[str, list[str]] = {
    "hot": ["warm", "summer", "heat", "humid"],
    "warm": ["hot", "summer"],
    "summer": ["warm", "hot"],
    "airy": ["breathable", "lightweight"],
    "breathable": ["airy", "lightweight"],
    "cold": ["winter", "cool"],
    "winter": ["cold", "cool"],
    "cool": ["cold", "winter"],
    "material": ["fabric"],
    "fabric": ["material", "textile"],
    "textile": ["fabric", "material"],
    "coat": ["outerwear", "jacket"],
    "care": ["wash", "cleaning", "delicate"],
    "delicate": ["care", "hand", "silk"],
}


@dataclass(frozen=True)
class RetrievedChunk:
    """A scored knowledge chunk returned by keyword retrieval."""

    content: str
    source: str
    heading: str
    score: float


@dataclass
class _KnowledgeChunk:
    content: str
    source: str
    heading: str


class RagService:
    """Keyword-based retrieval over local Markdown fashion knowledge files."""

    def __init__(self, knowledge_dir: str | Path) -> None:
        self.knowledge_dir = Path(knowledge_dir)
        self._chunks: list[_KnowledgeChunk] = self._load_chunks()

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 1.0) -> list[RetrievedChunk]:
        """Return the top-k most relevant chunks for a normalized query."""
        query_tokens = self._expand_query_tokens(query)
        if not query_tokens or not self._chunks:
            return []

        scored_chunks: list[RetrievedChunk] = []
        for chunk in self._chunks:
            score = self._score_chunk(query_tokens, chunk)
            if score >= min_score:
                scored_chunks.append(
                    RetrievedChunk(
                        content=chunk.content,
                        source=chunk.source,
                        heading=chunk.heading,
                        score=score,
                    )
                )

        scored_chunks.sort(key=lambda item: item.score, reverse=True)
        return scored_chunks[:top_k]

    def _load_chunks(self) -> list[_KnowledgeChunk]:
        """Load and chunk all Markdown files from the knowledge directory."""
        if not self.knowledge_dir.exists() or not self.knowledge_dir.is_dir():
            return []

        chunks: list[_KnowledgeChunk] = []
        for markdown_path in sorted(self.knowledge_dir.glob("*.md")):
            try:
                text = markdown_path.read_text(encoding="utf-8")
            except OSError:
                continue
            chunks.extend(self._split_markdown(text, markdown_path.name))
        return chunks

    def _split_markdown(self, text: str, source: str) -> list[_KnowledgeChunk]:
        """Split a Markdown document into heading-based chunks."""
        chunks: list[_KnowledgeChunk] = []
        current_heading = "Introduction"
        current_lines: list[str] = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                if current_lines:
                    current_lines.append("")
                continue

            if line.startswith("#"):
                if current_lines:
                    chunks.append(
                        _KnowledgeChunk(
                            content="\n".join(current_lines).strip(),
                            source=source,
                            heading=current_heading,
                        )
                    )
                    current_lines = []

                current_heading = line.lstrip("#").strip() or "Untitled"
                continue

            current_lines.append(line)

        if current_lines:
            chunks.append(
                _KnowledgeChunk(
                    content="\n".join(current_lines).strip(),
                    source=source,
                    heading=current_heading,
                )
            )

        return [chunk for chunk in chunks if chunk.content]

    def _normalize_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _tokenize(self, text: str) -> list[str]:
        return [
            token
            for token in self._normalize_text(text).split()
            if token and token not in STOP_WORDS
        ]

    def _expand_query_tokens(self, query: str) -> set[str]:
        """Normalize the query and expand it with simple fashion synonyms."""
        tokens = self._tokenize(query)
        expanded = set(tokens)

        for token in tokens:
            for synonym in SYNONYMS.get(token, []):
                expanded.add(synonym)

        return expanded

    def _score_chunk(self, query_tokens: set[str], chunk: _KnowledgeChunk) -> float:
        """Score a chunk using deterministic keyword overlap."""
        heading_tokens = set(self._tokenize(chunk.heading))
        content_tokens = set(self._tokenize(chunk.content))
        chunk_tokens = heading_tokens | content_tokens

        overlap = query_tokens & chunk_tokens
        if not overlap:
            return 0.0

        score = float(len(overlap))
        score += float(len(query_tokens & heading_tokens)) * 1.5
        return score
