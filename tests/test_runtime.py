import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from runtime.manager import RuntimeManager, Language


@pytest.fixture
def manager(tmp_path):
    return RuntimeManager(workspace_dir=str(tmp_path))


def test_language_detection(manager):
    assert manager.detect_language("script.py") == Language.PYTHON
    assert manager.detect_language("app.js") == Language.JAVASCRIPT
    assert manager.detect_language("main.go") == Language.GO
    assert manager.detect_language("lib.rs") == Language.RUST
    assert manager.detect_language("Main.java") == Language.JAVA
    assert manager.detect_language("run.sh") == Language.BASH
    assert manager.detect_language("query.sql") == Language.SQL
    assert manager.detect_language("app.ts") == Language.TYPESCRIPT


def test_language_detection_by_content(manager):
    python_code = "import os\nprint('hello')"
    assert manager.detect_language(python_code) == Language.PYTHON

    go_code = "package main\nfunc main() {}"
    assert manager.detect_language(go_code) == Language.GO

    js_code = "const x = 1; console.log(x);"
    assert manager.detect_language(js_code) == Language.JAVASCRIPT


def test_available_runtimes(manager):
    runtimes = manager.get_available_runtimes()
    assert isinstance(runtimes, dict)
    # Python should always be available in test env
    assert Language.PYTHON in runtimes
    assert isinstance(runtimes[Language.PYTHON], bool)


def test_python_runtime_available(manager):
    available = manager.check_runtime(Language.PYTHON)
    assert available is True


@pytest.mark.asyncio
async def test_python_execution(manager):
    code = "print('hello from test')"
    result = await manager.run(code, Language.PYTHON)
    assert result.exit_code == 0
    assert 'hello from test' in result.stdout


@pytest.mark.asyncio
async def test_python_execution_with_error(manager):
    code = "raise ValueError('intentional error')"
    result = await manager.run(code, Language.PYTHON)
    assert result.exit_code != 0
    assert result.stderr or result.stdout


@pytest.mark.asyncio
async def test_bash_execution(manager):
    code = "echo 'bash test output'"
    result = await manager.run(code, Language.BASH)
    assert result.exit_code == 0
    assert 'bash test output' in result.stdout


def test_execution_result_structure(manager):
    from tools.terminal import ExecutionResult
    result = ExecutionResult(
        stdout="output",
        stderr="",
        exit_code=0,
        duration=0.1,
        command="test",
    )
    assert result.stdout == "output"
    assert result.exit_code == 0
    assert result.duration == 0.1


def test_install_runtime_logs(manager, capsys):
    # install_runtime should log and return False (placeholder)
    result = manager.install_runtime(Language.RUST)
    assert result is False


def test_language_enum_values():
    assert Language.PYTHON.value == "python"
    assert Language.JAVASCRIPT.value == "javascript"
    assert Language.GO.value == "go"
    assert Language.RUST.value == "rust"
