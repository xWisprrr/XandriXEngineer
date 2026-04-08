"""
XandriX Engineer - Tool: File System Operations
"""
import json
import mimetypes
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import SUPPORTED_LANGUAGES
from backend.core.logger import get_logger
from backend.models.schemas import FileNode

logger = get_logger("tool.filesystem")

LANGUAGE_EXT_MAP: dict[str, str] = {}
for lang, info in SUPPORTED_LANGUAGES.items():
    for ext in info["extensions"]:
        LANGUAGE_EXT_MAP[ext] = lang


class FileSystem:
    """File system operations for project management."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.cwd()

    def resolve(self, path: str) -> Path:
        """Resolve a path relative to the base directory, preventing path traversal."""
        p = Path(path)
        base = self.base_dir.resolve()
        if p.is_absolute():
            resolved = p.resolve()
        else:
            resolved = (base / p).resolve()
        # Enforce that the resolved path is within base_dir to prevent path injection
        try:
            resolved.relative_to(base)
        except ValueError:
            # Strip traversal components and confine to base_dir
            safe_parts = [part for part in p.parts if part not in ("..", ".")]
            resolved = (base / Path(*safe_parts)).resolve() if safe_parts else base
        return resolved

    def read(self, path: str) -> str:
        """Read a file and return its contents."""
        full_path = self.resolve(path)
        logger.tool("filesystem", f"Reading {full_path}")
        return full_path.read_text(encoding="utf-8", errors="replace")

    def write(self, path: str, content: str, create_parents: bool = True) -> None:
        """Write content to a file, optionally creating parent directories."""
        full_path = self.resolve(path)
        if create_parents:
            full_path.parent.mkdir(parents=True, exist_ok=True)
        logger.tool("filesystem", f"Writing {full_path} ({len(content)} chars)")
        full_path.write_text(content, encoding="utf-8")

    def append(self, path: str, content: str) -> None:
        """Append content to a file."""
        full_path = self.resolve(path)
        with open(full_path, "a", encoding="utf-8") as f:
            f.write(content)

    def delete(self, path: str) -> None:
        """Delete a file or directory."""
        full_path = self.resolve(path)
        if full_path.is_dir():
            shutil.rmtree(full_path)
        elif full_path.exists():
            full_path.unlink()
        logger.tool("filesystem", f"Deleted {full_path}")

    def exists(self, path: str) -> bool:
        return self.resolve(path).exists()

    def mkdir(self, path: str) -> None:
        self.resolve(path).mkdir(parents=True, exist_ok=True)

    def list_dir(self, path: str = ".") -> list[str]:
        """List files and directories in a path."""
        full_path = self.resolve(path)
        return [item.name for item in full_path.iterdir()]

    def tree(self, path: str = ".", max_depth: int = 4, _depth: int = 0) -> Optional[FileNode]:
        """Build a file tree structure."""
        full_path = self.resolve(path) if _depth == 0 else Path(path)
        if not full_path.exists():
            return None

        # Skip hidden files/dirs and common noise
        skip_patterns = {".git", "__pycache__", "node_modules", ".venv", "venv",
                         "dist", "build", ".next", "*.pyc", ".DS_Store"}

        if full_path.name in skip_patterns:
            return None

        stat = full_path.stat()
        node = FileNode(
            name=full_path.name,
            path=str(full_path),
            is_dir=full_path.is_dir(),
            size=stat.st_size if not full_path.is_dir() else None,
            modified=datetime.fromtimestamp(stat.st_mtime),
            language=LANGUAGE_EXT_MAP.get(full_path.suffix) if not full_path.is_dir() else None,
        )

        if full_path.is_dir() and _depth < max_depth:
            children = []
            try:
                for item in sorted(full_path.iterdir()):
                    if item.name.startswith(".") and item.name not in {".env", ".gitignore"}:
                        continue
                    if item.name in skip_patterns:
                        continue
                    child = self.tree(str(item), max_depth, _depth + 1)
                    if child:
                        children.append(child)
            except PermissionError:
                pass
            node.children = children

        return node

    def find_files(self, pattern: str, path: str = ".") -> list[str]:
        """Find files matching a glob pattern."""
        full_path = self.resolve(path)
        return [str(p) for p in full_path.glob(pattern)]

    def copy(self, src: str, dst: str) -> None:
        """Copy a file or directory."""
        src_path = self.resolve(src)
        dst_path = self.resolve(dst)
        if src_path.is_dir():
            shutil.copytree(src_path, dst_path)
        else:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)

    def move(self, src: str, dst: str) -> None:
        """Move a file or directory."""
        src_path = self.resolve(src)
        dst_path = self.resolve(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))

    def read_json(self, path: str) -> dict:
        """Read and parse a JSON file."""
        return json.loads(self.read(path))

    def write_json(self, path: str, data: dict, indent: int = 2) -> None:
        """Serialize and write a JSON file."""
        self.write(path, json.dumps(data, indent=indent, default=str))

    def get_project_structure(self, path: str = ".") -> str:
        """Return a text representation of the project structure."""
        def _render(node: FileNode, prefix: str = "", is_last: bool = True) -> list[str]:
            connector = "└── " if is_last else "├── "
            lines = [prefix + connector + node.name]
            if node.children:
                extension = "    " if is_last else "│   "
                for i, child in enumerate(node.children):
                    is_child_last = i == len(node.children) - 1
                    lines.extend(_render(child, prefix + extension, is_child_last))
            return lines

        tree = self.tree(path)
        if not tree:
            return ""
        return "\n".join(_render(tree, "", True))

    def detect_language(self, path: str) -> Optional[str]:
        """Detect the programming language of a file by extension."""
        ext = Path(path).suffix.lower()
        return LANGUAGE_EXT_MAP.get(ext)
