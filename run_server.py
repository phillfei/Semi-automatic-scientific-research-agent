#!/usr/bin/env python3
"""
服务器启动脚本 - 带 Windows 兼容性修复
"""

import sys
import os
import argparse
import socket
import psutil
from contextlib import closing

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

# 先应用 Windows 修复（在导入其他模块之前）
from backend.fix_windows_asyncio import patch_all
patch_all()

# 现在可以安全导入其他模块
import uvicorn
from backend.app import app


def kill_process_on_port(port):
    """查找并终止占用指定端口的进程"""
    killed = []
    for conn in psutil.net_connections():
        if conn.laddr.port == port and conn.pid:
            try:
                proc = psutil.Process(conn.pid)
                proc_name = proc.name()
                proc.terminate()  # 先礼貌请求
                proc.wait(timeout=3)
                killed.append(f"{proc_name}(PID:{conn.pid})")
            except psutil.TimeoutExpired:
                proc.kill()  # 超时则强制杀死
                killed.append(f"{proc_name}(PID:{conn.pid})[强制]")
            except (psutil.NoSuchProcess, PermissionError):
                pass
    return killed


def kill_related_python_processes():
    """杀死所有与项目相关的 Python 进程（包括 uvicorn、agent 等）"""
    killed = []
    current_pid = os.getpid()  # 获取当前进程ID，避免自杀
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pid = proc.info['pid']
            name = proc.info['name'] or ''
            cmdline = proc.info['cmdline'] or []
            
            # 跳过当前进程
            if pid == current_pid:
                continue
                
            # 检查是否是相关进程
            is_target = False
            cmdline_str = ' '.join(cmdline).lower()
            
            # 1. Python 进程执行项目相关代码
            if 'python' in name.lower() or name.lower().endswith('.exe'):
                # 检查命令行是否包含项目关键词
                project_keywords = [
                    'evo_code_optimizer',
                    'evoagentx',
                    'run_server',
                    'workflow_api',
                    'uvicorn',
                    'fastapi',
                    'agent',
                    'supervisor_agent',
                    'search_agent',
                    'engineer_agent'
                ]
                
                for keyword in project_keywords:
                    if keyword in cmdline_str:
                        is_target = True
                        break
                
                # 检查是否在当前工作目录下运行
                if not is_target:
                    try:
                        cwd = proc.cwd()
                        if 'evo_code_optimizer' in cwd.lower() or 'evoagentx' in cwd.lower():
                            is_target = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            
            # 2. Uvicorn 进程
            if 'uvicorn' in name.lower() or 'uvicorn' in cmdline_str:
                is_target = True
            
            if is_target:
                try:
                    proc_obj = psutil.Process(pid)
                    proc_name = proc_obj.name()
                    proc_obj.terminate()
                    proc_obj.wait(timeout=3)
                    killed.append(f"{proc_name}(PID:{pid})")
                except psutil.TimeoutExpired:
                    proc_obj.kill()
                    killed.append(f"{proc_name}(PID:{pid})[强制]")
                except (psutil.NoSuchProcess, PermissionError):
                    pass
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    return killed


def force_free_port(port):
    """确保端口可用：先杀所有相关进程，再杀占用端口的进程，最后验证"""
    # 第1步：杀死所有相关 Python 进程
    killed_processes = kill_related_python_processes()
    if killed_processes:
        print(f"⚠️  已清理 {len(killed_processes)} 个相关进程:")
        for p in killed_processes[:10]:  # 最多显示10个
            print(f"   - {p}")
        if len(killed_processes) > 10:
            print(f"   ... 还有 {len(killed_processes) - 10} 个进程")
    
    # 第2步：尝试杀掉端口占用者
    killed_port = kill_process_on_port(port)
    if killed_port:
        print(f"⚠️  已清理端口 {port} 占用者: {', '.join(killed_port)}")
    
    # 第3步：验证端口是否真的空了
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        if sock.connect_ex(('localhost', port)) == 0:
            raise RuntimeError(f"端口 {port} 仍被占用（可能是系统进程）")
    
    return port


def main():
    parser = argparse.ArgumentParser(description="EvoAgentX Server")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="开发模式（自动重载）")
    parser.add_argument("--no-kill", action="store_true", help="不自动杀死占用端口的进程")
    args = parser.parse_args()
    
    # 确保端口可用
    if not args.no_kill:
        try:
            force_free_port(args.port)
        except RuntimeError as e:
            print(f"❌ {e}")
            sys.exit(1)
    
    print("=" * 60)
    print("🚀 EvoAgentX 服务器启动")
    print("=" * 60)
    print(f"📍 地址: http://{args.host}:{args.port}")
    print(f"📤 上传页面: http://localhost:{args.port}/upload")
    print(f"🔧 API: http://localhost:{args.port}/api/upload/")
    print("=" * 60)
    print()
    
    # uvicorn 配置
    config = uvicorn.Config(
        app=app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        # Windows 优化
        loop="asyncio",  # 使用标准 asyncio 而非 uvloop
        http="h11",      # 使用 h11 而非 httptools（更稳定）
        # 日志
        log_level="warning",  # 减少日志噪音
        access_log=False,     # 禁用访问日志（我们用自定义的）
    )
    
    server = uvicorn.Server(config)
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n\n👋 服务器已停止")


if __name__ == "__main__":
    main()
