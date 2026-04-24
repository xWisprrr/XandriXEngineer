"""Tests for ConversationController."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
import pytest_asyncio

from agents.conversation_controller import (
    ConversationController,
    ConversationPlan,
    ProjectState,
    ActionItem,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cc() -> ConversationController:
    return ConversationController()


@pytest.fixture
def project_with_files(cc: ConversationController) -> ProjectState:
    """A pre-populated project state simulating files already generated."""
    import asyncio
    # Seed state manually
    state = ProjectState(
        description="Build a SaaS task manager with authentication",
        tech_stack=["FastAPI", "Next.js", "SQLite"],
        files=[
            "backend/main.py",
            "backend/models.py",
            "frontend/src/app/page.tsx",
            "frontend/src/components/Dashboard.tsx",
            "frontend/src/styles/globals.css",
            "tests/test_api.py",
        ],
    )
    cc._projects[state.project_id] = state
    return state


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

def test_classify_new_project_keywords(cc: ConversationController):
    state = ProjectState()
    assert cc._classify_intent("build a todo app", state) == "new_project"
    assert cc._classify_intent("create a REST API", state) == "new_project"
    assert cc._classify_intent("generate a FastAPI backend", state) == "new_project"


def test_classify_new_project_no_context(cc: ConversationController):
    """Without any existing project context, any message should map to new_project."""
    state = ProjectState()
    assert cc._classify_intent("add dark mode", state) == "new_project"


def test_classify_modification_with_context(cc: ConversationController, project_with_files):
    intent = cc._classify_intent("make the UI dark mode and more modern", project_with_files)
    assert intent == "modification"


def test_classify_modification_various_keywords(cc: ConversationController, project_with_files):
    modification_msgs = [
        "add task priority levels",
        "refactor backend structure",
        "update the login page",
        "fix the authentication bug",
        "remove the old endpoint",
    ]
    for msg in modification_msgs:
        intent = cc._classify_intent(msg, project_with_files)
        assert intent == "modification", f"Expected modification for: {msg!r}"


# ---------------------------------------------------------------------------
# Affected file identification
# ---------------------------------------------------------------------------

def test_identify_affected_frontend_files(cc: ConversationController, project_with_files):
    affected = cc._identify_affected_files(
        "make the dashboard dark mode",
        project_with_files.files,
    )
    # Should include frontend files, not backend files
    assert any("frontend" in f or "Dashboard" in f for f in affected)


def test_identify_affected_backend_files(cc: ConversationController, project_with_files):
    affected = cc._identify_affected_files(
        "add a new API endpoint for analytics",
        project_with_files.files,
    )
    assert any("backend" in f or "main" in f for f in affected)


def test_identify_affected_test_files(cc: ConversationController, project_with_files):
    affected = cc._identify_affected_files(
        "update the test coverage",
        project_with_files.files,
    )
    assert any("test" in f for f in affected)


def test_identify_affected_fallback(cc: ConversationController, project_with_files):
    """When no keyword matches, fallback returns at most the first 5 files."""
    affected = cc._identify_affected_files("xyzzy something unknown", project_with_files.files)
    assert len(affected) <= 5
    assert len(affected) > 0


# ---------------------------------------------------------------------------
# Rule-based planning — new project
# ---------------------------------------------------------------------------

def test_rule_based_new_project_basic(cc: ConversationController):
    state = ProjectState()
    plan = cc._rule_based_new_project("build a FastAPI todo API with tests", state)
    assert plan.intent == "new_project"
    assert len(plan.actions) >= 2
    types = [a.type for a in plan.actions]
    assert "architecture_design" in types
    assert "code_generation" in types
    assert plan.task_title != ""
    assert plan.task_description != ""


def test_rule_based_new_project_with_auth(cc: ConversationController):
    state = ProjectState()
    plan = cc._rule_based_new_project("build a SaaS app with JWT authentication and a dashboard UI", state)
    targets = " ".join(a.target for a in plan.actions)
    assert "auth" in targets.lower()
    assert any("frontend" in a.target.lower() or "ui" in a.target.lower() or "Next" in a.target for a in plan.actions)


def test_rule_based_new_project_includes_testing(cc: ConversationController):
    state = ProjectState()
    plan = cc._rule_based_new_project("create a REST API", state)
    types = [a.type for a in plan.actions]
    assert "testing" in types


def test_rule_based_new_project_tech_stack_set(cc: ConversationController):
    state = ProjectState()
    cc._rule_based_new_project("build a web app with UI", state)
    assert "FastAPI" in state.tech_stack


# ---------------------------------------------------------------------------
# Rule-based planning — modification
# ---------------------------------------------------------------------------

def test_rule_based_modification(cc: ConversationController, project_with_files):
    affected = ["frontend/src/styles/globals.css", "frontend/src/components/Dashboard.tsx"]
    plan = cc._rule_based_modification("make the UI dark mode", project_with_files, affected)
    assert plan.intent == "modification"
    assert len(plan.actions) >= 1
    targets = [a.target for a in plan.actions if a.type == "modification"]
    assert any("frontend" in t or "Dashboard" in t for t in targets)
    # Should also include a testing action
    types = [a.type for a in plan.actions]
    assert "testing" in types


# ---------------------------------------------------------------------------
# process_message integration (no LLM)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_message_new_project(cc: ConversationController):
    plan = await cc.process_message("build a FastAPI todo API")
    assert isinstance(plan, ConversationPlan)
    assert plan.intent == "new_project"
    assert plan.project_id != ""
    assert len(plan.actions) >= 1
    assert plan.task_title != ""


@pytest.mark.asyncio
async def test_process_message_creates_project_state(cc: ConversationController):
    plan = await cc.process_message("build a todo app")
    state = cc.get_project(plan.project_id)
    assert state is not None
    assert "todo" in state.description.lower()


@pytest.mark.asyncio
async def test_process_message_conversation_history(cc: ConversationController):
    plan = await cc.process_message("build a todo app")
    state = cc.get_project(plan.project_id)
    assert len(state.conversation_history) >= 2  # user + assistant
    assert state.conversation_history[0]["role"] == "user"
    assert state.conversation_history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_process_message_modification_follow_up(cc: ConversationController, project_with_files):
    plan = await cc.process_message(
        "make the UI dark mode",
        project_id=project_with_files.project_id,
    )
    assert plan.intent == "modification"
    assert plan.project_id == project_with_files.project_id
    assert len(plan.affected_files) > 0


@pytest.mark.asyncio
async def test_process_message_updates_history(cc: ConversationController):
    plan1 = await cc.process_message("build a REST API")
    await cc.process_message("add authentication", project_id=plan1.project_id)
    state = cc.get_project(plan1.project_id)
    # Should have 4 history entries (user + assistant) × 2 turns
    assert len(state.conversation_history) == 4


# ---------------------------------------------------------------------------
# ProjectState management
# ---------------------------------------------------------------------------

def test_update_project_files(cc: ConversationController):
    state = ProjectState()
    cc._projects[state.project_id] = state
    cc.update_project_files(state.project_id, ["main.py", "tests/test_main.py"])
    assert state.files == ["main.py", "tests/test_main.py"]


def test_update_last_task(cc: ConversationController):
    state = ProjectState()
    cc._projects[state.project_id] = state
    cc.update_last_task(state.project_id, "task-abc")
    assert state.last_task_id == "task-abc"


def test_get_project_nonexistent(cc: ConversationController):
    assert cc.get_project("nonexistent-id") is None


# ---------------------------------------------------------------------------
# JSON parsing helper
# ---------------------------------------------------------------------------

def test_safe_json_valid():
    data = ConversationController._safe_json('{"key": "value"}', {})
    assert data == {"key": "value"}


def test_safe_json_with_fences():
    raw = '```json\n{"key": 42}\n```'
    data = ConversationController._safe_json(raw, {})
    assert data.get("key") == 42


def test_safe_json_invalid():
    data = ConversationController._safe_json("not json at all", {"default": True})
    assert data == {"default": True}


def test_safe_json_embedded():
    raw = 'Here is the result: {"summary": "done", "actions": []}'
    data = ConversationController._safe_json(raw, {})
    assert data.get("summary") == "done"
