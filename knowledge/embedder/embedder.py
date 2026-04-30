"""
Ada-002 Embedder

Takes chunks from the semantic chunker and generates embeddings using
Azure OpenAI text-embedding-ada-002. Batches requests to respect API
rate limits and writes enriched chunks (with embedding vectors) to a
JSONL file for the indexer to consume.

Usage:
    python embedder.py --input knowledge/chunker/output/chunks.jsonl \
                       --output knowledge/embedder/output/embedded_chunks.jsonl
"""

import argparse
import asyncio
import json
import logging
import os
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.client import make_openai_client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Azure uses a named deployment; direct OpenAI uses the model name — both resolve to the same value here.
DEPLOYMENT_ADA = os.environ.get("AZURE_OPENAI_DEPLOYMENT_ADA", "text-embedding-ada-002")
BATCH_SIZE = 16
RATE_LIMIT_DELAY = 0.5


class ChunkEmbedder:
    def __init__(self):
        self.client = make_openai_client()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(
            model=DEPLOYMENT_ADA,
            input=texts,
        )
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]

    async def embed_chunks(self, chunks: list[dict]) -> list[dict]:
        embedded = []
        total = len(chunks)

        for i in range(0, total, BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            texts = [c["content"] for c in batch]

            logger.info(f"Embedding batch {i//BATCH_SIZE + 1} / {(total + BATCH_SIZE - 1)//BATCH_SIZE} ({len(batch)} chunks)")
            t0 = time.perf_counter()

            vectors = await self.embed_batch(texts)

            elapsed = time.perf_counter() - t0
            logger.info(f"  Done in {elapsed:.2f}s — {len(vectors[0])} dims per vector")

            for chunk, vector in zip(batch, vectors):
                embedded.append({**chunk, "content_vector": vector})

            if i + BATCH_SIZE < total:
                await asyncio.sleep(RATE_LIMIT_DELAY)

        return embedded

    async def run(self, input_path: Path, output_path: Path) -> None:
        with open(input_path) as f:
            chunks = [json.loads(line) for line in f if line.strip()]

        logger.info(f"Loaded {len(chunks)} chunks from {input_path}")
        embedded = await self.embed_chunks(chunks)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            for item in embedded:
                f.write(json.dumps(item) + "\n")

        logger.info(f"Wrote {len(embedded)} embedded chunks → {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Embed knowledge chunks with Ada-002")
    parser.add_argument("--input", default="knowledge/chunker/output/chunks.jsonl")
    parser.add_argument("--output", default="knowledge/embedder/output/embedded_chunks.jsonl")
    args = parser.parse_args()

    embedder = ChunkEmbedder()
    asyncio.run(embedder.run(Path(args.input), Path(args.output)))


if __name__ == "__main__":
    main()
