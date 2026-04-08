# XandriX Engineer 🤖

**A fully autonomous AI software engineering system** — more advanced, more reliable, and open-source.

XandriX Engineer is an end-to-end autonomous coding agent that plans, writes, executes, tests, and debugs code across multiple programming languages with minimal human intervention. It features a real-time web dashboard for monitoring and control.

---

## 🌟 Features

### Core Capabilities
- **Natural Language Task Understanding** — Describe what you want, XandriX figures out how to build it
- **Intelligent Task Decomposition** — Automatically breaks goals into atomic executable steps
- **Autonomous Code Generation** — Writes production-quality code with error handling and best practices
- **Multi-Language Support** — Python, JavaScript, TypeScript, Go, Rust, Java, C/C++, Bash, SQL
- **Automatic Environment Provisioning** — Sets up runtimes, installs deps, configures projects
- **Code Execution & Output Interpretation** — Runs code and understands results
- **Automatic Debugging & Retry** — Detects errors, analyzes root causes, applies fixes
- **Iterative Refinement** — Loops until task is complete or max iterations reached
- **Git Integration** — Commits progress with meaningful messages at each step
- **Persistent Memory** — Short-term task context + long-term SQLite-backed memory
- **Self-Critique** — Evaluates its own output quality after completion

### Multi-Agent Architecture
| Agent | Role |
|-------|------|
| 🗺️ **Planner** | Analyzes requirements, makes architectural decisions |
| 💻 **Coder** | Writes and modifies code files |
| 🧪 **Tester** | Writes and runs tests, validates outputs |
| 🔍 **Debugger** | Diagnoses errors and applies fixes |
| ⚙️ **DevOps** | Sets up environments, installs dependencies |

### Control Dashboard
- Real-time execution log (terminal-style)
- Agent activity viewer with step-by-step progress
- File explorer + live code preview
- Task history and status tracking
- Start / Stop / Pause / Resume / Retry controls
- Built-in chat interface with the agent

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        XandriX Engineer                             │
│                                                                     │
│  ┌─────────────┐    ┌─────────────────────────────────────────┐    │
│  │   Frontend  │    │              Backend                    │    │
│  │  (React/TS) │◄──►│                                         │    │
│  │             │    │  ┌─────────────────────────────────┐   │    │
│  │ ┌─────────┐ │    │  │         Agent Loop              │   │    │
│  │ │Dashboard│ │    │  │  ┌─────────┐  ┌─────────────┐  │   │    │
│  │ │  TaskIO │ │    │  │  │ Planner │  │ Task Store  │  │   │    │
│  │ │  Logs   │ │    │  │  └────┬────┘  └─────────────┘  │   │    │
│  │ │ Agents  │ │    │  │       │                         │   │    │
│  │ │  Files  │ │    │  │  ┌────▼───────────────────┐    │   │    │
│  │ │  Chat   │ │    │  │  │    Agent Orchestrator   │    │   │    │
│  │ └─────────┘ │    │  │  │  Planner | Coder |      │    │   │    │
│  └─────────────┘    │  │  │  Tester | Debugger |    │    │   │    │
│                     │  │  │  DevOps                 │    │   │    │
│                     │  │  └────────────┬────────────┘    │   │    │
│                     │  └──────────────┼─────────────────┘   │    │
│                     │                 │                       │    │
│                     │  ┌──────────────▼─────────────────┐   │    │
│                     │  │          Tool Layer             │   │    │
│                     │  │  Terminal | FS | Git | Browser  │   │    │
│                     │  └──────────────┬─────────────────┘   │    │
│                     │                 │                       │    │
│                     │  ┌──────────────▼─────────────────┐   │    │
│                     │  │       Runtime Manager           │   │    │
│                     │  │  Python|JS|Go|Rust|Java|C/C++  │   │    │
│                     │  └─────────────────────────────────┘   │    │
│                     │                                         │    │
│                     │  ┌───────────┐  ┌────────────────────┐ │    │
│                     │  │  Memory   │  │  LLM Client        │ │    │
│                     │  │ ST + LT   │  │ OpenAI|Anthropic   │ │    │
│                     │  │ (SQLite)  │  │ Ollama|Groq        │ │    │
│                     │  └───────────┘  └────────────────────┘ │    │
│                     └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
XandriXEngineer/
├── backend/
│   ├── agents/
│   │   ├── base_agent.py          # Abstract agent base class
│   │   ├── planner_agent.py       # Requirement analysis
│   │   ├── coder_agent.py         # Code generation
│   │   ├── tester_agent.py        # Test writing & execution
│   │   ├── debugger_agent.py      # Error analysis & fixing
│   │   └── devops_agent.py        # Environment provisioning
│   ├── api/
│   │   └── main.py                # FastAPI app + WebSocket
│   ├── core/
│   │   ├── agent_loop.py          # Main orchestration loop
│   │   ├── task_planner.py        # LLM-powered task planner
│   │   ├── task_store.py          # SQLite task persistence
│   │   ├── memory_system.py       # Short + long-term memory
│   │   ├── llm_client.py          # Multi-provider LLM client
│   │   └── logger.py              # Structured logger
│   ├── runtime/
│   │   ├── runtime_manager.py     # Multi-language execution
│   │   └── environment_provisioner.py  # Auto environment setup
│   ├── tools/
│   │   ├── terminal.py            # Async shell execution
│   │   ├── filesystem.py          # File system operations
│   │   ├── web_browser.py         # Web fetch + search
│   │   └── git_tool.py            # Git operations
│   ├── models/
│   │   └── schemas.py             # Pydantic data models
│   ├── config.py                  # Central configuration
│   ├── main.py                    # Entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AgentActivity.tsx  # Step-by-step agent view
│   │   │   ├── ChatPanel.tsx      # Chat interface
│   │   │   ├── ExecutionLog.tsx   # Terminal log output
│   │   │   ├── FileExplorer.tsx   # Project file tree
│   │   │   ├── StatusBadge.tsx    # Task status indicator
│   │   │   ├── TaskHistory.tsx    # Past task list
│   │   │   └── TaskInput.tsx      # New task form
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts    # WebSocket hook
│   │   ├── pages/
│   │   │   └── Dashboard.tsx      # Main dashboard
│   │   ├── utils/
│   │   │   └── api.ts             # API client + types
│   │   ├── styles/
│   │   │   └── global.css         # Global styles
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- An LLM API key (OpenAI, Anthropic, Groq) **or** Ollama running locally

