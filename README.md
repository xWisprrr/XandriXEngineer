# XandriXEngineer 🤖

**Fully autonomous AI software engineer** — like Devin AI, but open-source, production-ready, and more advanced.

---

## Overview

XandriXEngineer is a multi-agent, autonomous software engineering system that can understand natural language goals, decompose them into actionable steps, generate and execute code, debug failures, and deliver working software — all with minimal human intervention.

```
┌─────────────────────────────────────────────────────────────────┐
│                    XandriXEngineer System                        │
│                                                                  │
│  ┌──────────────────┐    ┌─────────────────────────────────┐    │
│  │  Next.js Dashboard│    │         FastAPI Backend          │    │
│  │                  │◄──►│                                  │    │
│  │ • Task Input     │ WS │  ┌─────────┐  ┌─────────────┐  │    │
│  │ • Exec Logs      │    │  │Planner  │  │   Coder     │  │    │
│  │ • Agent Activity │    │  ├─────────┤  ├─────────────┤  │    │
│  │ • File Explorer  │    │  │Tester   │  │  Debugger   │  │    │
│  │ • Task History   │    │  ├─────────┤  ├─────────────┤  │    │
│  └──────────────────┘    │  │Reviewer │  │Orchestrator │  │    │
│                           │  └─────────┘  └─────────────┘  │    │
│                           │                                  │    │
│                           │  Tools: Terminal │ FileSystem   │    │
│                           │          Git     │ Browser      │    │
│                           │                                  │    │
│                           │  Runtime: Python │ JS/TS │ Go   │    │
│                           │           Rust  │ Java  │ Bash  │    │
│                           │                                  │    │
│                           │  Memory: ShortTerm │ ChromaDB   │    │
│                           └─────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Capabilities
- **Natural language task understanding** — describe what you want in plain English
- **Intelligent task decomposition** — planner agent breaks goals into executable steps
- **Autonomous code generation** — multi-language code generation (8+ languages)
- **Self-debugging** — automatically detects and fixes errors, retries with new strategies
- **Real-time execution** — terminal execution with live output streaming
- **Context retention** — short-term + long-term vector memory across sessions

### Multi-Agent Architecture
| Agent | Role |
|-------|------|
| **Planner** | Decomposes tasks into ordered steps |
| **Coder** | Generates, edits, and optimizes code |
| **Tester** | Creates and runs automated tests |
| **Debugger** | Analyzes errors and proposes fixes |
| **Reviewer** | Self-critiques output quality |
| **Orchestrator** | Routes tasks, manages parallelism |

### Multi-Language Support
Python · JavaScript · TypeScript · Go · Rust · Java · C · C++ · Bash · SQL

### Environment Provisioning
- Detects required runtimes automatically
- Installs missing compilers/interpreters
- Manages package managers: `pip`, `npm`, `cargo`, `go mod`, `maven`
- Sets up virtual environments and per-project isolation
- Docker container execution support

### Dashboard (Web UI)
- Task input panel with model/priority selectors
- Terminal-style real-time execution logs (color-coded)
- Per-agent status with activity indicators
- Workspace file explorer with syntax-highlighted preview
- Task history with start/stop/pause controls
- WebSocket-based live updates

### Advanced Features
- **Parallel step execution** for independent subtasks
- **Exponential backoff retry** system
- **Vector memory** via ChromaDB (with JSON fallback)
- **Git integration** with automatic meaningful commits
- **Structured JSON logging** with observability
- **SSE log streaming** endpoint
- **Docker Compose** for one-command deployment
- **OpenAI / Anthropic / rule-based fallback** LLM support

---

## Project Structure

```
XandriXEngineer/
├── backend/                    # Python FastAPI backend
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration (env-based)
│   ├── agents/                 # Multi-agent system
│   │   ├── orchestrator.py     # Agent coordination
│   │   ├── planner.py          # Task decomposition
│   │   ├── coder.py            # Code generation
│   │   ├── tester.py           # Test generation & execution
│   │   ├── debugger.py         # Error analysis & fixing
│   │   └── reviewer.py         # Self-critique & review
│   ├── core/
│   │   ├── agent_loop.py       # Main execution loop
│   │   ├── task_queue.py       # Task lifecycle management
│   │   └── event_bus.py        # Async pub/sub events
│   ├── tools/
│   │   ├── terminal.py         # Shell/code execution
│   │   ├── filesystem.py       # File operations
│   │   ├── browser.py          # Web browsing & docs
│   │   ├── git_tool.py         # Git operations
│   │   └── registry.py         # Tool registry
│   ├── runtime/
│   │   ├── manager.py          # Multi-language runtime
│   │   └── provisioner.py      # Env provisioning
│   ├── memory/
│   │   ├── short_term.py       # In-memory context
│   │   └── long_term.py        # ChromaDB vector store
│   ├── api/
│   │   ├── websocket.py        # WebSocket manager
│   │   └── routes/             # REST API endpoints
│   └── utils/
│       ├── logger.py           # Structured logging
│       └── retry.py            # Retry with backoff
├── frontend/                   # Next.js 14 + TailwindCSS
│   └── src/
│       ├── app/                # App router
│       ├── components/         # Dashboard UI components
│       └── lib/                # API & WebSocket clients
├── tests/                      # pytest test suite (34 tests)
├── docker-compose.yml
└── README.md
```

---

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
git clone https://github.com/xWisprrr/XandriXEngineer
cd XandriXEngineer

# Optional: set LLM API keys
cp .env.example .env
# Edit .env: OPENAI_API_KEY=sk-... or ANTHROPIC_API_KEY=...

docker-compose up
```

