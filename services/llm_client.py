"""
LLM Client — configurable via LLM_PROVIDER in .env
Supports: azure_openai | azure_foundry_serverless

To swap providers, change LLM_PROVIDER in .env — no code changes needed.
"""

import os
from dotenv import load_dotenv
load_dotenv(override=True)

PROVIDER = os.getenv("LLM_PROVIDER", "azure_openai")


def get_chat_response(messages: list[dict], system_prompt: str = None, max_tokens: int = 2048) -> str:
    """
    Single entry point for all LLM calls across the app.
    Returns the text response as a string.

    Args:
        messages: List of {"role": "user"|"assistant", "content": "..."}
        system_prompt: Optional system instruction (prepended automatically)
        max_tokens: Max tokens in response
    """
    if PROVIDER == "azure_openai":
        return _call_azure_openai(messages, system_prompt, max_tokens)
    elif PROVIDER == "azure_foundry_serverless":
        return _call_azure_foundry(messages, system_prompt, max_tokens)
    elif PROVIDER == "anthropic":
        return _call_anthropic(messages, system_prompt, max_tokens)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: '{PROVIDER}'. Must be azure_openai, azure_foundry_serverless, or anthropic.")


def get_embedding(text: str) -> list[float]:
    """
    Get text embedding vector for RAG indexing and retrieval.
    Always uses Azure OpenAI embeddings (ada-002) regardless of chat provider —
    embeddings must be consistent across index and query time.
    """
    from openai import AzureOpenAI
    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    )
    resp = client.embeddings.create(
        input=text,
        model=os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
    )
    return resp.data[0].embedding


# ── Provider implementations ──────────────────────────────────────────

def _call_azure_openai(messages: list[dict], system_prompt: str, max_tokens: int) -> str:
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    )

    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        messages=full_messages,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content


def _call_azure_foundry(messages: list[dict], system_prompt: str, max_tokens: int) -> str:
    """
    Azure AI Foundry Serverless endpoint — supports Claude and other
    models deployed via the model catalog (no quota allocation needed).
    Uses the azure-ai-inference SDK which is provider-agnostic.
    """
    from azure.ai.inference import ChatCompletionsClient
    from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage
    from azure.core.credentials import AzureKeyCredential

    client = ChatCompletionsClient(
        endpoint=os.getenv("AZURE_FOUNDRY_ENDPOINT"),
        credential=AzureKeyCredential(os.getenv("AZURE_FOUNDRY_KEY"))
    )

    # Convert message dicts to SDK message objects
    sdk_messages = []
    if system_prompt:
        sdk_messages.append(SystemMessage(content=system_prompt))

    role_map = {
        "user": UserMessage,
        "assistant": AssistantMessage,
        "system": SystemMessage
    }
    for msg in messages:
        msg_class = role_map.get(msg["role"], UserMessage)
        sdk_messages.append(msg_class(content=msg["content"]))

    response = client.complete(
        messages=sdk_messages,
        model=os.getenv("AZURE_FOUNDRY_MODEL", "claude-sonnet-4-6"),
        max_tokens=max_tokens
    )
    return response.choices[0].message.content


def _call_anthropic(messages: list[dict], system_prompt: str, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=max_tokens,
        system=system_prompt or "You are a helpful assistant.",
        messages=messages
    )
    return response.content[0].text


# ── Quick connectivity test ───────────────────────────────────────────

if __name__ == "__main__":
    print(f"Testing LLM provider: {PROVIDER}")
    result = get_chat_response(
        messages=[{"role": "user", "content": "Reply with exactly: CONNECTION OK"}],
        system_prompt="You are a helpful assistant."
    )
    print(f"OK Response: {result}")
