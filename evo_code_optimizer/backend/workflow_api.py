"""
工作流执行 API - 实际调用 Agent
"""

import asyncio
import sys
import traceback
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.task_manager import task_manager, TaskStatus
from utils.agent_logger import get_agent_logger
from utils.project_manager import project_manager

router = APIRouter(prefix="/workflow", tags=["workflow"])

# 初始化日志记录器
logger = get_agent_logger()


class OptimizeRequest(BaseModel):
    project_name: str
    html_content: Optional[str] = ""
    data_sample_content: Optional[str] = ""
    data_sample_path: Optional[str] = ""
    data_sample_filename: Optional[str] = ""
    data_sample_folder: Optional[str] = ""
    code_content: Optional[str] = ""
    instruction: Optional[str] = ""
    search_time_limit: Optional[int] = 5


class OptimizeResponse(BaseModel):
    task_id: str
    status: str
    message: str


async def run_agent_workflow(task_id: str, project_name: str, inputs: dict):
    """
    异步执行 Agent 工作流
    """
    try:
        # 开始任务
        task_manager.start_task(task_id)
        task_manager.add_log(task_id, f"🚀 开始执行工作流: {project_name}", "info")
        logger.log_step("Workflow", "start", f"任务 {task_id} 开始")
        
        # 记录任务到项目历史
        project_manager.add_task(project_name, {
            "task_id": task_id,
            "instruction": inputs.get("instruction", ""),
            "has_html": bool(inputs.get("html_content", "")),
            "has_data": bool(inputs.get("data_sample_content", "")),
            "has_code": bool(inputs.get("code_content", "")),
            "search_time_limit": inputs.get("search_time_limit", 5)
        })
        
        # 导入必要的模块
        try:
            from agents import create_llm
            from workflows.optimization_workflow import create_workflow
        except ImportError as e:
            task_manager.fail_task(task_id, f"导入失败: {e}")
            logger.log_agent_error("Workflow", "import", e)
            return
        
        # 创建 LLM
        task_manager.update_progress(task_id, 5, "初始化 LLM")
        task_manager.add_log(task_id, "🤖 初始化 LLM...")
        llm = create_llm(temperature=0.3)
        
        # 创建并配置工作流
        task_manager.update_progress(task_id, 10, "创建工作流")
        task_manager.add_log(task_id, "📋 创建工作流...")
        
        workflow = create_workflow(project_name, llm)
        
        # ========== Supervisor Agent ==========
        task_manager.update_progress(task_id, 15, "Supervisor - 深度研究")
        task_manager.add_log(task_id, "🎯 Supervisor Agent: 开始深度研究项目")
        
        # 获取 Supervisor Agent
        supervisor = workflow.agent_manager.get_agent("Supervisor")
        if supervisor:
            # 如果有二进制数据文件路径，尝试提取信息
            data_sample_info = ""
            data_sample_path = inputs.get("data_sample_path", "")
            data_sample_folder = inputs.get("data_sample_folder", "")
            
            if data_sample_folder:
                # 扫描文件夹内容
                try:
                    from pathlib import Path
                    folder = Path(data_sample_folder)
                    files = list(folder.rglob("*")) if folder.exists() else []
                    file_list = [f.name for f in files if f.is_file()][:50]
                    ogg_files = [f for f in files if f.is_file() and f.suffix.lower() == '.ogg']
                    
                    data_sample_info = f"数据文件夹: {data_sample_folder}, 共 {len(file_list)} 个文件"
                    if ogg_files:
                        try:
                            import soundfile as sf
                            sample_ogg = ogg_files[0]
                            info = sf.info(str(sample_ogg))
                            data_sample_info += f"\nOGG样例文件({sample_ogg.name}): 时长={info.duration:.2f}s, 采样率={info.samplerate}Hz, 通道数={info.channels}"
                        except Exception:
                            pass
                    
                    if file_list:
                        data_sample_info += f"\n文件列表(前20): {', '.join(file_list[:20])}"
                    
                    task_manager.add_log(task_id, f"📊 数据文件夹解析完成: {len(file_list)} 个文件")
                except Exception as e:
                    task_manager.add_log(task_id, f"⚠️ 数据文件夹解析失败: {e}")
                    data_sample_info = f"数据文件夹: {data_sample_folder}"
            elif data_sample_path and data_sample_path.lower().endswith('.ogg'):
                try:
                    import soundfile as sf
                    info = sf.info(data_sample_path)
                    data_sample_info = f"OGG音频文件: {inputs.get('data_sample_filename', '')}, 时长={info.duration:.2f}s, 采样率={info.samplerate}Hz, 通道数={info.channels}"
                    task_manager.add_log(task_id, f"📊 数据文件解析: {data_sample_info}")
                except Exception as e:
                    task_manager.add_log(task_id, f"⚠️ 数据文件解析失败: {e}")
                    data_sample_info = f"OGG音频文件: {inputs.get('data_sample_filename', '')}"
            elif data_sample_path:
                data_sample_info = f"二进制数据文件: {inputs.get('data_sample_filename', '')}"
            
            analysis = supervisor.initialize_project(
                project_name=project_name,
                html_content=inputs.get("html_content", ""),
                data_sample_content=inputs.get("data_sample_content", ""),
                data_sample_path=data_sample_path,
                data_sample_folder=data_sample_folder,
                data_sample_info=data_sample_info,
                code_content=inputs.get("code_content", ""),
                instruction=inputs.get("instruction", "")
            )
            directions = analysis.get("optimization_directions", analysis.get("directions", []))
            task_manager.add_log(task_id, f"✅ 研究完成，发现 {len(directions)} 个优化方向")
        else:
            task_manager.add_log(task_id, "⚠️ Supervisor Agent 未找到，使用默认配置")
            analysis = {"directions": [], "optimization_directions": []}
            directions = []
        
        await asyncio.sleep(0.5)
        
        # ========== Search Agent ==========
        task_manager.update_progress(task_id, 35, "Search - 并行检索")
        task_manager.add_log(task_id, "🔍 Search Agent: 开始搜索相关资源")
        
        search = workflow.agent_manager.get_agent("Search")
        search_results = []
        search_time_limit = inputs.get("search_time_limit", 5)
        
        if search and directions:
            # 构建搜索任务
            tasks = []
            for direction in directions[:3]:  # 最多3个方向
                tasks.append({
                    "direction_name": direction.get("name", "未知方向"),
                    "keywords": direction.get("keywords", direction.get("search_keywords", [])),
                    "rationale": direction.get("rationale", "")
                })
            
            if tasks:
                try:
                    task_manager.add_log(task_id, f"⏱️ 搜索时间限制: {search_time_limit} 分钟")
                    # 设置超时
                    result = await asyncio.wait_for(
                        asyncio.to_thread(search.parallel_search, tasks, total_time_limit=search_time_limit, project_name=project_name),
                        timeout=max(300, search_time_limit * 60 + 60)
                    )
                    search_results = result.get("search_results", [])
                    cached_count = sum(1 for r in search_results if r.get("from_cache"))
                    task_manager.add_log(task_id, f"✅ 搜索完成，获取 {len(search_results)} 份报告 (知识库复用 {cached_count} 个)")
                    
                    # Search Agent 向 Supervisor 汇报最有价值的方法
                    if search_results:
                        task_manager.add_log(task_id, "📊 Search Agent: 正在分析最有价值的方法...")
                        best_methods_report = await asyncio.wait_for(
                            asyncio.to_thread(search.report_best_methods, search_results),
                            timeout=120
                        )
                        
                        # 将汇报结果记录到日志，并传给 Supervisor
                        if best_methods_report.get("best_methods"):
                            for bm in best_methods_report["best_methods"]:
                                task_manager.add_log(
                                    task_id,
                                    f"⭐ 推荐方法: {bm.get('method_name')} ({bm.get('direction_name')}) - 信心:{best_methods_report.get('confidence', 'medium')}"
                                )
                        
                        # 保存到项目历史，供 Supervisor 后续参考
                        project_manager.add_history(project_name, {
                            "task_id": task_id,
                            "type": "search_report",
                            "best_methods": best_methods_report.get("best_methods", []),
                            "recommendation": best_methods_report.get("recommendation", ""),
                            "confidence": best_methods_report.get("confidence", "medium")
                        })
                        
                        # 如果有 Supervisor，主动汇报
                        if supervisor:
                            try:
                                supervisor.receive_search_report(best_methods_report)
                            except Exception as e:
                                task_manager.add_log(task_id, f"⚠️ 向Supervisor汇报失败: {e}")
                                
                except asyncio.TimeoutError:
                    task_manager.add_log(task_id, "⚠️ 搜索超时，使用部分结果")
                except Exception as e:
                    task_manager.add_log(task_id, f"⚠️ 搜索出错: {e}")
        else:
            task_manager.add_log(task_id, "⚠️ Search Agent 未找到或无优化方向")
        
        task_manager.update_progress(task_id, 60, "Engineer - 代码生成")
        await asyncio.sleep(0.5)
        
        # ========== Engineer Agent ==========
        task_manager.update_progress(task_id, 65, "Engineer - 生成优化代码")
        task_manager.add_log(task_id, "🔧 Engineer Agent: 开始生成代码")
        
        engineer = workflow.agent_manager.get_agent("Engineer")
        generated_items = []
        
        if engineer:
            try:
                # 检查是否有原始代码
                original_code = inputs.get("code_content", "")
                
                # 构建数据信息字符串传给 Engineer
                data_info_parts = []
                if inputs.get("data_sample_folder"):
                    data_info_parts.append(f"数据文件夹路径: {inputs.get('data_sample_folder')}")
                if inputs.get("data_sample_path"):
                    data_info_parts.append(f"样例数据文件: {inputs.get('data_sample_path')}")
                if inputs.get("data_sample_filename"):
                    data_info_parts.append(f"数据文件名: {inputs.get('data_sample_filename')}")
                data_info = "\n".join(data_info_parts)
                
                # 生成代码和测试
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        engineer.generate_code_and_tests,
                        search_results,
                        original_code,
                        project_name,
                        data_info
                    ),
                    timeout=600  # 10分钟超时
                )
                generated_items = result.get("generated_items", [])
                task_manager.add_log(task_id, f"✅ 代码生成完成，共 {len(generated_items)} 组代码")
                
                # 保存代码
                if generated_items:
                    task_manager.update_progress(task_id, 85, "保存代码文件")
                    saved_files = engineer.save_generated_code(generated_items)
                    task_manager.add_log(task_id, f"💾 已保存 {len(saved_files)} 个文件")
                    
            except asyncio.TimeoutError:
                task_manager.add_log(task_id, "⚠️ 代码生成超时")
            except Exception as e:
                task_manager.add_log(task_id, f"⚠️ 代码生成出错: {e}")
                logger.log_agent_error("Workflow", "engineer", e)
        else:
            task_manager.add_log(task_id, "⚠️ Engineer Agent 未找到")
        
        # ========== 完成 ==========
        task_manager.update_progress(task_id, 95, "整理结果")
        
        results = {
            "project_name": project_name,
            "analysis": analysis,
            "search_results_count": len(search_results),
            "generated_items_count": len(generated_items),
            "generated_files": [
                {
                    "direction": item.get("direction"),
                    "main_code_preview": item.get("main_code", "")[:200] + "..."
                }
                for item in generated_items
            ]
        }
        
        # 记录结果到项目历史
        project_manager.add_history(project_name, {
            "task_id": task_id,
            "search_results_count": len(search_results),
            "generated_items_count": len(generated_items),
            "directions": [item.get("direction") for item in generated_items]
        })
        
        task_manager.update_progress(task_id, 100, "完成")
        task_manager.complete_task(task_id, results)
        task_manager.add_log(task_id, "✨ 工作流执行完成！", "success")
        logger.log_step("Workflow", "complete", f"任务 {task_id} 完成")
        
    except Exception as e:
        error_msg = f"工作流执行失败: {str(e)}"
        task_manager.fail_task(task_id, error_msg)
        task_manager.add_log(task_id, f"❌ {error_msg}", "error")
        logger.log_agent_error("Workflow", "run", e)
        traceback.print_exc()


