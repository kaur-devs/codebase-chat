import os
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".env", "dist", "build", ".next", ".nuxt", "coverage",
    ".pytest_cache", ".mypy_cache", ".tox", "vendor", "target",
    ".idea", ".vscode", ".DS_Store",
}

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".bmp", ".webp",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pyc", ".pyo", ".class", ".o",
    ".lock", ".sum",
    ".min.js", ".min.css",
}

CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".rb",
    ".java", ".kt", ".swift", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".php", ".lua", ".r", ".scala", ".dart",
    ".html", ".css", ".scss", ".sass", ".less",
    ".sql", ".sh", ".bash", ".zsh", ".fish",
    ".yaml", ".yml", ".toml", ".json", ".xml",
    ".md", ".txt", ".rst", ".env.example",
    ".dockerfile", ".tf", ".hcl",
}

MAX_FILE_SIZE_BYTES = 100_000  # 100KB per file


def should_skip_dir(dirname: str) -> bool:
    return dirname in SKIP_DIRS or dirname.startswith(".")


def should_include_file(filepath: str) -> bool:
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext in SKIP_EXTENSIONS:
        return False

    if ext in CODE_EXTENSIONS:
        return True

    if path.name in {"Dockerfile", "Makefile", "Procfile", "Gemfile", "Rakefile"}:
        return True

    return False


def is_file_too_large(filepath: str) -> bool:
    return os.path.getsize(filepath) > MAX_FILE_SIZE_BYTES


def get_language(filepath: str) -> str:
    ext_map = {
        ".py": "python", ".js": "javascript", ".jsx": "javascript",
        ".ts": "typescript", ".tsx": "typescript",
        ".go": "go", ".rs": "rust", ".rb": "ruby",
        ".java": "java", ".kt": "kotlin", ".swift": "swift",
        ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
        ".cs": "csharp", ".php": "php",
        ".html": "html", ".css": "css", ".scss": "scss",
        ".sql": "sql", ".sh": "bash",
        ".yaml": "yaml", ".yml": "yaml",
        ".json": "json", ".xml": "xml", ".md": "markdown",
        ".toml": "toml",
    }
    ext = Path(filepath).suffix.lower()
    return ext_map.get(ext, "text")


def collect_code_files(repo_path: str) -> list[dict]:
    files = []
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]

        for filename in filenames:
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, repo_path)

            if not should_include_file(filepath):
                continue
            if is_file_too_large(filepath):
                continue

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError):
                continue

            files.append({
                "path": rel_path,
                "content": content,
                "language": get_language(filepath),
            })

    return files


def build_file_tree(file_paths: list[str]) -> str:
    tree: dict = {}
    for path in sorted(file_paths):
        parts = path.split(os.sep)
        current = tree
        for part in parts:
            current = current.setdefault(part, {})

    lines: list[str] = []

    def render(node: dict, prefix: str = "") -> None:
        entries = sorted(node.keys())
        for i, name in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{name}")
            if node[name]:
                extension = "    " if is_last else "│   "
                render(node[name], prefix + extension)

    render(tree)
    return "\n".join(lines)
