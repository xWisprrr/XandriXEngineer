import fnmatch
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import aiofiles

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FileInfo:
    name: str
    path: str
    size: int
    modified: str
    is_dir: bool
    extension: str


class FileSystemTool:
    name = "filesystem"

    def __init__(self, base_dir: str = "./workspace") -> None:
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _safe_path(self, path: str) -> str:
        if os.path.isabs(path):
            abs_path = os.path.normpath(path)
        else:
            abs_path = os.path.normpath(os.path.join(self.base_dir, path))
        if not abs_path.startswith(self.base_dir):
            logger.warning(f"Path traversal attempt: {path}")
            return self.base_dir
        return abs_path

    async def read_file(self, path: str) -> str:
        abs_path = self._safe_path(path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: {path}")
        async with aiofiles.open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            return await f.read()

    async def write_file(self, path: str, content: str) -> bool:
        abs_path = self._safe_path(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        async with aiofiles.open(abs_path, "w", encoding="utf-8") as f:
            await f.write(content)
        logger.debug(f"Written file: {abs_path}")
        return True

    def list_directory(self, path: str = ".") -> List[FileInfo]:
        abs_path = self._safe_path(path)
        if not os.path.isdir(abs_path):
            return []
        items: List[FileInfo] = []
        for entry in sorted(os.scandir(abs_path), key=lambda e: (not e.is_dir(), e.name)):
            stat = entry.stat()
            items.append(
                FileInfo(
                    name=entry.name,
                    path=os.path.relpath(entry.path, self.base_dir),
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    is_dir=entry.is_dir(),
                    extension=os.path.splitext(entry.name)[1] if not entry.is_dir() else "",
                )
            )
        return items

    def create_directory(self, path: str) -> bool:
        abs_path = self._safe_path(path)
        os.makedirs(abs_path, exist_ok=True)
        return True

    def delete_file(self, path: str) -> bool:
        abs_path = self._safe_path(path)
        if os.path.isfile(abs_path):
            os.remove(abs_path)
            return True
        elif os.path.isdir(abs_path):
            import shutil
            shutil.rmtree(abs_path)
            return True
        return False

    def search_files(self, pattern: str, directory: str = ".") -> List[str]:
        abs_dir = self._safe_path(directory)
        matched: List[str] = []
        for root, dirs, files in os.walk(abs_dir):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                if fnmatch.fnmatch(fname, pattern) or fnmatch.fnmatch(
                    os.path.join(root, fname), pattern
                ):
                    matched.append(os.path.relpath(os.path.join(root, fname), self.base_dir))
        return matched

    def file_exists(self, path: str) -> bool:
        return os.path.exists(self._safe_path(path))