@router.post("/optimize", response_model=OptimizeResponse)
async def start_optimize(
    request: OptimizeRequest,
    background_tasks: BackgroundTasks
):
    """启动代码优化任务"""
    
    # 创建任务
    inputs = {
        "html_content": request.html_content,
        "data_sample_content": request.data_sample_content,
        "data_sample_path": request.data_sample_path,
        "data_sample_filename": request.data_sample_filename,
        "data_sample_folder": request.data_sample_folder,
        "code_content": request.code_content,
        "instruction": request.instruction,
        "search_time_limit": request.search_time_limit
    }
    
    task = task_manager.create_task(request.project_name, inputs)
    
    # 在后台执行工作流
    background_tasks.add_task(
        run_agent_workflow,
        task.id,
        request.project_name,
        inputs
    )
    
    logger.log_step("API", "optimize", f"创建任务 {task.id} for {request.project_name}")
    
    return OptimizeResponse(
        task_id=task.id,
        status="pending",
        message="任务已创建并开始执行"
    )


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态和进度"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task.to_dict()


@router.get("/task/{task_id}/logs")
async def get_task_logs(task_id: str, limit: int = 100):
    """获取任务日志"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "task_id": task_id,
        "logs": task.logs[-limit:]
    }


@router.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任务"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status == TaskStatus.RUNNING:
        task.status = TaskStatus.CANCELLED
        task_manager.add_log(task_id, "任务已取消", "warning")
    
    return {"status": "cancelled", "task_id": task_id}


@router.get("/tasks")
async def list_tasks():
    """列出所有任务"""
    return {
        "tasks": [task.to_dict() for task in task_manager.tasks.values()]
    }
