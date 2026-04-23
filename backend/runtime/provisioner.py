import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EnvInfo:
    path: str
    language: str
    dependencies: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EnvironmentProvisioner:
    def __init__(self, base_dir: str = "./workspace") -> None:
        self.base_dir = os.path.abspath(base_dir)

    def _run_cmd(self, cmd: str, cwd: str) -> bool:
        try:
            result = subprocess.run(
                cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                logger.warning(f"Command failed: {cmd}\n{result.stderr}")
                return False
            logger.debug(f"Command succeeded: {cmd}")
            return True
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {cmd}")
            return False
        except Exception as exc:
            logger.error(f"Command error: {exc}")
            return False

    def setup_virtual_env(self, path: str) -> bool:
        venv_path = os.path.join(path, ".venv")
        if os.path.exists(venv_path):
            return True
        return self._run_cmd("python3 -m venv .venv", cwd=path)

    def install_dependencies(self, language: str, deps: List[str], cwd: str) -> bool:
        if not deps:
            return True
        pkg_str = " ".join(deps)
        install_cmds: Dict[str, str] = {
            "python": f"pip3 install {pkg_str}",
            "javascript": f"npm install {pkg_str}",
            "typescript": f"npm install {pkg_str}",
            "go": f"go get {pkg_str}",
            "rust": f"cargo add {pkg_str}",
            "java": "echo 'Use Maven/Gradle for Java deps'",
        }
        cmd = install_cmds.get(language.lower())
        if not cmd:
            logger.warning(f"No install command for language: {language}")
            return False
        return self._run_cmd(cmd, cwd=cwd)

    def create_project_env(
        self,
        project_name: str,
        language: str,
        dependencies: Optional[List[str]] = None,
    ) -> EnvInfo:
        project_dir = os.path.join(self.base_dir, project_name)
        os.makedirs(project_dir, exist_ok=True)
        deps = dependencies or []

        if language.lower() == "python":
            self.setup_virtual_env(project_dir)
            if deps:
                venv_pip = os.path.join(project_dir, ".venv", "bin", "pip")
                if os.path.exists(venv_pip):
                    self._run_cmd(f"{venv_pip} install {' '.join(deps)}", cwd=project_dir)
                else:
                    self.install_dependencies(language, deps, project_dir)
        elif language.lower() in ("javascript", "typescript"):
            if not os.path.exists(os.path.join(project_dir, "package.json")):
                self._run_cmd("npm init -y", cwd=project_dir)
            if deps:
                self.install_dependencies(language, deps, project_dir)
        elif language.lower() == "go":
            if not os.path.exists(os.path.join(project_dir, "go.mod")):
                self._run_cmd(f"go mod init {project_name}", cwd=project_dir)
            if deps:
                self.install_dependencies(language, deps, project_dir)
        elif language.lower() == "rust":
            if not os.path.exists(os.path.join(project_dir, "Cargo.toml")):
                self._run_cmd(f"cargo init --name {project_name}", cwd=project_dir)

        logger.info(f"Created project env: {project_name} ({language}) at {project_dir}")
        return EnvInfo(path=project_dir, language=language, dependencies=deps)


environment_provisioner = EnvironmentProvisioner()
