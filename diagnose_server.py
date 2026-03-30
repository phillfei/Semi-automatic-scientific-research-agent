#!/usr/bin/env python3
"""
服务器问题诊断工具
"""

import sys
import socket
import subprocess
import urllib.request
import urllib.error


def check_port(port):
    """检查端口是否被占用"""
    print(f"\n🔍 检查端口 {port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', port))
        print(f"  ✅ 端口 {port} 可用")
        return True
    except socket.error:
        print(f"  ⚠️  端口 {port} 已被占用")
        # 查找占用进程
        try:
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            lines = [l for l in result.stdout.split('\n') if f':{port}' in l]
            for line in lines[:3]:
                print(f"     {line.strip()}")
        except:
            pass
        return False
    finally:
        sock.close()


def test_http_connection(host, port, use_https=False):
    """测试 HTTP/HTTPS 连接"""
    protocol = "https" if use_https else "http"
    url = f"{protocol}://{host}:{port}/"
    
    print(f"\n🌐 测试 {protocol.upper()} 连接: {url}")
    
    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, method='GET')
        
        if use_https:
            with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                print(f"  ✅ HTTPS 连接成功 (状态: {response.status})")
                return True
        else:
            with urllib.request.urlopen(req, timeout=5) as response:
                print(f"  ✅ HTTP 连接成功 (状态: {response.status})")
                return True
                
    except urllib.error.HTTPError as e:
        print(f"  ⚠️  HTTP 错误: {e.code} - {e.reason}")
        return False
    except urllib.error.URLError as e:
        error_msg = str(e.reason)
        if "unknown url type" in error_msg:
            print(f"  ❌ URL 错误: {e.reason}")
        elif "Connection refused" in error_msg:
            print(f"  ❌ 连接被拒绝: 服务器可能未运行")
        else:
            print(f"  ❌ 连接失败: {e.reason}")
        return False
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


def test_api_endpoints(host, port):
    """测试 API 端点"""
    print(f"\n📡 测试 API 端点...")
    
    endpoints = [
        "/",
        "/api/upload/",
    ]
    
    for endpoint in endpoints:
        url = f"http://{host}:{port}{endpoint}"
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=3) as response:
                print(f"  ✅ {endpoint} - 状态 {response.status}")
        except Exception as e:
            print(f"  ❌ {endpoint} - 错误: {e}")


def check_browser_cache():
    """提供清除浏览器缓存的指导"""
    print("\n🧹 浏览器缓存问题排查")
    print("=" * 50)
    print("""
如果看到 "Invalid HTTP request received"，可能原因：

1. 🔒 浏览器强制使用 HTTPS (HSTS)
   解决步骤:
   a) 访问 chrome://net-internals/#hsts
   b) 在 "Delete domain security policies" 中输入: localhost
   c) 点击 Delete
   d) 清除浏览器缓存 (Ctrl+Shift+Delete)
   e) 重启浏览器

2. 🧩 浏览器扩展干扰
   解决步骤:
   a) 禁用 HTTPS Everywhere
   b) 禁用广告拦截器
   c) 使用无痕模式 (Ctrl+Shift+N)

3. 📱 前端代码使用 HTTPS URL
   检查: 确保所有 API 调用使用 http:// 而非 https://
   例如: http://localhost:8000/api/upload

4. 🔄 自动重定向
   检查: 其他程序（如代理软件）是否在 80/443 端口做重定向
""")


def main():
    print("=" * 60)
    print("🔧 EvoAgentX 服务器诊断工具")
    print("=" * 60)
    
    host = "localhost"
    port = 8000
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    # 检查端口
    port_available = check_port(port)
    
    if not port_available:
        print(f"\n⚠️  端口 {port} 已被占用，可能服务器已在运行")
        print("   尝试连接现有服务器...")
        
        # 测试现有服务器
        test_http_connection(host, port, use_https=False)
        test_api_endpoints(host, port)
        
        # 测试 HTTPS（看是否是这个导致的警告）
        print("\n🔒 检查是否因 HTTPS 导致警告...")
        test_http_connection(host, port, use_https=True)
        
    else:
        print(f"\nℹ️  端口 {port} 空闲，请先启动服务器:")
        print(f"   python -m backend.app")
    
    # 显示浏览器缓存清理指南
    check_browser_cache()
    
    # 显示推荐的访问方式
    print("\n" + "=" * 60)
    print("📋 推荐的访问方式")
    print("=" * 60)
    print(f"""
1. 启动服务器:
   cd evo_code_optimizer
   python -m backend.app

2. 访问页面 (使用 HTTP，不是 HTTPS):
   http://localhost:{port}/upload

3. 如果用 iframe 嵌入:
   <iframe src="http://localhost:{port}/upload" ...>

4. 检查控制台:
   - 按 F12 打开开发者工具
   - 查看 Console 标签
   - 检查 Network 标签中的请求
""")
    
    print("\n" + "=" * 60)
    print("🧪 测试命令")
    print("=" * 60)
    print(f"""
# 测试根路径
curl -v http://{host}:{port}/

# 测试上传 API
curl -v http://{host}:{port}/api/upload/

# 检查响应头
curl -I http://{host}:{port}/
""")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
