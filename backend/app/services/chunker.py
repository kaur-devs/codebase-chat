import ast


def chunk_python_file(content: str, file_path: str) -> list[dict]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return _fallback_chunk(content, file_path, "python")

    chunks = []
    lines = content.split("\n")

    module_level_lines = set(range(1, len(lines) + 1))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = node.end_lineno or start
            code = "\n".join(lines[start - 1 : end])

            class_name = None
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    for child in ast.iter_child_nodes(parent):
                        if child is node:
                            class_name = parent.name
                            break

            chunks.append({
                "file_path": file_path,
                "function_name": node.name,
                "class_name": class_name,
                "line_start": start,
                "line_end": end,
                "language": "python",
                "code_text": code,
            })

            for line_num in range(start, end + 1):
                module_level_lines.discard(line_num)

        elif isinstance(node, ast.ClassDef):
            start = node.lineno
            first_child_start = None
            for child in ast.iter_child_nodes(node):
                if hasattr(child, "lineno"):
                    first_child_start = child.lineno
                    break

            end = (first_child_start - 1) if first_child_start else (node.end_lineno or start)
            code = "\n".join(lines[start - 1 : end])

            if code.strip():
                chunks.append({
                    "file_path": file_path,
                    "function_name": None,
                    "class_name": node.name,
                    "line_start": start,
                    "line_end": end,
                    "language": "python",
                    "code_text": code,
                })

            for line_num in range(start, end + 1):
                module_level_lines.discard(line_num)

    if module_level_lines:
        sorted_lines = sorted(module_level_lines)
        module_code = "\n".join(lines[i - 1] for i in sorted_lines)
        if module_code.strip():
            chunks.append({
                "file_path": file_path,
                "function_name": None,
                "class_name": None,
                "line_start": sorted_lines[0],
                "line_end": sorted_lines[-1],
                "language": "python",
                "code_text": module_code,
            })

    return chunks


def _fallback_chunk(content: str, file_path: str, language: str) -> list[dict]:
    lines = content.split("\n")
    chunks = []
    chunk_size = 60
    overlap = 10

    for start_idx in range(0, len(lines), chunk_size - overlap):
        end_idx = min(start_idx + chunk_size, len(lines))
        code = "\n".join(lines[start_idx:end_idx])

        if not code.strip():
            continue

        chunks.append({
            "file_path": file_path,
            "function_name": None,
            "class_name": None,
            "line_start": start_idx + 1,
            "line_end": end_idx,
            "language": language,
            "code_text": code,
        })

        if end_idx >= len(lines):
            break

    return chunks


def chunk_file(content: str, file_path: str, language: str) -> list[dict]:
    if language == "python":
        return chunk_python_file(content, file_path)

    # TODO: Add tree-sitter chunking for JS/TS in a later iteration
    return _fallback_chunk(content, file_path, language)
