"""
Technical Librarian Agent

Performs hybrid RAG (BM25 + Ada-002 vector) over the Azure AI Search index
of technical manuals and SOPs. Given a fault code, retrieves the exact
repair procedure, parts list, and estimated duration.

Includes citation validation: each repair step is scored against the
source chunk for faithfulness. Steps scoring < 0.85 are flagged.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AsyncAzureOpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)

DEPLOYMENT_GPT4O = os.environ.get("AZURE_OPENAI_DEPLOYMENT_GPT4O", "gpt-4o")
DEPLOYMENT_ADA = os.environ.get("AZURE_OPENAI_DEPLOYMENT_ADA", "text-embedding-ada-002")
SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX", "kinetic-core-manuals")


class TechnicalLibrarianAgent:
    def __init__(self, client: AsyncAzureOpenAI | AsyncOpenAI):
        self.client = client
        self.search_client = SearchClient(
            endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
            index_name=SEARCH_INDEX,
            credential=AzureKeyCredential(os.environ["AZURE_SEARCH_KEY"]),
        )

    async def _embed_query(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            model=DEPLOYMENT_ADA,
            input=text,
        )
        return response.data[0].embedding

    def _hybrid_search(self, fault_code: str, root_cause: str, embedding: list[float]) -> list[dict]:
        query_text = f"{fault_code} {root_cause} repair procedure"
        vector_query = VectorizedQuery(
            vector=embedding,
            k_nearest_neighbors=10,
            fields="content_vector",
        )

        # Run two searches and merge: one broad hybrid + one fault-code-filtered.
        # The filtered search ensures we always get the exact procedure section even
        # if it scores lower on semantic similarity than introductory content.
        broad = list(self.search_client.search(
            search_text=query_text,
            vector_queries=[vector_query],
            select=["id", "content", "source_document", "section", "page_number", "fault_codes"],
            top=5,
        ))
        targeted = list(self.search_client.search(
            search_text=fault_code,
            select=["id", "content", "source_document", "section", "page_number", "fault_codes"],
            filter=f"fault_codes/any(c: c eq '{fault_code}')",
            top=5,
        ))

        seen: set[str] = set()
        chunks: list[dict] = []
        for r in targeted + broad:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            chunks.append({
                "id": r["id"],
                "content": r["content"],
                "source": r.get("source_document", ""),
                "section": r.get("section", ""),
                "page": r.get("page_number", 0),
                "score": r.get("@search.score", 0.0),
                "reranker_score": r.get("@search.reranker_score", 0.0),
            })

        return chunks[:8]  # cap at 8 to stay within prompt budget

    async def _synthesize_repair(self, fault_code: str, root_cause: str, chunks: list[dict]) -> dict:
        context = "\n\n---\n\n".join(
            f"[Source: {c['source']} §{c['section']} p.{c['page']}]\n{c['content']}"
            for c in chunks
        )
        prompt = f"""You are the Technical Librarian for Kinetic-Core critical infrastructure.

FAULT CODE: {fault_code}
ROOT CAUSE: {root_cause}

RETRIEVED MANUAL SECTIONS:
{context}

Extract and structure the repair procedure for this fault code. Respond with this JSON:
{{
  "repair_steps": [
    {{"step": 1, "action": "<exact step text>", "source_section": "<§X.X>", "safety_critical": true/false}},
    ...
  ],
  "parts_list": [
    {{"part_number": "<P-XXXX>", "part_name": "<name>", "quantity": 1}},
    ...
  ],
  "estimated_duration_minutes": <integer>,
  "team_size": <integer>,
  "tools_required": ["<tool 1>", ...],
  "safety_prerequisites": ["<prerequisite 1>", ...],
  "source_citations": ["<source ref 1>", ...]
}}

IMPORTANT: Only include information explicitly stated in the retrieved sections. If a step is not in the sources, do not invent it."""

        response = await self.client.chat.completions.create(
            model=DEPLOYMENT_GPT4O,
            messages=[
                {"role": "system", "content": "You are a precise technical documentation specialist. Extract information exactly as written in the source material. Never fabricate repair steps."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=2048,
        )

        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            logger.error("Failed to parse Librarian LLM response")
            return {"repair_steps": [], "parts_list": [], "estimated_duration_minutes": 60, "source_citations": []}

    async def _validate_faithfulness(self, repair_plan: dict, source_chunks: list[dict]) -> float:
        """Score repair steps against source chunks using GPT-4o as judge."""
        context = "\n".join(c["content"] for c in source_chunks[:3])
        steps_text = "\n".join(f"{s['step']}. {s['action']}" for s in repair_plan.get("repair_steps", []))

        prompt = f"""Rate the faithfulness of these repair steps against the source material.
Score 0.0 (completely hallucinated) to 1.0 (fully supported by source).

SOURCE MATERIAL:
{context[:2000]}

REPAIR STEPS TO EVALUATE:
{steps_text}

Respond with JSON: {{"faithfulness_score": <0.0-1.0>, "unfaithful_steps": [<step numbers>]}}"""

        response = await self.client.chat.completions.create(
            model=DEPLOYMENT_GPT4O,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=256,
        )
        try:
            result = json.loads(response.choices[0].message.content)
            return float(result.get("faithfulness_score", 0.0))
        except (json.JSONDecodeError, KeyError, ValueError):
            return 0.0

    async def lookup(self, fault_code: str, root_cause: str, incident_id: str) -> dict:
        started_at = datetime.now(timezone.utc)
        logger.info(f"[{incident_id}] Librarian: embedding query for {fault_code}")

        embedding = await self._embed_query(f"{fault_code} {root_cause}")
        chunks = self._hybrid_search(fault_code, root_cause, embedding)

        if not chunks:
            logger.warning(f"[{incident_id}] Librarian: no chunks found for {fault_code}")
            return {
                "agent": "TechnicalLibrarian",
                "incident_id": incident_id,
                "fault_code": fault_code,
                "repair_steps": [],
                "parts_list": [],
                "estimated_duration_minutes": None,
                "faithfulness_score": 0.0,
                "retrieval_count": 0,
                "error": "No matching documentation found",
            }

        repair_plan = await self._synthesize_repair(fault_code, root_cause, chunks)
        faithfulness = await self._validate_faithfulness(repair_plan, chunks)

        if faithfulness < 0.85:
            logger.warning(
                f"[{incident_id}] Librarian: faithfulness score {faithfulness:.2f} below threshold 0.85 — flagging for review"
            )

        return {
            "agent": "TechnicalLibrarian",
            "incident_id": incident_id,
            "looked_up_at": started_at.isoformat(),
            "fault_code": fault_code,
            "repair_steps": repair_plan.get("repair_steps", []),
            "parts_list": repair_plan.get("parts_list", []),
            "estimated_duration_minutes": repair_plan.get("estimated_duration_minutes", 60),
            "team_size": repair_plan.get("team_size", 2),
            "tools_required": repair_plan.get("tools_required", []),
            "safety_prerequisites": repair_plan.get("safety_prerequisites", []),
            "source_citations": repair_plan.get("source_citations", []),
            "faithfulness_score": faithfulness,
            "requires_human_review": faithfulness < 0.85,
            "retrieval_count": len(chunks),
            "retrieval_scores": [{"id": c["id"], "score": c["score"]} for c in chunks],
            "prompt_version": "v1.1",
        }
