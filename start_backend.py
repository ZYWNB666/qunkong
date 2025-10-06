#!/usr/bin/env python3
"""
Qunkong 后端服务启动脚本
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
        'flask', 'websockets', 'pymysql', 'psutil', 'configparser'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("缺少以下依赖包:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def check_database_config():
    """检查数据库配置"""
    config_file = "config/database.conf"
    template_file = "config/database.conf.template"
    
    if not os.path.exists(config_file):
        print("错误: 数据库配置文件不存在")
        print(f"请复制 {template_file} 到 {config_file}")
        print("然后编辑配置文件填写数据库连接信息")
        print("\n或者运行初始化脚本:")
        print("python scripts/init_database.py")
        return False
    
    # 检查配置文件是否已填写
    try:
        import configparser
        config = configparser.ConfigParser()
        config.read(config_file, encoding='utf-8')
        
        username = config.get('mysql', 'username')
        if username == 'your_username':
            print("警告: 数据库配置文件未填写")
            print(f"请编辑 {config_file} 填写正确的数据库连接信息")
            return False
            
    except Exception as e:
        print(f"读取数据库配置失败: {e}")
        return False
    
    return True

def test_database_connection():
    """测试数据库连接"""
    try:
        from app.models import DatabaseManager
        db = DatabaseManager()
        print("数据库连接测试成功")
        return True
    except FileNotFoundError as e:
        print(f"数据库配置文件错误: {e}")
        return False
    except Exception as e:
        print(f"数据库连接失败: {e}")
        print("请检查:")
        print("1. MySQL服务是否运行")
        print("2. 数据库配置是否正确")
        print("3. 数据库用户权限是否足够")
        return False

def start_backend():
    """启动后端服务"""
    print("正在启动 Qunkong 后端服务...")
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
    print("Qunkong 后端服务启动器")
    print("=" * 30)
    
    # 检查Python环境
    print("1. 检查Python环境...")
    if not check_python():
        return 1
    print("   ✓ Python环境检查通过")
    
    # 检查依赖包
    print("\n2. 检查依赖包...")
    if not check_dependencies():
        return 1
    print("   ✓ 依赖包检查通过")
    
    # 检查数据库配置
    print("\n3. 检查数据库配置...")
    if not check_database_config():
        return 1
    print("   ✓ 数据库配置检查通过")
    
    # 测试数据库连接
    print("\n4. 测试数据库连接...")
    if not test_database_connection():
        return 1
    print("   ✓ 数据库连接测试通过")
    
    print("\n" + "=" * 50)
    
    # 启动后端服务
    if not start_backend():
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
