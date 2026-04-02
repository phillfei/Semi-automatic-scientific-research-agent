"""
Windows asyncio 兼容性修复
解决 ConnectionResetError 和 ProactorBasePipeTransport 警告
"""

import sys
import asyncio
import platform


def fix_windows_asyncio():
    """修复 Windows 上的 asyncio 问题"""
    
    if platform.system() == 'Windows':
        # 使用 SelectorEventLoop 替代 ProactorEventLoop (Windows 默认)
        # ProactorEventLoop 在连接关闭时会触发警告
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            print("✅ 已切换到 WindowsSelectorEventLoopPolicy")
        except AttributeError:
            pass
        
        # 或者保持 ProactorEventLoop 但静默错误
        #  monkey-patch _call_connection_lost
        try:
            from asyncio.proactor_events import _ProactorBasePipeTransport
            
            original_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost
            
            def patched_call_connection_lost(self, exc):
                """静默处理连接关闭错误"""
                try:
                    original_call_connection_lost(self, exc)
                except ConnectionResetError:
                    # 忽略 "远程主机强迫关闭了连接" 错误
                    pass
                except OSError:
                    # 忽略其他网络错误
                    pass
            
            _ProactorBasePipeTransport._call_connection_lost = patched_call_connection_lost
            print("✅ 已安装 ProactorBasePipeTransport 补丁")
            
        except Exception as e:
            print(f"⚠️  无法安装补丁: {e}")


def silence_uvicorn_logs():
    """减少 uvicorn 的无效请求警告"""
    import logging
    
    # 提高 uvicorn 日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # 完全禁用无效请求警告
    class FilterInvalidHTTP(logging.Filter):
        def filter(self, record):
            return "Invalid HTTP request" not in record.getMessage()
    
    # 应用到 uvicorn 的 error_logger
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logger = logging.getLogger(logger_name)
        logger.addFilter(FilterInvalidHTTP())
    
    print("✅ 已配置日志过滤")


# 兼容性导入
def patch_all():
    """应用所有修复"""
    fix_windows_asyncio()
    silence_uvicorn_logs()
    print("🔧 Windows 兼容性修复完成\n")
