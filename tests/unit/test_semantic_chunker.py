"""Tests for the semantic chunker."""

import pytest
from knowledge.chunker.semantic_chunker import chunk_document, _extract_fault_codes


SAMPLE_DOC = """# Kinetic-Core Service Manual

## Chapter 1: Safety

All work requires LOTO before beginning.

## Chapter 2: Fault Codes

### KX-T2209-B — Thermal Escalation

When fault code KX-T2209-B is detected, follow procedure 5.1.

### KX-V1103-A — Vibration Escalation

When fault code KX-V1103-A is detected, follow procedure 5.2.

## Chapter 3: Repair Procedures

Detailed repair steps are in sections 5.1 and 5.2.
"""


def test_chunk_splits_by_headings():
    chunks = chunk_document(SAMPLE_DOC, "test_manual.md")
    assert len(chunks) >= 4  # At least one per section


def test_chunk_extracts_fault_codes():
    chunks = chunk_document(SAMPLE_DOC, "test_manual.md")
    fault_chunks = [c for c in chunks if c.fault_codes]
    assert len(fault_chunks) >= 1
    all_codes = {code for c in fault_chunks for code in c.fault_codes}
    assert "KX-T2209-B" in all_codes
    assert "KX-V1103-A" in all_codes


def test_chunk_has_required_fields():
    chunks = chunk_document(SAMPLE_DOC, "test.md")
    for chunk in chunks:
        assert chunk.id
        assert chunk.content
        assert chunk.source_document == "test.md"
        assert chunk.section
        assert chunk.token_estimate > 0


def test_extract_fault_codes_from_text():
    text = "Fault KX-T2209-B and also KX-V1103-A were found. Also KX-P3301-C."
    codes = _extract_fault_codes(text)
    assert set(codes) == {"KX-T2209-B", "KX-V1103-A", "KX-P3301-C"}


def test_empty_document_produces_one_chunk():
    chunks = chunk_document("Some content without headings.", "doc.md")
    assert len(chunks) == 1


def test_chunk_index_is_sequential():
    chunks = chunk_document(SAMPLE_DOC, "test.md")
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
