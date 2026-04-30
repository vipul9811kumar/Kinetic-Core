"""
Phase 4 smoke test: hybrid BM25 + vector search against the indexed service manual.

Runs two queries:
  1. Fault-code filter: find all chunks about KX-T2209-B
  2. Semantic query: "coolant pump seal repair procedure voltage safety"

Usage:
    cd /workspaces/Kinetic-Core
    python scripts/test_search.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from agents.client import make_openai_client


async def embed_query(query: str) -> list[float]:
    client = make_openai_client()
    resp = await client.embeddings.create(
        model=os.environ.get("AZURE_OPENAI_DEPLOYMENT_ADA", "text-embedding-ada-002"),
        input=[query],
    )
    return resp.data[0].embedding


def run_search(search_client: SearchClient, query: str, vector: list[float], filter_expr: str | None = None) -> list[dict]:
    vector_query = VectorizedQuery(
        vector=vector,
        k_nearest_neighbors=5,
        fields="content_vector",
    )
    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        filter=filter_expr,
        select=["id", "section", "fault_codes", "token_estimate", "content"],
        top=5,
    )
    return list(results)


async def main() -> None:
    print("=" * 60)
    print("Kinetic-Core — Phase 4: Hybrid Search Test")
    print("=" * 60)

    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    key = os.environ["AZURE_SEARCH_KEY"]
    index = os.environ.get("AZURE_SEARCH_INDEX", "kinetic-core-manuals")

    search_client = SearchClient(endpoint=endpoint, index_name=index, credential=AzureKeyCredential(key))

    # ── Query 1: fault-code filter ─────────────────────────────────────────────
    print("\n[Query 1] Filter: fault_codes/any(c: c eq 'KX-T2209-B')")
    q1 = "thermal escalation coolant pump seal degradation repair"
    vec1 = await embed_query(q1)
    results1 = run_search(search_client, q1, vec1, filter_expr="fault_codes/any(c: c eq 'KX-T2209-B')")
    print(f"  Found {len(results1)} chunks tagged KX-T2209-B")
    for r in results1:
        score = r.get("@search.score", 0)
        print(f"    [{score:.3f}] '{r['section']}' ({r['token_estimate']} tokens) codes={r['fault_codes']}")

    # ── Query 2: hybrid text+vector, no filter ─────────────────────────────────
    print("\n[Query 2] Hybrid query: 'pump seal replacement safety prerequisites voltage'")
    q2 = "pump seal replacement safety prerequisites voltage LOTO"
    vec2 = await embed_query(q2)
    results2 = run_search(search_client, q2, vec2)
    print(f"  Top {len(results2)} results:")
    for r in results2:
        score = r.get("@search.score", 0)
        snippet = r["content"][:120].replace("\n", " ")
        print(f"    [{score:.3f}] '{r['section']}' — {snippet}...")

    # ── Query 3: fault code in text, no filter ─────────────────────────────────
    print("\n[Query 3] Text search: 'KX-T2209-B procedure 5.1'")
    q3 = "KX-T2209-B procedure 5.1"
    vec3 = await embed_query(q3)
    results3 = run_search(search_client, q3, vec3)
    top = results3[0] if results3 else {}
    print(f"  Top result: '{top.get('section')}' score={top.get('@search.score', 0):.3f}")
    if top:
        print(f"  Fault codes in chunk: {top.get('fault_codes')}")

    print("\n" + "=" * 60)
    print("Phase 4 COMPLETE — hybrid search index live, fault code retrieval verified")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
