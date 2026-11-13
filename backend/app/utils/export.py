import json
import re

CODE_FENCE = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)


def collect_code_blocks(messages, found=[]):
    for message in messages:
        for match in CODE_FENCE.finditer(message.content):
            found.append(
                {"language": match.group(1) or "text", "code": match.group(2)}
            )
    return found


def format_sources(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        sources = json.loads(raw)
    except json.JSONDecodeError:
        return ""

    lines = []
    for source in sources:
        location = f"{source['file_path']}:{source['line_start']}-{source['line_end']}"
        name = source.get("function_name") or source.get("class_name")
        lines.append(f"- `{location}`" + (f" — {name}" if name else ""))
    return "\n".join(lines)


def conversation_to_markdown(title: str, messages) -> str:
    parts = [f"# {title}", ""]

    for message in messages:
        speaker = "You" if message.role == "user" else "Assistant"
        parts.append(f"## {speaker}")
        parts.append("")
        parts.append(message.content)
        parts.append("")

        sources = format_sources(getattr(message, "sources", None))
        if sources:
            parts.append("**Sources**")
            parts.append("")
            parts.append(sources)
            parts.append("")

    blocks = collect_code_blocks(messages)
    if blocks:
        parts.append(f"_{len(blocks)} code block(s) referenced._")

    return "\n".join(parts)
