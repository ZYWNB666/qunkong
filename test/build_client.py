#!/usr/bin/env python3
"""
Qunkong Agent 客户端打包脚本
"""
import os
import sys
import subprocess
import platform
from pathlib import Path

def check_dependencies():
    """检查打包依赖"""
    print("检查打包环境...")
    
    try:
        import PyInstaller
        print(f"✓ PyInstaller 版本: {PyInstaller.__version__}")
    except ImportError:
        print("✗ PyInstaller 未安装，请运行: pip install pyinstaller")
        return False
    
    for package in ['websockets', 'psutil']:
        try:
            __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"✗ {package} 未安装")
            return False
    
    return True

def build_executable():
    """构建可执行文件"""
    print("\n开始打包...")
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',                    # 打包成单个文件
        '--name=qunkong-agent',        # 可执行文件名
        '--strip',                      # 去除符号信息
        '--clean',                      # 清理临时文件
        '--noconfirm',                  # 不确认覆盖
        
        # 包含的隐式导入
        '--hidden-import=websockets',
        '--hidden-import=psutil', 
        '--hidden-import=json',
        '--hidden-import=asyncio',
        '--hidden-import=platform',
        '--hidden-import=subprocess',
        '--hidden-import=hashlib',
        
        # 排除不需要的模块（减小文件大小）
        '--exclude-module=tkinter',
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        
        # 源文件
        'app/client.py'
    ]
    
    # 如果有UPX，启用压缩
    if os.system('which upx >/dev/null 2>&1') == 0:
        cmd.append('--upx-dir=/usr/bin')
        print("✓ 启用 UPX 压缩")
    
    print(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode == 0

def main():
    print("Qunkong Agent 打包工具")
    print("=" * 40)
    
    if not os.path.exists('app/client.py'):
        print("✗ 未找到 app/client.py 文件")
        return 1
    
    if not check_dependencies():
        return 1
    
    if build_executable():
        exe_path = Path('dist/qunkong-agent')
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n✓ 打包成功! 文件大小: {size_mb:.1f} MB")
            print(f"可执行文件: {exe_path}")
            
            # 设置执行权限
            os.chmod(exe_path, 0o755)
            
            print("\n使用方法:")
            print("./dist/qunkong-agent --server SERVER_IP --port 8765")
            return 0
    
    print("✗ 打包失败")
    return 1

if __name__ == '__main__':
    sys.exit(main())