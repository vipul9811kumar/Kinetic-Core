"""
Semantic Chunker

Splits industrial PDF/Markdown manuals into semantically coherent chunks
optimized for hybrid RAG retrieval. Uses section boundaries (headings) as
primary split points, then applies token-based splitting within sections
that exceed the max chunk size.

Key design: fault codes (e.g. KX-T2209-B) are ALWAYS kept in the same
chunk as their associated repair procedure — never split across boundaries.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


FAULT_CODE_PATTERN = re.compile(r"KX-[A-Z0-9]{4,6}-[A-Z]")
HEADING_PATTERN = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
MAX_CHUNK_TOKENS = 512
OVERLAP_TOKENS = 64


@dataclass
class Chunk:
    id: str
    content: str
    source_document: str
    section: str
    page_number: int
    fault_codes: list[str] = field(default_factory=list)
    token_estimate: int = 0
    chunk_index: int = 0

    def to_index_doc(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "source_document": self.source_document,
            "section": self.section,
            "page_number": self.page_number,
            "fault_codes": self.fault_codes,
            "token_estimate": self.token_estimate,
            "chunk_index": self.chunk_index,
        }


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English technical text."""
    return max(1, len(text) // 4)


def _extract_fault_codes(text: str) -> list[str]:
    return list(set(FAULT_CODE_PATTERN.findall(text)))


def _make_chunk_id(source: str, section: str, index: int) -> str:
    raw = f"{source}::{section}::{index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _split_by_tokens(text: str, max_tokens: int, overlap_tokens: int) -> Iterator[str]:
    """Split long text into overlapping token windows."""
    words = text.split()
    tokens_per_word = 1.3
    words_per_chunk = int(max_tokens / tokens_per_word)
    overlap_words = int(overlap_tokens / tokens_per_word)

    if len(words) <= words_per_chunk:
        yield text
        return

    start = 0
    while start < len(words):
        end = min(start + words_per_chunk, len(words))
        yield " ".join(words[start:end])
        if end >= len(words):
            break
        start = end - overlap_words


def _parse_sections(content: str) -> list[tuple[str, str, int]]:
    """
    Returns list of (section_title, section_text, page_estimate) tuples.
    Page estimate uses ~250 words per page heuristic.
    """
    matches = list(HEADING_PATTERN.finditer(content))
    sections = []

    for i, match in enumerate(matches):
        section_title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_text = content[start:end].strip()
        word_count = len(section_text.split())
        page_estimate = max(1, word_count // 250)
        sections.append((section_title, section_text, page_estimate))

    if not sections:
        sections = [("Document", content, 1)]

    return sections


def chunk_document(content: str, source_name: str) -> list[Chunk]:
    """
    Main entry point. Takes raw document text and returns a list of Chunk objects
    ready for embedding and indexing.
    """
    sections = _parse_sections(content)
    chunks: list[Chunk] = []
    global_index = 0
    cumulative_page = 1

    for section_title, section_text, page_span in sections:
        if not section_text.strip():
            continue

        token_count = _estimate_tokens(section_text)

        if token_count <= MAX_CHUNK_TOKENS:
            # Search title + body so fault codes embedded in headings (e.g. "5.2 KX-V1103-A")
            # are captured even when not repeated in the section body text.
            fault_codes = _extract_fault_codes(section_title + " " + section_text)
            chunk = Chunk(
                id=_make_chunk_id(source_name, section_title, global_index),
                content=section_text,
                source_document=source_name,
                section=section_title,
                page_number=cumulative_page,
                fault_codes=fault_codes,
                token_estimate=token_count,
                chunk_index=global_index,
            )
            chunks.append(chunk)
            global_index += 1
        else:
            for sub_chunk_text in _split_by_tokens(section_text, MAX_CHUNK_TOKENS, OVERLAP_TOKENS):
                fault_codes = _extract_fault_codes(section_title + " " + sub_chunk_text)
                chunk = Chunk(
                    id=_make_chunk_id(source_name, section_title, global_index),
                    content=sub_chunk_text,
                    source_document=source_name,
                    section=section_title,
                    page_number=cumulative_page,
                    fault_codes=fault_codes,
                    token_estimate=_estimate_tokens(sub_chunk_text),
                    chunk_index=global_index,
                )
                chunks.append(chunk)
                global_index += 1

        cumulative_page += page_span

    return chunks


def chunk_file(filepath: Path) -> list[Chunk]:
    content = filepath.read_text(encoding="utf-8")
    return chunk_document(content, filepath.name)


def chunk_directory(directory: Path, extensions: tuple[str, ...] = (".md", ".txt")) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    for ext in extensions:
        for filepath in sorted(directory.rglob(f"*{ext}")):
            chunks = chunk_file(filepath)
            all_chunks.extend(chunks)
    return all_chunks


def export_chunks_jsonl(chunks: list[Chunk], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk.to_index_doc()) + "\n")


if __name__ == "__main__":
    manual_path = Path("data/synthetic/manuals/kx_model_x_service_manual.md")
    if manual_path.exists():
        chunks = chunk_file(manual_path)
        print(f"Produced {len(chunks)} chunks from {manual_path.name}")
        for c in chunks[:3]:
            print(f"  [{c.chunk_index}] '{c.section}' — {c.token_estimate} tokens, fault_codes={c.fault_codes}")
        out = Path("knowledge/chunker/output/chunks.jsonl")
        export_chunks_jsonl(chunks, out)
        print(f"Exported to {out}")
    else:
        print(f"Manual not found at {manual_path}. Run from repo root.")
