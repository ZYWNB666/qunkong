#!/usr/bin/env python3
"""
QueenBee 数据库初始化脚本
"""
import os
import sys
import shutil
import pymysql
import configparser

def create_config_from_template():
    """从模板创建配置文件"""
    template_path = "config/database.conf.template"
    config_path = "config/database.conf"
    
    if not os.path.exists(template_path):
        print(f"错误: 模板文件不存在: {template_path}")
        return False
    
    if os.path.exists(config_path):
        print(f"配置文件已存在: {config_path}")
        return True
    
    # 创建config目录
    os.makedirs("config", exist_ok=True)
    
    # 复制模板文件
    shutil.copy2(template_path, config_path)
    print(f"已创建配置文件: {config_path}")
    print("请编辑配置文件，填写正确的数据库连接信息")
    return True

def test_database_connection(config_path):
    """测试数据库连接"""
    try:
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        # 连接到MySQL服务器（不指定数据库）
        conn = pymysql.connect(
            host=config.get('mysql', 'host'),
            port=config.getint('mysql', 'port'),
            user=config.get('mysql', 'username'),
            password=config.get('mysql', 'password'),
            charset=config.get('mysql', 'charset', fallback='utf8mb4')
        )
        
        cursor = conn.cursor()
        
        # 创建数据库（如果不存在）
        database_name = config.get('mysql', 'database')
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"数据库 '{database_name}' 已创建或已存在")
        
        # 选择数据库
        cursor.execute(f"USE `{database_name}`")
        
        conn.close()
        print("数据库连接测试成功")
        return True
        
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return False

def init_database_tables():
    """初始化数据库表"""
    try:
        # 导入数据库管理器
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from app.models import DatabaseManager
        
        # 初始化数据库
        db = DatabaseManager()
        print("数据库表初始化完成")
        return True
        
    except Exception as e:
        print(f"数据库表初始化失败: {e}")
        return False

def main():
    """主函数"""
    print("QueenBee 数据库初始化脚本")
    print("=" * 40)
    
    # 1. 创建配置文件
    print("1. 创建配置文件...")
    if not create_config_from_template():
        return False
    
    config_path = "config/database.conf"
    
    # 检查配置文件是否已填写
    config = configparser.ConfigParser()
    config.read(config_path, encoding='utf-8')
    
    if config.get('mysql', 'username') == 'your_username':
        print("\n请先编辑配置文件 config/database.conf，填写正确的数据库连接信息")
        print("然后重新运行此脚本")
        return False
    
    # 2. 测试数据库连接
    print("\n2. 测试数据库连接...")
    if not test_database_connection(config_path):
        return False
    
    # 3. 初始化数据库表
    print("\n3. 初始化数据库表...")
    if not init_database_tables():
        return False
    
    print("\n" + "=" * 40)
    print("数据库初始化完成！")
    print("现在可以启动 QueenBee 服务了")
    return True

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