- **Dashboard**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Option 2: Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt

# Optional LLM keys (system works without them using rule-based fallback)
export OPENAI_API_KEY=sk-...        # Optional
export ANTHROPIC_API_KEY=sk-ant-... # Optional
export MODEL_PROVIDER=openai        # openai | anthropic (default: openai)

python main.py
# Server running at http://localhost:8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# Dashboard at http://localhost:3000
```

**Tests:**
```bash
# From repo root
pytest tests/ -v
# 34 tests, all passing
```

---

## Configuration

All configuration is via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | `` | OpenAI API key |
| `ANTHROPIC_API_KEY` | `` | Anthropic API key |
| `MODEL_PROVIDER` | `openai` | `openai` or `anthropic` |
| `DEFAULT_MODEL` | `gpt-4o` | Model to use |
| `WORKSPACE_DIR` | `./workspace` | Where agent creates files |
| `MAX_RETRIES` | `3` | Retry attempts per step |
| `MAX_CONCURRENT_TASKS` | `5` | Parallel task limit |
| `TASK_TIMEOUT` | `300` | Seconds before task timeout |
| `LOG_LEVEL` | `INFO` | `DEBUG\|INFO\|WARNING\|ERROR` |

> **No API key?** The system uses intelligent rule-based fallback for planning and code generation — it still works, just without LLM power.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/tasks` | Create & start a new task |
| `GET` | `/api/tasks` | List all tasks |
| `GET` | `/api/tasks/{id}` | Get task details |
| `POST` | `/api/tasks/{id}/pause` | Pause task |
| `POST` | `/api/tasks/{id}/resume` | Resume task |
| `POST` | `/api/tasks/{id}/stop` | Stop task |
| `GET` | `/api/agents` | List agent statuses |
| `GET` | `/api/files` | List workspace files |
| `GET` | `/api/files/content` | Get file content |
| `POST` | `/api/files` | Create/update file |
| `GET` | `/api/logs` | Get system logs |
| `GET` | `/api/logs/stream` | SSE log stream |
| `WS` | `/ws/{client_id}` | Real-time WebSocket |
| `GET` | `/health` | Health check |

---

## Example Task

```
Goal: "Create a REST API in Python with FastAPI that has CRUD endpoints for a todo list, including tests"

Steps generated by Planner:
  1. [setup]  Create project directory structure
  2. [code]   Generate FastAPI app with Todo model and CRUD routes
  3. [code]   Generate Pydantic schemas for request/response
  4. [test]   Generate pytest tests for all endpoints
  5. [exec]   Install dependencies (fastapi, uvicorn, pytest, httpx)
  6. [exec]   Run tests and verify they pass
  7. [debug]  Fix any failing tests automatically
  8. [review] Review code quality and suggest improvements
  9. [git]    Commit working implementation
```

---

## Architecture

```
User Input (NL Goal)
       │
       ▼
  TaskQueue.add_task()
       │
       ▼
  AgentLoop (background)
       │
       ▼
  PlannerAgent.analyze_task()  ──► List[Step]
       │
       ▼
  Orchestrator.execute_step()  ──► (parallel for independent steps)
       │
   ┌───┴───────────────────────────────┐
   │                                   │
   ▼                                   ▼
CoderAgent               TesterAgent / DebuggerAgent
   │                                   │
   ▼                                   ▼
ToolRegistry ──► Terminal / FileSystem / Git / Browser
   │
   ▼
RuntimeManager ──► Python / JS / Go / Rust / Java / ...
   │
   ▼
EventBus.publish() ──► WebSocket ──► Dashboard
   │
   ▼
Memory.store() ──► ShortTerm + ChromaDB (LongTerm)
```

---

## License

MIT — open source, free to use and modify.

