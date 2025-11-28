#!/usr/bin/env python3
"""
生产环境启动脚本
支持多种启动模式
"""
import os
import sys
import argparse
import configparser
import platform


def get_config():
    """读取配置"""
    config = configparser.ConfigParser()
    try:
        config.read('config/database.conf', encoding='utf-8')
        return config
    except:
        return None


def is_windows():
    """检测是否是 Windows 系统"""
    return platform.system() == 'Windows'


def start_uvicorn(workers=1, reload=False):
    """使用 Uvicorn 启动"""
    import uvicorn
    
    config = get_config()
    port = 5000
    if config:
        try:
            port = config.getint('server', 'api_port', fallback=5000)
        except:
            pass
    
    print(f"启动 Uvicorn 服务器...")
    print(f"端口: {port}, Workers: {workers}, Reload: {reload}")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
        reload=reload,
        log_level="info",
        access_log=True
    )


def start_gunicorn(workers=None):
    """使用 Gunicorn + Uvicorn worker 启动（仅 Linux/Mac）"""
    
    # 检查是否是 Windows
    if is_windows():
        print("=" * 60)
        print("❌ 错误: Gunicorn 不支持 Windows 系统！")
        print("=" * 60)
        print("\n请使用以下替代方案：")
        print("\n  1. 使用 Uvicorn（推荐）:")
        print("     python start_production.py --mode uvicorn --workers 1")
        print("\n  2. 如果需要多 Worker，请在 Linux/Docker 中运行")
        print("\n  3. Windows 开发模式:")
        print("     python start_production.py --mode dev")
        print()
        sys.exit(1)
    
    import subprocess
    
    config = get_config()
    port = 5000
    if config:
        try:
            port = config.getint('server', 'api_port', fallback=5000)
        except:
            pass
    
    if workers is None:
        import multiprocessing
        workers = multiprocessing.cpu_count() * 2 + 1
    
    print(f"启动 Gunicorn 服务器...")
    print(f"端口: {port}, Workers: {workers}")
    
    cmd = [
        "gunicorn",
        "app.main:app",
        "-w", str(workers),
        "-k", "uvicorn.workers.UvicornWorker",
        "-b", f"0.0.0.0:{port}",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "--log-level", "info",
        "--timeout", "120",
        "--keep-alive", "65",
        "--graceful-timeout", "30"
    ]
    
    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(description='Qunkong 生产环境启动脚本')
    parser.add_argument(
        '--mode', 
        choices=['uvicorn', 'gunicorn', 'dev'],
        default='uvicorn',
        help='启动模式 (default: uvicorn)'
    )
    parser.add_argument(
        '--workers', 
        type=int, 
        default=1,
        help='Worker 数量 (default: 1, 因为 WebSocket 需要共享状态)'
    )
    parser.add_argument(
        '--reload', 
        action='store_true',
        help='开启热重载（仅开发模式）'
    )
    
    args = parser.parse_args()
    
    # Windows 下提示
    if is_windows() and args.workers > 1:
        print("⚠️  警告: Windows 上多 Worker 模式可能不稳定")
        print("   建议使用 Docker/Linux 部署生产环境")
        print()
    
    if args.mode == 'dev':
        start_uvicorn(workers=1, reload=True)
    elif args.mode == 'gunicorn':
        start_gunicorn(workers=args.workers)
    else:
        start_uvicorn(workers=args.workers, reload=args.reload)


if __name__ == '__main__':
    main()

