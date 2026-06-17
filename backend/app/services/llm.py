import json
from collections.abc import AsyncGenerator

import litellm
from litellm import acompletion

from app.config import settings

litellm.set_verbose = False


def build_system_prompt(readme: str | None, file_tree: str | None) -> str:
    parts = [
        "You are a code assistant that answers questions about a GitHub repository.",
        "You have access to relevant code snippets retrieved from the codebase.",
        "Always reference specific file paths and line numbers when explaining code.",
        "If you're unsure about something, say so rather than guessing.",
        "Format code blocks with the appropriate language identifier.",
    ]

    if readme:
        parts.append(f"\n## Repository README\n\n{readme[:3000]}")

    if file_tree:
        parts.append(f"\n## File Structure\n\n```\n{file_tree[:2000]}\n```")

    return "\n".join(parts)


def build_context_message(chunks: list[dict], related_chunks: list[dict]) -> str:
    parts = ["## Relevant Code\n"]

    for chunk in chunks:
        header = f"### {chunk['file_path']}"
        if chunk.get("function_name"):
            header += f" → {chunk['function_name']}()"
        if chunk.get("class_name"):
            header += f" (class {chunk['class_name']})"
        header += f" [lines {chunk['line_start']}-{chunk['line_end']}]"

        parts.append(header)
        parts.append(f"```{chunk['language']}\n{chunk['code_text']}\n```\n")

    if related_chunks:
        parts.append("## Related Files (imported by / imports the above)\n")
        for chunk in related_chunks[:3]:
            parts.append(f"### {chunk['file_path']}")
            code_preview = chunk["code_text"][:500]
            parts.append(f"```{chunk['language']}\n{code_preview}\n```\n")

    return "\n".join(parts)


async def stream_chat_response(
    question: str,
    chunks: list[dict],
    related_chunks: list[dict],
    readme: str | None,
    file_tree: str | None,
    conversation_history: list[dict],
    model: str | None = None,
    api_key: str | None = None,
) -> AsyncGenerator[str, None]:
    model = model or settings.default_llm_model

    system_prompt = build_system_prompt(readme, file_tree)
    context_message = build_context_message(chunks, related_chunks)

    messages = [{"role": "system", "content": system_prompt}]

    for msg in conversation_history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    user_message = f"{context_message}\n\n## Question\n\n{question}"
    messages.append({"role": "user", "content": user_message})

    kwargs: dict = {"model": model, "messages": messages, "stream": True}

    if api_key:
        kwargs["api_key"] = api_key

    response = await acompletion(**kwargs)

    async for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
