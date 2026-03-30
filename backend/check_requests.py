#!/usr/bin/env python3
"""
诊断 Invalid HTTP request 警告
捕获并分析原始请求内容
"""

import socket
import ssl
import threading


def create_diagnostic_server(host='0.0.0.0', port=8000):
    """创建诊断服务器，查看原始请求内容"""
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(5)
    
    print(f"🔍 诊断服务器监听 {host}:{port}")
    print("请在浏览器访问后查看原始请求内容\n")
    
    while True:
        conn, addr = sock.accept()
        print(f"\n📡 新连接来自: {addr}")
        
        try:
            # 接收原始数据
            data = conn.recv(4096)
            
            if not data:
                continue
            
            # 尝试解码
            try:
                text = data.decode('utf-8', errors='replace')
                print("📨 收到的数据:")
                print("-" * 50)
                print(text[:500])  # 只显示前500字符
                print("-" * 50)
                
                # 分析请求类型
                first_line = text.split('\r\n')[0] if '\r\n' in text else text.split('\n')[0]
                
                if first_line.startswith('\x16\x03') or first_line.startswith('\x16\x01'):
                    print("⚠️  检测到: TLS/SSL 握手请求 (HTTPS)")
                    print("💡 解决方案: 浏览器在尝试 HTTPS 连接，请访问 http:// 而非 https://")
                    
                elif 'GET /' in first_line or 'POST /' in first_line:
                    print("✅ 检测到: 正常 HTTP 请求")
                    
                elif 'OPTIONS' in first_line:
                    print("ℹ️  检测到: CORS 预检请求")
                    
                else:
                    print(f"❓ 未知请求类型: {first_line[:50]}")
                    
            except Exception as e:
                print(f"❌ 解码错误: {e}")
                print(f"原始字节 (hex): {data[:50].hex()}")
                
        except Exception as e:
            print(f"❌ 处理错误: {e}")
            
        finally:
            conn.close()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    
    print("=" * 60)
    print("HTTP 请求诊断工具")
    print("=" * 60)
    print(f"\n1. 先停止当前运行的服务器")
    print(f"2. 运行此诊断工具")
    print(f"3. 在浏览器访问 http://localhost:{port}")
    print(f"4. 查看输出判断问题\n")
    
    try:
        create_diagnostic_server(port=port)
    except KeyboardInterrupt:
        print("\n\n诊断结束")
