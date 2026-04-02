#!/usr/bin/env python3
"""FastAPI 后端服务"""

import os
import sys
sys.path.insert(0, str(os.path.dirname(os.path.dirname(__file__))))

# 先应用 Windows 兼容性修复（必须在导入 uvicorn 之前）
from backend.fix_windows_asyncio import patch_all
patch_all()

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 导入上传 API
from backend.upload_api import app as upload_app
from backend.workflow_api import router as workflow_router
from backend.middleware import (
    WindowsConnectionFixMiddleware,
    HTTPSDetectionMiddleware,
    RequestLoggingMiddleware
)
from utils.project_manager import project_manager

load_dotenv()

app = FastAPI(title="EvoAgentX 代码优化系统")

# 添加自定义中间件（顺序很重要，后添加的先执行）
app.add_middleware(WindowsConnectionFixMiddleware)
app.add_middleware(HTTPSDetectionMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 获取前端目录路径（使用绝对路径避免 Windows 兼容性问题）
FRONTEND_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

# 挂载前端静态文件
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# 挂载上传 API（作为子应用）
app.mount("/api/upload", upload_app)

# 挂载工作流 API
app.include_router(workflow_router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """首页 - 返回完整前端页面"""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Frontend not found</h1>"


@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    """上传页面"""
    upload_path = os.path.join(FRONTEND_DIR, "upload.html")
    if os.path.exists(upload_path):
        with open(upload_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Upload page not found</h1>"


# ========== 项目管理 API ==========

@app.get("/api/projects")
async def list_projects():
    """列出所有项目"""
    return {"projects": project_manager.list_projects()}


@app.post("/api/projects")
async def create_project(request: dict):
    """创建或获取项目"""
    name = request.get("name", "").strip()
    if not name:
        return {"error": "项目名称不能为空"}
    
    exists = project_manager.project_exists(name)
    result = project_manager.create_project(name)
    return {
        "name": result["name"],
        "created_at": result["created_at"],
        "exists": exists
    }


@app.get("/api/projects/{project_name}")
async def get_project(project_name: str):
    """获取项目信息"""
    project = project_manager.get_project(project_name)
    if not project:
        return {"error": "项目不存在"}
    return project


@app.get("/api/projects/{project_name}/history")
async def get_project_history(project_name: str, limit: int = 50):
    """获取项目历史记录"""
    return {
        "project_name": project_name,
        "history": project_manager.get_history(project_name, limit=limit)
    }


@app.get("/api/projects/{project_name}/tasks")
async def get_project_tasks(project_name: str, limit: int = 50):
    """获取项目任务记录"""
    return {
        "project_name": project_name,
        "tasks": project_manager.get_tasks(project_name, limit=limit)
    }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "EvoAgentX"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", 8000))
    print(f"Starting server: http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
