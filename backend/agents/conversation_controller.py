"""
ConversationController — converts chat messages into structured engineering tasks.

Responsibilities:
  1. classify_intent   — decide whether a message is a NEW project or an INCREMENTAL EDIT
  2. extract_tasks     — convert natural language → ordered list of typed action dicts
  3. identify_affected_files — for modifications, determine which workspace files are impacted
  4. generate_modification_plan — produce a patch-level step sequence for follow-up edits

The controller keeps lightweight per-project state so that follow-up messages stay
contextually aware of the project already built.
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ActionItem:
    """A single structured engineering action derived from conversation."""
    type: str          # "architecture_design" | "code_generation" | "testing" | "modification" | "execution"
    target: str = ""   # e.g. "backend API (FastAPI)" or "frontend/src/styles/globals.css"
    goal: str = ""     # human-readable goal
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationPlan:
    """Output of the ConversationController for a single user message."""
    intent: str                        # "new_project" | "modification" | "clarification"
    project_id: str = ""
    summary: str = ""                  # one-sentence summary of what will be done
    actions: List[ActionItem] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)  # only for modifications
    task_title: str = ""
    task_description: str = ""         # full description to hand to the Planner


@dataclass
class ProjectState:
    """Lightweight project context kept in memory between conversation turns."""
    project_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    files: List[str] = field(default_factory=list)   # relative paths written so far
    tech_stack: List[str] = field(default_factory=list)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    last_task_id: Optional[str] = None


# ---------------------------------------------------------------------------
# ConversationController
# ---------------------------------------------------------------------------

class ConversationController:
    """
    Converts natural language chat messages into deterministic engineering action plans.

    Usage:
        cc = ConversationController()
        plan = await cc.process_message("Build a SaaS task manager with auth")
        # → ConversationPlan(intent="new_project", actions=[...])

        plan2 = await cc.process_message("make the UI dark mode", project_id=plan.project_id)
        # → ConversationPlan(intent="modification", affected_files=["frontend/..."], actions=[...])
    """

    name = "conversation_controller"

    # Keywords that signal the user wants an incremental edit rather than a new project
    MODIFICATION_KEYWORDS = [
        "make", "change", "update", "add", "remove", "fix", "refactor", "improve",
        "modify", "edit", "adjust", "replace", "rename", "move", "delete",
        "dark mode", "more modern", "prettier", "cleaner", "faster", "optimise", "optimize",
        "priority", "analytics", "dashboard", "feature", "endpoint", "route",
    ]

    NEW_PROJECT_KEYWORDS = [
        "build", "create", "generate", "write", "implement", "develop",
        "set up", "scaffold", "start", "initialize", "init", "new project",
    ]

    def __init__(self) -> None:
        # project_id → ProjectState  (in-memory; persists for the life of the process)
        self._projects: Dict[str, ProjectState] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_message(
        self,
        message: str,
        project_id: Optional[str] = None,
        workspace_files: Optional[List[str]] = None,
    ) -> ConversationPlan:
        """
        Main entry point.  Returns a ConversationPlan describing what to do next.

        Args:
            message:         The raw user chat message.
            project_id:      If provided, treat this as a follow-up for an existing project.
            workspace_files: Currently generated files in the workspace (for modification planning).
        """
        # Resolve or create project state
        if project_id and project_id in self._projects:
            state = self._projects[project_id]
        else:
            state = ProjectState()
            self._projects[state.project_id] = state

        if workspace_files:
            state.files = workspace_files

        # Append user turn to conversation history
        state.conversation_history.append({"role": "user", "content": message})

        # Determine intent
        intent = self._classify_intent(message, state)

        # Build the plan
        if intent == "new_project":
            plan = await self._plan_new_project(message, state)
        elif intent == "modification":
            plan = await self._plan_modification(message, state)
        else:
            # clarification — ask the LLM or return a minimal plan
            plan = ConversationPlan(
                intent="clarification",
                project_id=state.project_id,
                summary="Please clarify your request.",
                task_title="Clarification needed",
                task_description=message,
            )

        plan.project_id = state.project_id

        # Append assistant response to history
        state.conversation_history.append({
            "role": "assistant",
            "content": plan.summary,
        })

        logger.info(
            f"ConversationController: intent={intent}, project={state.project_id}, "
            f"actions={len(plan.actions)}"
        )
        return plan

    def get_project(self, project_id: str) -> Optional[ProjectState]:
        return self._projects.get(project_id)

    def update_project_files(self, project_id: str, files: List[str]) -> None:
        """Called by the orchestrator after code generation to keep state in sync."""
        state = self._projects.get(project_id)
        if state:
            state.files = files

    def update_last_task(self, project_id: str, task_id: str) -> None:
        state = self._projects.get(project_id)
        if state:
            state.last_task_id = task_id

    # ------------------------------------------------------------------
    # Intent classification
    # ------------------------------------------------------------------

    def _classify_intent(self, message: str, state: ProjectState) -> str:
        msg_lower = message.lower()

        # If there's no existing project context, it must be new
        has_context = bool(state.files or state.description)

        has_modification_kw = any(kw in msg_lower for kw in self.MODIFICATION_KEYWORDS)
        has_new_project_kw = any(kw in msg_lower for kw in self.NEW_PROJECT_KEYWORDS)

        if has_context and has_modification_kw and not has_new_project_kw:
            return "modification"

        if has_new_project_kw or not has_context:
            return "new_project"

        # Ambiguous — treat as modification if we have context, else new
        if has_context:
            return "modification"
        return "new_project"

    # ------------------------------------------------------------------
    # New project planning
    # ------------------------------------------------------------------

    async def _plan_new_project(self, message: str, state: ProjectState) -> ConversationPlan:
        state.description = message

        if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
            try:
                return await self._llm_plan_new_project(message, state)
            except Exception as exc:
                logger.warning(f"LLM planning failed, using rule-based fallback: {exc}")

        return self._rule_based_new_project(message, state)

    async def _llm_plan_new_project(self, message: str, state: ProjectState) -> ConversationPlan:
        prompt = f"""You are a principal software architect.
