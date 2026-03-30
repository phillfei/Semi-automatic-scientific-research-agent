"""
中间件 - 处理常见请求问题
"""

import os
import logging
import psutil
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

logger = logging.getLogger(__name__)


def kill_related_python_processes():
    """杀死所有与项目相关的 Python 进程（包括 uvicorn、agent 等）"""
    killed = []
    current_pid = os.getpid()
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pid = proc.info['pid']
            name = proc.info['name'] or ''
            cmdline = proc.info['cmdline'] or []
            
            if pid == current_pid:
                continue
                
            is_target = False
            cmdline_str = ' '.join(cmdline).lower()
            
            if 'python' in name.lower() or name.lower().endswith('.exe'):
                project_keywords = [
                    'evo_code_optimizer', 'evoagentx', 'run_server',
                    'workflow_api', 'uvicorn', 'fastapi', 'agent',
                    'supervisor_agent', 'search_agent', 'engineer_agent'
                ]
                
                for keyword in project_keywords:
                    if keyword in cmdline_str:
                        is_target = True
                        break
                
                if not is_target:
                    try:
                        cwd = proc.cwd()
                        if 'evo_code_optimizer' in cwd.lower() or 'evoagentx' in cwd.lower():
                            is_target = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            
            if 'uvicorn' in name.lower() or 'uvicorn' in cmdline_str:
                is_target = True
            
            if is_target:
                try:
                    proc_obj = psutil.Process(pid)
                    proc_name = proc_obj.name()
                    proc_obj.terminate()
                    proc_obj.wait(timeout=2)
                    killed.append(f"{proc_name}(PID:{pid})")
                except psutil.TimeoutExpired:
                    proc_obj.kill()
                    killed.append(f"{proc_name}(PID:{pid})[强制]")
                except (psutil.NoSuchProcess, PermissionError):
                    pass
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    return killed


class WindowsConnectionFixMiddleware(BaseHTTPMiddleware):
    """
    修复 Windows 上的连接关闭问题
    捕获 ConnectionResetError 并优雅处理
    """
    
    async def dispatch(self, request, call_next):
        try:
            response = await call_next(request)
            return response
        except ConnectionResetError:
            # 客户端强制关闭连接，静默处理
            logger.debug(f"Client closed connection: {request.url.path}")
            return Response(status_code=499)  # Client Closed Request
        except BrokenPipeError:
            logger.debug(f"Broken pipe: {request.url.path}")
            return Response(status_code=499)
        except OSError as e:
            if e.errno == 10054:  # Windows: 远程主机强迫关闭连接
                logger.debug(f"Connection reset by peer: {request.url.path}")
                return Response(status_code=499)
            raise


class HTTPSDetectionMiddleware(BaseHTTPMiddleware):
    """
    检测并处理 HTTPS 请求发送到 HTTP 服务器的情况
    """
    
    async def dispatch(self, request, call_next):
        # 检查是否是 TLS/SSL 握手请求
        # TLS 握手以 0x16 (22) 字节开始
        
        # 检查常见的 HTTPS 指示器
        if request.url.scheme == "https":
            logger.warning(f"HTTPS request detected on HTTP server: {request.url}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "HTTPS not supported",
                    "message": "This server only supports HTTP. Please use http:// instead of https://",
                    "solution": f"Try: http://{request.url.netloc}{request.url.path}"
                }
            )
        
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # 检查是否是 TLS/SSL 错误
            error_msg = str(e).lower()
            if "tls" in error_msg or "ssl" in error_msg or "handshake" in error_msg:
                logger.warning(f"TLS/SSL error detected: {e}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "HTTPS request detected",
                        "message": "Please use HTTP instead of HTTPS",
                        "hint": "Clear browser HSTS cache for localhost"
                    }
                )
            raise


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    简化请求日志，减少噪音
    """
    
    async def dispatch(self, request, call_next):
        # 忽略 favicon.ico 请求
        if request.url.path == "/favicon.ico":
            return Response(status_code=204)
        
        # 只记录 API 请求，不记录静态资源
        should_log = (
            request.url.path.startswith("/api") or
            request.method != "GET" or
            request.url.path == "/"
        )
        
        if should_log:
            logger.info(f"{request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Error handling {request.url.path}: {e}")
            raise


class ProcessKillMiddleware(BaseHTTPMiddleware):
    """
    每次请求前自主杀死所有相关进程
    确保接口调用前环境干净
    """
    
    async def dispatch(self, request, call_next):
        # 每次请求前执行进程清理
        killed = kill_related_python_processes()
        if killed:
            logger.warning(f"🧹 请求前清理进程: {', '.join(killed[:5])}")
            if len(killed) > 5:
                logger.warning(f"   ... 还有 {len(killed) - 5} 个进程")
        
        # 继续处理请求
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"请求处理失败 {request.url.path}: {e}")
            raise
