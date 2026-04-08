"""
XandriX Engineer - Environment Provisioner
Automatically detects, installs, and configures development environments.
"""
import json
import re
from pathlib import Path
from typing import Optional

from backend.core.logger import get_logger
from backend.models.schemas import ExecutionResult, ExecutionStatus
from backend.tools.filesystem import FileSystem
from backend.tools.terminal import Terminal

logger = get_logger("provisioner")


class EnvironmentProvisioner:
    """Automatically provisions development environments for projects."""

    def __init__(self, terminal: Terminal = None):
        self.terminal = terminal or Terminal()
        self.fs = FileSystem()

    async def provision(self, project_dir: Path, language: str, dependencies: list[str] = None) -> ExecutionResult:
        """Fully provision an environment for a project."""
        logger.info(f"Provisioning {language} environment at {project_dir}")
        self.terminal.set_working_dir(project_dir)

        # Ensure runtime is available
        runtime_result = await self._ensure_runtime(language)
        if runtime_result.status == ExecutionStatus.ERROR:
            logger.warning(f"Runtime check warning: {runtime_result.stderr}")

        # Initialize project structure
        await self._init_project(project_dir, language)

        # Install dependencies
        if dependencies:
            dep_result = await self._install_dependencies(project_dir, language, dependencies)
            if dep_result.status == ExecutionStatus.ERROR:
                return dep_result

        logger.success(f"Environment provisioned for {language}")
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout=f"Environment ready for {language}",
        )

    async def _ensure_runtime(self, language: str) -> ExecutionResult:
        """Check if runtime is available, attempt install if missing."""
        checks = {
            "python": ("python3 --version", "python3"),
            "javascript": ("node --version", "nodejs"),
            "typescript": ("node --version", "nodejs"),
            "go": ("go version", "golang"),
            "rust": ("rustc --version", None),
            "java": ("java -version", "default-jdk"),
            "c": ("gcc --version", "gcc"),
            "cpp": ("g++ --version", "g++"),
            "bash": ("bash --version", None),
            "sql": ("sqlite3 --version", "sqlite3"),
        }

        check_cmd, apt_pkg = checks.get(language, ("echo ok", None))
        result = await self.terminal.run(check_cmd + " 2>&1 | head -1")

        if result.return_code != 0 and apt_pkg:
            logger.info(f"Installing {apt_pkg}...")
            install = await self.terminal.run(
                f"apt-get install -y {apt_pkg} 2>&1 || echo 'manual install needed'"
            )
            return install

        return result

    async def _init_project(self, project_dir: Path, language: str) -> None:
        """Initialize project structure and config files."""
        project_dir.mkdir(parents=True, exist_ok=True)

        if language == "python":
            await self._init_python(project_dir)
        elif language in ("javascript", "typescript"):
            await self._init_node(project_dir, language)
        elif language == "go":
            await self._init_go(project_dir)
        elif language == "rust":
            await self._init_rust(project_dir)

    async def _init_python(self, project_dir: Path) -> None:
        """Set up Python virtual environment."""
        venv_dir = project_dir / ".venv"
        if not venv_dir.exists():
            logger.info("Creating Python virtual environment...")
            result = await self.terminal.run(
                f"python3 -m venv {venv_dir}",
                working_dir=project_dir,
            )
            if result.return_code == 0:
                self.terminal.set_env(
                    "PATH", f"{venv_dir}/bin:{self.terminal._env.get('PATH', '')}"
                )
                self.terminal.set_env("VIRTUAL_ENV", str(venv_dir))

    async def _init_node(self, project_dir: Path, language: str) -> None:
        """Set up Node.js project."""
        pkg_json = project_dir / "package.json"
        if not pkg_json.exists():
            logger.info("Initializing npm project...")
            await self.terminal.run("npm init -y", working_dir=project_dir)

        if language == "typescript":
            tsconfig = project_dir / "tsconfig.json"
            if not tsconfig.exists():
                tsconfig_content = {
                    "compilerOptions": {
                        "target": "ES2020",
                        "module": "commonjs",
                        "strict": True,
                        "esModuleInterop": True,
                        "outDir": "./dist",
                        "rootDir": "./src",
                    },
                    "include": ["src/**/*"],
                    "exclude": ["node_modules"],
                }
                tsconfig.write_text(json.dumps(tsconfig_content, indent=2))

    async def _init_go(self, project_dir: Path) -> None:
        """Initialize Go module."""
        go_mod = project_dir / "go.mod"
        if not go_mod.exists():
            project_name = project_dir.name.lower().replace(" ", "_")
            await self.terminal.run(
                f"go mod init {project_name}",
                working_dir=project_dir,
            )

    async def _init_rust(self, project_dir: Path) -> None:
        """Initialize Rust project with Cargo."""
        cargo_toml = project_dir / "Cargo.toml"
        if not cargo_toml.exists():
            logger.info("Initializing Cargo project...")
            await self.terminal.run(
                f"cargo init --name {project_dir.name.replace(' ', '_').replace('-', '_')}",
                working_dir=project_dir,
            )

    async def _install_dependencies(
        self, project_dir: Path, language: str, dependencies: list[str]
    ) -> ExecutionResult:
        """Install project dependencies."""
        if not dependencies:
            return ExecutionResult(status=ExecutionStatus.SUCCESS)

        logger.info(f"Installing {len(dependencies)} dependencies for {language}")

        if language == "python":
            deps_str = " ".join(dependencies)
            req_file = project_dir / "requirements.txt"
            if req_file.exists():
                return await self.terminal.run(
                    f"pip install -r requirements.txt",
                    working_dir=project_dir,
                    timeout=300,
                )
            return await self.terminal.run(
                f"pip install {deps_str}",
                working_dir=project_dir,
                timeout=300,
            )

        elif language in ("javascript", "typescript"):
            deps_str = " ".join(dependencies)
            return await self.terminal.run(
                f"npm install {deps_str}",
                working_dir=project_dir,
                timeout=300,
            )

        elif language == "go":
            results_ok = True
            for dep in dependencies:
                r = await self.terminal.run(f"go get {dep}", working_dir=project_dir, timeout=120)
                if r.return_code != 0:
                    results_ok = False
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS if results_ok else ExecutionStatus.ERROR
            )

        elif language == "rust":
            for dep in dependencies:
                await self.terminal.run(f"cargo add {dep}", working_dir=project_dir, timeout=120)
            return ExecutionResult(status=ExecutionStatus.SUCCESS)

        return ExecutionResult(
            status=ExecutionStatus.ERROR,
            stderr=f"No dependency manager for {language}",
        )

    async def detect_dependencies(self, project_dir: Path, language: str) -> list[str]:
        """Auto-detect required dependencies from project files."""
        deps = []

        if language == "python":
            req_files = ["requirements.txt", "requirements-dev.txt", "Pipfile", "pyproject.toml"]
            for rf in req_files:
                rf_path = project_dir / rf
                if rf_path.exists():
                    content = rf_path.read_text()
                    # Extract package names
                    for line in content.splitlines():
                        line = line.strip()
                        if line and not line.startswith(("#", "-", "[")):
                            pkg = re.split(r"[>=<!\[]", line)[0].strip()
                            if pkg:
                                deps.append(pkg)
                    break

        elif language in ("javascript", "typescript"):
            pkg_json = project_dir / "package.json"
            if pkg_json.exists():
                data = json.loads(pkg_json.read_text())
                deps.extend(data.get("dependencies", {}).keys())
                deps.extend(data.get("devDependencies", {}).keys())

        return deps

    async def create_dockerfile(self, project_dir: Path, language: str, entry_point: str = None) -> str:
        """Generate an appropriate Dockerfile for the project."""
        templates = {
            "python": f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true
COPY . .
{"CMD [\"python3\", \"" + entry_point + "\"]" if entry_point else "CMD [\"python3\", \"main.py\"]"}
""",
            "javascript": f"""FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
{"CMD [\"node\", \"" + entry_point + "\"]" if entry_point else "CMD [\"node\", \"index.js\"]"}
""",
            "go": f"""FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o main .
FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/main .
CMD ["./main"]
""",
        }

        dockerfile_content = templates.get(language, f"""FROM ubuntu:22.04
WORKDIR /app
COPY . .
""")
        dockerfile_path = project_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        return dockerfile_content
