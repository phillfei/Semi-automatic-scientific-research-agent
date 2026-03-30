"""
任务管理器 - 管理 Agent 工作流执行
支持异步执行、进度跟踪、结果存储
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from enum import Enum
import traceback


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """任务对象"""
    
    def __init__(self, project_name: str, inputs: Dict[str, Any]):
        self.id = str(uuid.uuid4())
        self.project_name = project_name
        self.inputs = inputs
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.progress = 0
        self.current_step = ""
        self.logs: list = []
        self.results: Dict = {}
        self.error: Optional[str] = None
        
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "project_name": self.project_name,
            "status": self.status.value,
            "progress": self.progress,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "logs": self.logs[-50:],  # 最近50条日志
            "results": self.results,
            "error": self.error
        }


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._callbacks: Dict[str, list] = {}
    
    def create_task(self, project_name: str, inputs: Dict) -> Task:
        """创建新任务"""
        task = Task(project_name, inputs)
        self.tasks[task.id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def update_progress(self, task_id: str, progress: int, step: str = ""):
        """更新进度"""
        if task := self.tasks.get(task_id):
            task.progress = min(100, max(0, progress))
            if step:
                task.current_step = step
            self._notify(task_id, "progress", task.to_dict())
    
    def add_log(self, task_id: str, message: str, level: str = "info"):
        """添加日志"""
        if task := self.tasks.get(task_id):
            log_entry = {
                "time": datetime.now().isoformat(),
                "level": level,
                "message": message
            }
            task.logs.append(log_entry)
            self._notify(task_id, "log", log_entry)
    
    def complete_task(self, task_id: str, results: Dict):
        """完成任务"""
        if task := self.tasks.get(task_id):
            task.status = TaskStatus.COMPLETED
            task.progress = 100
            task.results = results
            task.completed_at = datetime.now()
            self._notify(task_id, "completed", task.to_dict())
    
    def fail_task(self, task_id: str, error: str):
        """标记任务失败"""
        if task := self.tasks.get(task_id):
            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = datetime.now()
            self._notify(task_id, "failed", task.to_dict())
    
    def start_task(self, task_id: str):
        """开始任务"""
        if task := self.tasks.get(task_id):
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            self._notify(task_id, "started", task.to_dict())
    
    def subscribe(self, task_id: str, callback: Callable):
        """订阅任务更新"""
        if task_id not in self._callbacks:
            self._callbacks[task_id] = []
        self._callbacks[task_id].append(callback)
    
    def _notify(self, task_id: str, event: str, data: Any):
        """通知订阅者"""
        if task_id in self._callbacks:
            for callback in self._callbacks[task_id]:
                try:
                    callback(event, data)
                except Exception:
                    pass


# 全局任务管理器实例
task_manager = TaskManager()
