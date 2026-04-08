import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CommitInfo:
    hash: str
    message: str
    author: str
    timestamp: str


class GitTool:
    name = "git"

    def __init__(self, repo_path: Optional[str] = None) -> None:
        self.repo_path = repo_path or os.getcwd()
        self._repo = None

    def _get_repo(self):
        if self._repo is None:
            try:
                import git
                self._repo = git.Repo(self.repo_path)
            except Exception as exc:
                logger.error(f"Failed to open git repo at {self.repo_path}: {exc}")
                raise
        return self._repo

    def init_repo(self, path: str) -> bool:
        try:
            import git
            os.makedirs(path, exist_ok=True)
            git.Repo.init(path)
            self.repo_path = path
            self._repo = None
            logger.info(f"Initialized git repo at {path}")
            return True
        except Exception as exc:
            logger.error(f"Git init failed: {exc}")
            return False

    def commit(self, message: str, files: Optional[List[str]] = None) -> str:
        try:
            repo = self._get_repo()
            if files:
                repo.index.add(files)
            else:
                repo.git.add(A=True)
            commit_obj = repo.index.commit(message)
            logger.info(f"Committed: {commit_obj.hexsha[:8]} - {message}")
            return commit_obj.hexsha
        except Exception as exc:
            logger.error(f"Git commit failed: {exc}")
            return ""

    def create_branch(self, name: str) -> bool:
        try:
            repo = self._get_repo()
            repo.create_head(name)
            logger.info(f"Created branch: {name}")
            return True
        except Exception as exc:
            logger.error(f"Create branch failed: {exc}")
            return False

    def get_diff(self) -> str:
        try:
            repo = self._get_repo()
            return repo.git.diff()
        except Exception as exc:
            logger.error(f"Git diff failed: {exc}")
            return ""

    def get_log(self, limit: int = 10) -> List[CommitInfo]:
        try:
            repo = self._get_repo()
            commits: List[CommitInfo] = []
            for commit in list(repo.iter_commits())[:limit]:
                commits.append(
                    CommitInfo(
                        hash=commit.hexsha[:8],
                        message=commit.message.strip(),
                        author=str(commit.author),
                        timestamp=datetime.fromtimestamp(commit.committed_date).isoformat(),
                    )
                )
            return commits
        except Exception as exc:
            logger.error(f"Git log failed: {exc}")
            return []

    def get_status(self) -> str:
        try:
            repo = self._get_repo()
            return repo.git.status()
        except Exception as exc:
            logger.error(f"Git status failed: {exc}")
            return ""