A user wants to build this project: "{message}"

Produce a JSON object with:
{{
  "summary": "one-sentence summary of what will be built",
  "task_title": "short title (≤60 chars)",
  "task_description": "full engineering description for the dev team (≤300 chars)",
  "tech_stack": ["list", "of", "technologies"],
  "actions": [
    {{
      "type": "architecture_design|code_generation|testing|execution",
      "target": "what is being designed/coded/tested",
      "goal": "what this action achieves"
    }}
  ]
}}

Rules:
- Maximum 8 actions
- Prefer FastAPI (backend) + Next.js (frontend) unless user specifies otherwise
- Always include architecture_design first, then code_generation steps, then testing
- Return ONLY valid JSON, no explanation"""

        raw = await self._call_llm(prompt)
        data = self._safe_json(raw, {})

        actions = [
            ActionItem(
                type=a.get("type", "code_generation"),
                target=a.get("target", ""),
                goal=a.get("goal", ""),
            )
            for a in data.get("actions", [])
        ]

        if data.get("tech_stack"):
            state.tech_stack = data["tech_stack"]

        return ConversationPlan(
            intent="new_project",
            summary=data.get("summary", f"Building: {message[:80]}"),
            actions=actions,
            task_title=data.get("task_title", message[:60]),
            task_description=data.get("task_description", message),
        )

    def _rule_based_new_project(self, message: str, state: ProjectState) -> ConversationPlan:
        msg_lower = message.lower()

        # Detect stack hints
        has_auth = any(kw in msg_lower for kw in ["auth", "login", "signup", "jwt"])
        has_db = any(kw in msg_lower for kw in ["database", "db", "postgres", "sqlite", "mongo"])
        has_frontend = any(kw in msg_lower for kw in ["ui", "dashboard", "frontend", "react", "next"])

        actions: List[ActionItem] = [
            ActionItem(
                type="architecture_design",
                goal="Define full stack structure, API contracts, and database schema",
            ),
            ActionItem(
                type="code_generation",
                target="backend API (FastAPI)",
                goal="Implement backend with CRUD endpoints and business logic",
            ),
        ]

        if has_auth:
            actions.append(ActionItem(
                type="code_generation",
                target="authentication system",
                goal="Implement JWT-based login and signup",
            ))

        if has_db:
            actions.append(ActionItem(
                type="code_generation",
                target="database models",
                goal="Set up SQLite/Postgres schema with ORM",
            ))

        if has_frontend:
            actions.append(ActionItem(
                type="code_generation",
                target="frontend UI (Next.js)",
                goal="Build responsive dashboard with Tailwind CSS",
            ))

        actions.append(ActionItem(
            type="testing",
            goal="Generate and run backend unit + API tests with pytest",
        ))

        actions.append(ActionItem(
            type="execution",
            goal="Start backend server and verify all endpoints respond",
        ))

        state.tech_stack = ["FastAPI", "Python", "SQLite"]
        if has_frontend:
            state.tech_stack += ["Next.js", "Tailwind CSS"]

        return ConversationPlan(
            intent="new_project",
            summary=f"Building: {message[:80]}",
            actions=actions,
            task_title=message[:60],
            task_description=message,
        )

    # ------------------------------------------------------------------
    # Modification planning
    # ------------------------------------------------------------------

    async def _plan_modification(self, message: str, state: ProjectState) -> ConversationPlan:
        affected = self._identify_affected_files(message, state.files)

        if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
            try:
                return await self._llm_plan_modification(message, state, affected)
            except Exception as exc:
                logger.warning(f"LLM modification planning failed: {exc}")

        return self._rule_based_modification(message, state, affected)

    def _identify_affected_files(self, message: str, files: List[str]) -> List[str]:
        """Return the subset of workspace files most likely to be touched by this change."""
        msg_lower = message.lower()
        affected: List[str] = []

        frontend_kws = ["ui", "dark mode", "modern", "style", "css", "frontend", "dashboard", "page", "component"]
        backend_kws = ["api", "endpoint", "route", "backend", "server", "model", "database", "auth"]
        test_kws = ["test", "spec", "coverage"]

        for path in files:
            path_lower = path.lower()
            if any(kw in msg_lower for kw in frontend_kws) and any(
                seg in path_lower for seg in ["frontend", "component", "page", "style", "css", "tsx", "jsx"]
            ):
                affected.append(path)
            elif any(kw in msg_lower for kw in backend_kws) and any(
                seg in path_lower for seg in ["backend", "api", "route", "model", "main.py", "app.py"]
            ):
                affected.append(path)
            elif any(kw in msg_lower for kw in test_kws) and any(
                seg in path_lower for seg in ["test", "spec"]
            ):
                affected.append(path)

        # Fallback: return all files if nothing matched
        return affected or files[:5]

    async def _llm_plan_modification(
        self, message: str, state: ProjectState, affected: List[str]
    ) -> ConversationPlan:
        history_text = "\n".join(
            f"{t['role'].upper()}: {t['content']}"
            for t in state.conversation_history[-6:]
        )
        files_text = "\n".join(f"- {f}" for f in state.files[:20]) if state.files else "(none yet)"

        prompt = f"""You are a senior engineer performing an incremental code modification.

