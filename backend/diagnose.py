#!/usr/bin/env python3
"""
服务器连接诊断工具
用于排查 "Invalid HTTP request received" 警告
"""

import socket
import sys
import urllib.request
import urllib.error


def check_port_usage(port):
    """检查端口使用情况"""
    print(f"\n📡 检查端口 {port} 使用情况...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', port))
        print(f"  ✅ 端口 {port} 可用")
        return True
    except socket.error as e:
        print(f"  ❌ 端口 {port} 被占用: {e}")
        return False
    finally:
        sock.close()


def test_http_connection(host, port, protocol="http"):
    """测试 HTTP 连接"""
    url = f"{protocol}://{host}:{port}/"
    print(f"\n🌐 测试连接: {url}")
    
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"  ✅ 连接成功")
            print(f"  📄 状态码: {response.status}")
            print(f"  📄 内容长度: {len(response.read())} bytes")
            return True
    except urllib.error.HTTPError as e:
        print(f"  ⚠️ HTTP 错误: {e.code}")
        return False
    except urllib.error.URLError as e:
        print(f"  ❌ 连接失败: {e.reason}")
        return False
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


def check_https_redirect(host, port):
    """检查是否尝试 HTTPS 连接 HTTP"""
    print(f"\n🔒 检查 HTTPS 连接...")
    
    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        url = f"https://{host}:{port}/"
        req = urllib.request.Request(url, method='GET')
        
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=3) as response:
                print(f"  ⚠️  警告: HTTPS 连接成功，但服务器是 HTTP")
                print(f"  这可能是浏览器或前端配置问题")
        except urllib.error.URLError as e:
            if "wrong version number" in str(e) or "UNKNOWN_PROTOCOL" in str(e):
                print(f"  ✅ 正常: 服务器拒绝 HTTPS 连接（符合预期）")
            else:
                print(f"  ℹ️  {e}")
    except Exception as e:
        print(f"  ℹ️  无法测试 HTTPS: {e}")


def main():
    """主诊断程序"""
    print("=" * 70)
    print("🔍 EvoAgentX 服务器连接诊断工具")
    print("=" * 70)
    
    host = "localhost"
    port = 8000
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    print(f"\n目标服务器: {host}:{port}")
    
    # 检查端口
    check_port_usage(port)
    
    # 测试 HTTP 连接
    http_ok = test_http_connection(host, port, "http")
    
    # 检查 HTTPS
    check_https_redirect(host, port)
    
    # 提供解决方案
    print("\n" + "=" * 70)
    print("📋 可能的原因和解决方案")
    print("=" * 70)
    
    if not http_ok:
        print("""
❌ 无法连接到服务器

可能原因:
1. 服务器未启动
   解决: 运行 `python -m backend.app`

2. 端口被其他程序占用
   解决: 更换端口 `port=8001` 或终止占用端口的程序

3. 防火墙阻止
   解决: 检查防火墙设置
""")
    else:
        print("""
✅ HTTP 连接正常

如果仍看到 "Invalid HTTP request received" 警告，可能原因:

1. 🔒 浏览器强制 HTTPS
   解决: 
   - 清除浏览器缓存
   - 访问 chrome://net-internals/#hsts 删除 localhost 的 HSTS 设置
   - 使用无痕模式访问

2. 🧩 浏览器扩展干扰
   解决: 禁用广告拦截器、HTTPS Everywhere 等扩展

3. 📱 前端代码使用 HTTPS
   解决: 检查前端配置，确保使用 http://localhost:8000

4. 🔄 自动重定向
   解决: 检查是否有其他服务在 80/443 端口做重定向
""")
    
    print("\n" + "=" * 70)
    print("🧪 测试命令")
    print("=" * 70)
    print(f"""
# 测试根路径
curl http://{host}:{port}/

# 测试上传 API
curl http://{host}:{port}/api/upload/

# 使用 verbose 模式查看详细信息
curl -v http://{host}:{port}/
""")
    
    return 0 if http_ok else 1


if __name__ == "__main__":
    sys.exit(main())
