#!/usr/bin/env python3
"""
QueenBee 后端服务启动脚本
"""
import sys
import os
import subprocess
import time

def check_python():
    """检查Python环境"""
    if sys.version_info < (3, 7):
        print("错误: 需要Python 3.7或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    return True

def check_dependencies():
    """检查依赖包"""
    required_packages = [
        'flask', 'websockets', 'sqlite3'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'sqlite3':
                import sqlite3
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("缺少以下依赖包:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n请运行以下命令安装依赖:")
        print("pip install flask websockets")
        return False
    
    return True

def start_backend():
    """启动后端服务"""
    print("正在启动 QueenBee 后端服务...")
    print("Web服务地址: http://localhost:5000")
    print("WebSocket服务地址: ws://localhost:8765")
    print("按 Ctrl+C 停止服务")
    print("-" * 50)
    
    try:
        # 启动后端服务
        if os.path.exists('app/main.py'):
            subprocess.run([sys.executable, '-m', 'app.main'], cwd=os.getcwd())
        elif os.path.exists('bak/server.py'):
            subprocess.run([sys.executable, 'bak/server.py'], cwd=os.getcwd())
        else:
            print("错误: 未找到后端服务文件")
            print("请确保以下文件之一存在:")
            print("  - app/main.py")
            print("  - bak/server.py")
            return False
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"启动服务时出错: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print("QueenBee 后端服务启动器")
    print("=" * 30)
    
    # 检查Python环境
    if not check_python():
        return 1
    
    # 检查依赖包
    if not check_dependencies():
        return 1
    
    # 启动后端服务
    if not start_backend():
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
