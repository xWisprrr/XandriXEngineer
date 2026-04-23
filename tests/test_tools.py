import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from tools.filesystem import FileSystemTool, FileInfo
from tools.terminal import TerminalTool, ExecutionResult


@pytest.fixture
def fs(tmp_path):
    return FileSystemTool(base_dir=str(tmp_path))


@pytest.fixture
def terminal(tmp_path):
    return TerminalTool(default_cwd=str(tmp_path))


@pytest.mark.asyncio
async def test_filesystem_write_and_read(fs):
    content = "Hello, XandriXEngineer!\nLine 2"
    await fs.write_file("test.txt", content)
    result = await fs.read_file("test.txt")
    assert result == content


@pytest.mark.asyncio
async def test_filesystem_read_nonexistent(fs):
    with pytest.raises(FileNotFoundError):
        await fs.read_file("nonexistent.txt")


def test_filesystem_list_directory(fs):
    # Create a file first by writing synchronously
    import aiofiles
    import asyncio

    async def setup():
        await fs.write_file("a.py", "print('a')")
        await fs.write_file("b.js", "console.log('b')")

    asyncio.get_event_loop().run_until_complete(setup())
    files = fs.list_directory(".")
    names = [f.name for f in files]
    assert "a.py" in names
    assert "b.js" in names


def test_filesystem_create_directory(fs):
    success = fs.create_directory("subdir/nested")
    assert success
    files = fs.list_directory(".")
    names = [f.name for f in files]
    assert "subdir" in names
    # Verify nested subdirectory was actually created inside subdir
    subdir_files = fs.list_directory("subdir")
    assert any(f.name == "nested" for f in subdir_files)


@pytest.mark.asyncio
async def test_filesystem_delete_file(fs):
    await fs.write_file("to_delete.txt", "delete me")
    assert fs.file_exists("to_delete.txt")
    success = fs.delete_file("to_delete.txt")
    assert success
    assert not fs.file_exists("to_delete.txt")


@pytest.mark.asyncio
async def test_filesystem_search_files(fs):
    await fs.write_file("foo.py", "")
    await fs.write_file("bar.py", "")
    await fs.write_file("baz.js", "")
    found = fs.search_files("*.py")
    assert len(found) == 2
    for f in found:
        assert f.endswith(".py")


def test_filesystem_file_info_structure(fs):
    import asyncio
    asyncio.get_event_loop().run_until_complete(fs.write_file("info_test.py", "x = 1"))
    files = fs.list_directory(".")
    py_files = [f for f in files if f.name == "info_test.py"]
    assert len(py_files) == 1
    fi = py_files[0]
    assert isinstance(fi, FileInfo)
    assert fi.name == "info_test.py"
    assert fi.extension == ".py"
    assert fi.size > 0
    assert not fi.is_dir


@pytest.mark.asyncio
async def test_terminal_execution(terminal):
    result = await terminal.execute("echo 'terminal test'")
    assert result.exit_code == 0
    assert 'terminal test' in result.stdout
    assert result.duration > 0


@pytest.mark.asyncio
async def test_terminal_execution_failure(terminal):
    result = await terminal.execute("python3 -c 'raise SystemExit(1)'")
    assert result.exit_code != 0


@pytest.mark.asyncio
async def test_terminal_execution_timeout(terminal):
    result = await terminal.execute("sleep 10", timeout=1)
    assert result.exit_code == -1
    assert 'timed out' in result.stderr.lower()


@pytest.mark.asyncio
async def test_terminal_run_python_code(terminal):
    result = await terminal.run_python_code("print(2 + 2)")
    assert result.exit_code == 0
    assert '4' in result.stdout


def test_execution_result_command_field():
    result = ExecutionResult(stdout="out", stderr="err", exit_code=0, duration=0.5, command="test cmd")
    assert result.command == "test cmd"


@pytest.mark.asyncio
async def test_git_init(tmp_path):
    from tools.git_tool import GitTool
    git = GitTool(repo_path=str(tmp_path))
    success = git.init_repo(str(tmp_path))
    assert success

    # Verify .git dir exists
    assert os.path.isdir(os.path.join(str(tmp_path), ".git"))
