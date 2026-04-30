"""
OpenAI client factory.

Returns AsyncAzureOpenAI when AZURE_OPENAI_ENDPOINT is set,
otherwise falls back to AsyncOpenAI (direct API) using OPENAI_API_KEY.
This lets us develop against the direct API while Azure quota is pending,
then switch back to Azure with a single env-var change.
"""

import os

from openai import AsyncAzureOpenAI, AsyncOpenAI


def make_openai_client() -> AsyncAzureOpenAI | AsyncOpenAI:
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
    if azure_endpoint and not azure_endpoint.startswith(("https://", "http://")):
        azure_endpoint = ""  # invalid — treat as unset, fall through to direct OpenAI

    if azure_endpoint:
        return AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=os.environ.get("AZURE_OPENAI_KEY", ""),
            api_version="2024-08-01-preview",
        )

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "No OpenAI client configured. Set AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_KEY "
            "for Azure, or OPENAI_API_KEY for direct OpenAI."
        )
    return AsyncOpenAI(api_key=api_key)
