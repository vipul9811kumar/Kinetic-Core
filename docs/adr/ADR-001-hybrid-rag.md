# ADR-001: Hybrid RAG over Pure Vector Search

**Date:** 2025-01-15  
**Status:** Accepted  
**Deciders:** Architecture Team

## Context

The Technical Librarian agent needs to retrieve repair procedures from industrial PDFs. These manuals contain both semantic prose ("if the unit exhibits thermal instability...") and exact alphanumeric fault codes ("KX-T2209-B"). Pure vector search loses on exact code matching; pure BM25 loses on semantic context.

## Decision

Use **Hybrid RAG** — Reciprocal Rank Fusion (RRF) of BM25 lexical scores and Ada-002 vector similarity scores — via Azure AI Search's built-in hybrid retrieval.

## Consequences

- **Positive:** Recall improves ~23% on our fault-code test set vs. pure vector.
- **Positive:** Azure AI Search natively supports hybrid search — no custom re-ranking service needed.
- **Negative:** Index size increases ~15% (both BM25 inverted index + vector storage).
- **Mitigation:** Standard SKU of AI Search provides sufficient throughput at pilot scale.
