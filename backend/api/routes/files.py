from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from config import settings
from tools.filesystem import FileSystemTool
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/files", tags=["files"])

_fs: Optional[FileSystemTool] = None


def get_fs() -> FileSystemTool:
    global _fs
    if _fs is None:
        _fs = FileSystemTool(base_dir=settings.WORKSPACE_DIR)
    return _fs


class CreateFileRequest(BaseModel):
    path: str
    content: str


@router.get("", response_model=List[Dict[str, Any]])
async def list_files(path: str = Query(default=".")):
    fs = get_fs()
    try:
        files = fs.list_directory(path)
        return [
            {
                "name": f.name,
                "path": f.path,
                "size": f.size,
                "modified": f.modified,
                "is_dir": f.is_dir,
                "extension": f.extension,
            }
            for f in files
        ]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/content")
async def get_file_content(path: str = Query(...)):
    fs = get_fs()
    try:
        content = await fs.read_file(path)
        return {"path": path, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("")
async def create_or_update_file(request: CreateFileRequest):
    fs = get_fs()
    try:
        await fs.write_file(request.path, request.content)
        return {"message": "File saved", "path": request.path}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("")
async def delete_file(path: str = Query(...)):
    fs = get_fs()
    if not fs.file_exists(path):
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    success = fs.delete_file(path)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete file")
    return {"message": "File deleted", "path": path}
