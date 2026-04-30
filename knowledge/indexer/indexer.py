"""
Azure AI Search Indexer

Creates (or updates) the hybrid search index in Azure AI Search and
bulk-uploads embedded chunks. The index is configured for:
  - BM25 full-text search on the 'content' field
  - Vector search (HNSW) on the 'content_vector' field (1536 dims for Ada-002)
  - Semantic ranking using Azure AI's built-in reranker

Usage:
    # Full pipeline: chunk → embed → index
    python indexer.py --input knowledge/embedder/output/embedded_chunks.jsonl --create-index

    # Just upload new chunks to existing index
    python indexer.py --input knowledge/embedder/output/embedded_chunks.jsonl
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY", "")
INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX", "kinetic-core-manuals")
UPLOAD_BATCH_SIZE = 100

# Semantic Search (Azure AI reranker) requires Standard S1+ tier.
# Free tier uses BM25 + HNSW vector hybrid, which is still excellent for fault-code retrieval.
ENABLE_SEMANTIC_SEARCH = os.environ.get("AZURE_SEARCH_SEMANTIC", "false").lower() == "true"


def build_index_definition() -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SimpleField(name="source_document", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="section", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, sortable=True),
        SimpleField(name="token_estimate", type=SearchFieldDataType.Int32),
        SearchField(
            name="fault_codes",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
            filterable=True,
            facetable=True,
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="hnsw-profile",
        ),
    ]

    semantic = None
    if ENABLE_SEMANTIC_SEARCH:
        semantic = SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="default",
                    prioritized_fields=SemanticPrioritizedFields(
                        content_fields=[SemanticField(field_name="content")],
                        keywords_fields=[
                            SemanticField(field_name="fault_codes"),
                            SemanticField(field_name="section"),
                        ],
                    ),
                )
            ]
        )

    return SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo", parameters={"m": 4, "efConstruction": 400})],
            profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-algo")],
        ),
        semantic_search=semantic,
    )


def create_or_update_index(index_client: SearchIndexClient) -> None:
    index_def = build_index_definition()
    result = index_client.create_or_update_index(index_def)
    logger.info(f"Index '{result.name}' created/updated with {len(result.fields)} fields")


def upload_chunks(search_client: SearchClient, chunks: list[dict]) -> None:
    total = len(chunks)
    uploaded = 0

    for i in range(0, total, UPLOAD_BATCH_SIZE):
        batch = chunks[i : i + UPLOAD_BATCH_SIZE]
        t0 = time.perf_counter()
        results = search_client.upload_documents(batch)
        elapsed = time.perf_counter() - t0

        succeeded = sum(1 for r in results if r.succeeded)
        failed = len(batch) - succeeded
        uploaded += succeeded

        logger.info(
            f"Batch {i//UPLOAD_BATCH_SIZE + 1}: uploaded {succeeded}/{len(batch)} in {elapsed:.2f}s"
            + (f" — {failed} FAILED" if failed else "")
        )

    logger.info(f"Upload complete: {uploaded}/{total} chunks indexed in '{INDEX_NAME}'")


def main():
    parser = argparse.ArgumentParser(description="Upload embedded chunks to Azure AI Search")
    parser.add_argument("--input", default="knowledge/embedder/output/embedded_chunks.jsonl")
    parser.add_argument("--create-index", action="store_true", help="Create/update the index definition first")
    parser.add_argument("--delete-index", action="store_true", help="Delete and recreate the index (destructive!)")
    args = parser.parse_args()

    if not SEARCH_ENDPOINT or not SEARCH_KEY:
        logger.error("Set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY")
        return

    credential = AzureKeyCredential(SEARCH_KEY)
    index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=credential)
    search_client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)

    if args.delete_index:
        logger.warning(f"Deleting index '{INDEX_NAME}'...")
        index_client.delete_index(INDEX_NAME)
        args.create_index = True

    if args.create_index:
        create_or_update_index(index_client)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return

    with open(input_path) as f:
        chunks = [json.loads(line) for line in f if line.strip()]

    logger.info(f"Loaded {len(chunks)} embedded chunks from {input_path}")
    upload_chunks(search_client, chunks)


if __name__ == "__main__":
    main()
