import shutil
import tempfile
from pathlib import Path

from git import Repo

from app.config import settings
from app.utils.file_filter import collect_code_files, build_file_tree


class CloneResult:
    def __init__(
        self,
        files: list[dict],
        file_tree: str,
        readme: str | None,
        owner: str,
        name: str,
        default_branch: str,
    ):
        self.files = files
        self.file_tree = file_tree
        self.readme = readme
        self.owner = owner
        self.name = name
        self.default_branch = default_branch


def parse_github_url(url: str) -> tuple[str, str]:
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.split("/")
    owner = parts[-2]
    name = parts[-1]
    return owner, name


def clone_and_extract(url: str, github_token: str | None = None) -> CloneResult:
    owner, name = parse_github_url(url)

    clone_url = url
    if github_token:
        clone_url = url.replace("https://", f"https://{github_token}@")
    if not clone_url.endswith(".git"):
        clone_url += ".git"

    tmp_dir = tempfile.mkdtemp(prefix="codebase_chat_")

    try:
        repo = Repo.clone_from(
            clone_url,
            tmp_dir,
            depth=1,
            single_branch=True,
            no_checkout=False,
        )

        default_branch = repo.active_branch.name

        files = collect_code_files(tmp_dir)

        if len(files) > settings.max_repo_files:
            raise ValueError(
                f"Repository has {len(files)} code files, exceeding the limit of {settings.max_repo_files}"
            )

        readme = None
        for readme_name in ["README.md", "readme.md", "README.rst", "README.txt", "README"]:
            readme_path = Path(tmp_dir) / readme_name
            if readme_path.exists():
                readme = readme_path.read_text(encoding="utf-8", errors="ignore")[:10000]
                break

        file_paths = [f["path"] for f in files]
        file_tree = build_file_tree(file_paths)

        return CloneResult(
            files=files,
            file_tree=file_tree,
            readme=readme,
            owner=owner,
            name=name,
            default_branch=default_branch,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