Conversation history:
{history_text}

User request: "{message}"

Workspace files:
{files_text}

Produce a JSON object:
{{
  "summary": "one-sentence summary of the change",
  "affected_files": ["list of files that need changing"],
  "actions": [
    {{
      "type": "modification",
      "target": "file path or component name",
      "goal": "what specifically changes in this file"
    }}
  ]
}}

Rules:
- Maximum 5 actions
- Only modify affected files — do NOT rebuild the whole project
- Re-run tests only for affected modules
- Return ONLY valid JSON"""

        raw = await self._call_llm(prompt)
        data = self._safe_json(raw, {})

        actions = [
            ActionItem(
                type=a.get("type", "modification"),
                target=a.get("target", ""),
                goal=a.get("goal", ""),
            )
            for a in data.get("actions", [])
        ]

        return ConversationPlan(
            intent="modification",
            summary=data.get("summary", f"Applying: {message[:80]}"),
            actions=actions,
            affected_files=data.get("affected_files", affected),
            task_title=f"Modify: {message[:50]}",
            task_description=(
                f"Incremental modification to existing project.\n"
                f"Change requested: {message}\n"
                f"Affected files: {', '.join(data.get('affected_files', affected)[:5])}\n"
                f"Original project: {state.description[:200]}"
            ),
        )

    def _rule_based_modification(
        self, message: str, state: ProjectState, affected: List[str]
    ) -> ConversationPlan:
        msg_lower = message.lower()

        actions: List[ActionItem] = []
        for path in affected[:5]:
            actions.append(ActionItem(
                type="modification",
                target=path,
                goal=f"Apply change: {message[:100]}",
            ))

        # Always add a test step for the modified module
        if affected:
            actions.append(ActionItem(
                type="testing",
                target=", ".join(affected[:3]),
                goal="Re-run tests for modified files only",
            ))

        return ConversationPlan(
            intent="modification",
            summary=f"Applying incremental change: {message[:80]}",
            actions=actions,
            affected_files=affected,
            task_title=f"Modify: {message[:50]}",
            task_description=(
                f"Incremental modification to existing project.\n"
                f"Change requested: {message}\n"
                f"Affected files: {', '.join(affected[:5])}\n"
                f"Original project: {state.description[:200]}"
            ),
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _call_llm(self, prompt: str) -> str:
        if settings.MODEL_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            msg = await client.messages.create(
                model=settings.DEFAULT_MODEL or "claude-3-opus-20240229",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        elif settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=settings.DEFAULT_MODEL or "gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
            )
            return response.choices[0].message.content or ""
        raise ValueError("No LLM API key configured")

    @staticmethod
    def _safe_json(raw: str, default: Any) -> Any:
        """Parse JSON from LLM output, tolerating markdown fences."""
        try:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception:
            pass
        return default


# Module-level singleton
conversation_controller = ConversationController()
