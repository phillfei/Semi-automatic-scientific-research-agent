"""
项目管理器 - 基于JSON文件存储项目历史记录
支持项目创建、历史查询、任务记录、搜索报告复用
"""

import json
import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from threading import Lock


class ProjectManager:
    """项目管理器 - 管理项目历史记录"""
    
    def __init__(self, data_dir: str = "./data/projects"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
    
    def _get_project_file(self, project_name: str) -> Path:
        """获取项目历史文件路径"""
        # 清理项目名，避免非法字符
        safe_name = "".join(c for c in project_name if c.isalnum() or c in ('_', '-', ' ')).strip()
        if not safe_name:
            safe_name = "default_project"
        return self.data_dir / f"{safe_name}.json"
    
    def _load_project(self, project_name: str) -> Dict[str, Any]:
        """加载项目数据"""
        file_path = self._get_project_file(project_name)
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "name": project_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "history": [],
            "tasks": [],
            "search_reports": {}
        }
    
    def _save_project(self, project_name: str, data: Dict[str, Any]):
        """保存项目数据"""
        file_path = self._get_project_file(project_name)
        data["updated_at"] = datetime.now().isoformat()
        with self._lock:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create_project(self, project_name: str) -> Dict[str, Any]:
        """创建新项目"""
        data = self._load_project(project_name)
        self._save_project(project_name, data)
        return {"name": project_name, "created_at": data["created_at"]}
    
    def get_project(self, project_name: str) -> Optional[Dict[str, Any]]:
        """获取项目信息"""
        data = self._load_project(project_name)
        return {
            "name": data["name"],
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "history_count": len(data.get("history", [])),
            "task_count": len(data.get("tasks", [])),
            "search_report_count": len(data.get("search_reports", {}))
        }
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """列出所有项目"""
        projects = []
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                projects.append({
                    "name": data.get("name", file_path.stem),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "history_count": len(data.get("history", [])),
                    "task_count": len(data.get("tasks", [])),
                    "search_report_count": len(data.get("search_reports", {}))
                })
            except Exception:
                pass
        # 按更新时间排序
        projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return projects
    
    def add_history(self, project_name: str, entry: Dict[str, Any]):
        """添加历史记录"""
        data = self._load_project(project_name)
        entry["timestamp"] = datetime.now().isoformat()
        data.setdefault("history", []).append(entry)
        self._save_project(project_name, data)
    
    def get_history(self, project_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取项目历史记录"""
        data = self._load_project(project_name)
        history = data.get("history", [])
        return history[-limit:] if limit > 0 else history
    
    def add_task(self, project_name: str, task: Dict[str, Any]):
        """添加任务记录"""
        data = self._load_project(project_name)
        task["timestamp"] = datetime.now().isoformat()
        data.setdefault("tasks", []).append(task)
        self._save_project(project_name, data)
    
    def get_tasks(self, project_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取项目任务记录"""
        data = self._load_project(project_name)
        tasks = data.get("tasks", [])
        return tasks[-limit:] if limit > 0 else tasks
    
    def project_exists(self, project_name: str) -> bool:
        """检查项目是否存在"""
        file_path = self._get_project_file(project_name)
        return file_path.exists()
    
    def _make_report_key(self, direction_name: str, keywords: List[str]) -> str:
        """生成搜索报告的唯一键"""
        key_str = f"{direction_name}_{'_'.join(sorted(keywords))}"
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def save_search_report(self, project_name: str, direction_name: str, keywords: List[str],
                           report: str, search_results: List[Dict]) -> str:
        """保存搜索报告到项目知识库"""
        data = self._load_project(project_name)
        key = self._make_report_key(direction_name, keywords)
        
        if "search_reports" not in data:
            data["search_reports"] = {}
        
        data["search_reports"][key] = {
            "direction_name": direction_name,
            "keywords": keywords,
            "report": report,
            "search_results": search_results,
            "saved_at": datetime.now().isoformat(),
            "use_count": data["search_reports"].get(key, {}).get("use_count", 0) + 1
        }
        self._save_project(project_name, data)
        return key
    
    def get_search_report(self, project_name: str, direction_name: str, keywords: List[str]) -> Optional[Dict[str, Any]]:
        """从项目知识库获取搜索报告"""
        data = self._load_project(project_name)
        key = self._make_report_key(direction_name, keywords)
        report = data.get("search_reports", {}).get(key)
        if report:
            # 更新使用次数
            report["use_count"] = report.get("use_count", 0) + 1
            data["search_reports"][key] = report
            self._save_project(project_name, data)
        return report
    
    def list_search_reports(self, project_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """列出项目的所有搜索报告"""
        data = self._load_project(project_name)
        reports = data.get("search_reports", {})
        result = []
        for key, report in reports.items():
            result.append({
                "key": key,
                "direction_name": report.get("direction_name"),
                "keywords": report.get("keywords"),
                "saved_at": report.get("saved_at"),
                "use_count": report.get("use_count", 0)
            })
        # 按使用次数排序
        result.sort(key=lambda x: x.get("use_count", 0), reverse=True)
        return result[:limit]


# 全局项目管理器实例
project_manager = ProjectManager()