### 1. Clone & Configure

```bash
git clone https://github.com/xWisprrr/XandriXEngineer.git
cd XandriXEngineer

# Configure environment
cp .env.example .env
# Edit .env and add your LLM_API_KEY
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the backend (from repo root)
cd ..
python -m backend.main
# Backend runs at http://localhost:8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
# Dashboard available at http://localhost:3000
```

### 4. Using Docker (Production)

```bash
# Set your API key in .env, then:
docker-compose up --build

# Dashboard: http://localhost:3000
# API: http://localhost:8000
```

---

## 🔧 Configuration

Edit `.env` to configure XandriX Engineer:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | LLM provider: `openai`, `anthropic`, `ollama`, `groq` |
| `LLM_MODEL` | `gpt-4o` | Model to use (e.g., `gpt-4o`, `claude-3-5-sonnet`, `llama3.2`) |
| `LLM_API_KEY` | — | Your API key |
| `LLM_BASE_URL` | — | Custom API endpoint (for Ollama: `http://localhost:11434`) |
| `MAX_ITERATIONS` | `50` | Max agent loop iterations per task |
| `MAX_RETRIES` | `5` | Max retries per failing step |
| `AGENT_TIMEOUT` | `300` | Timeout per agent step (seconds) |

### Using Ollama (Local LLM)

```bash
# Install and start Ollama
ollama pull llama3.2

# Set in .env:
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
LLM_BASE_URL=http://localhost:11434
LLM_API_KEY=  # leave empty
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/tasks` | Create and start a task |
| `GET` | `/api/tasks` | List all tasks |
| `GET` | `/api/tasks/{id}` | Get task details |
| `DELETE` | `/api/tasks/{id}` | Delete a task |
| `POST` | `/api/tasks/{id}/control` | Control task: `start/stop/pause/resume/retry` |
| `GET` | `/api/tasks/{id}/files` | Get project file tree |
| `GET` | `/api/tasks/{id}/files/content?path=` | Read file content |
| `POST` | `/api/chat` | Chat with the agent |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/system/info` | System configuration |
| `WS` | `/ws` | Global WebSocket (logs + events) |
| `WS` | `/ws/{task_id}` | Task-specific WebSocket |

---

## 💡 Example Task Execution

Here's what happens when you submit: *"Build a REST API in Python with FastAPI that manages a todo list"*

```
[PLANNER] Analyzing requirements...
[PLANNER] Plan generated: 8 steps

Step 1/8 [DEVOPS]  → Setup Python environment
Step 2/8 [PLANNER] → Analyze requirements and design API
Step 3/8 [CODER]   → Create FastAPI application with Todo models
Step 4/8 [CODER]   → Implement CRUD endpoints
Step 5/8 [CODER]   → Add database integration (SQLite)
Step 6/8 [TESTER]  → Write and run tests
Step 7/8 [DEVOPS]  → Create Dockerfile and requirements.txt
Step 8/8 [PLANNER] → Document API and usage

[AGENT] Task completed successfully! ✅
[GIT]   Committed: "Task complete: Build a REST API in Python"
```

Generated files:
```
project/
├── main.py          # FastAPI application
├── models.py        # Pydantic models
├── database.py      # SQLite setup
├── test_api.py      # Tests
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## 🔍 Supported Languages

| Language | Execute | Compile | Package Manager |
|----------|---------|---------|-----------------|
| Python | ✅ | — | pip |
| JavaScript | ✅ | — | npm |
| TypeScript | ✅ | tsc | npm |
| Go | ✅ | go build | go get |
| Rust | ✅ | rustc | cargo |
| Java | ✅ | javac | maven |
| C | ✅ | gcc | — |
| C++ | ✅ | g++ | — |
| Bash | ✅ | — | — |
| SQL | ✅ | — | — |

---

## 🧩 Extending XandriX

### Adding a New Agent

```python
from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentType, Task, TaskStep, TaskStatus

class MyAgent(BaseAgent):
    agent_type = AgentType.CODER  # or define a new type
    
    async def execute(self, task: Task, step: TaskStep) -> TaskStep:
        # Your agent logic here
        response = await self.llm.chat(...)
        step.output = response.content
        step.status = TaskStatus.COMPLETED
        return step
```

### Adding a New LLM Provider

Edit `backend/core/llm_client.py` and add a new `_yourprovider_chat` method following the existing pattern.

---

## 📊 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 2 GB | 8 GB |
| Storage | 1 GB | 10 GB |
| Python | 3.11 | 3.12 |
| Node.js | 18 | 20 |
| LLM | GPT-3.5 / Llama 3 | GPT-4o / Claude 3.5 |

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or PR on GitHub.

---

*Built with ❤️ as an open-source alternative to Devin AI*
