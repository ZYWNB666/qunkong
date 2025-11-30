#!/usr/bin/env python3
"""
Qunkong RBAC权限管理系统 - 一键初始化脚本
执行方式: python scripts/init_database.py
"""

import sys
import os
import getpass
import pymysql
import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_banner():
    """打印欢迎信息"""
    print("=" * 70)
    print("  Qunkong RBAC权限管理系统 - 数据库初始化工具")
    print("=" * 70)
    print()


def print_step(step, message):
    """打印步骤信息"""
    print(f"\n[步骤 {step}] {message}")
    print("-" * 70)


def run_command(cmd, success_msg, error_msg):
    """执行命令并处理结果 (已弃用,保留兼容)"""
    print(f"✓ {success_msg}")
    return True


def get_mysql_credentials():
    """获取MySQL连接信息"""
    print_step(1, "读取MySQL连接配置")
    
    import configparser
    config = configparser.ConfigParser()
    config_file = 'config/database.conf'
    
    if not os.path.exists(config_file):
        print(f"✗ 配置文件不存在: {config_file}")
        print("\n请先配置数据库连接信息")
        return None
    
    try:
        config.read(config_file, encoding='utf-8')
        
        db_config = {
            'host': config.get('mysql', 'host'),
            'port': config.get('mysql', 'port'),
            'user': config.get('mysql', 'username'),
            'password': config.get('mysql', 'password'),
            'database': config.get('mysql', 'database')
        }
        
        print(f"✓ 配置读取成功")
        print(f"  主机: {db_config['host']}:{db_config['port']}")
        print(f"  数据库: {db_config['database']}")
        print(f"  用户: {db_config['user']}")
        
        return db_config
        
    except Exception as e:
        print(f"✗ 读取配置文件失败: {e}")
        print("\n请检查配置文件格式是否正确")
        return None


def confirm_action(message):
    """确认操作"""
    while True:
        response = input(f"\n{message} (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("请输入 yes 或 no")


def test_connection(config):
    """测试MySQL连接"""
    print_step(2, "测试MySQL连接")
    
    try:
        connection = pymysql.connect(
            host=config['host'],
            port=int(config['port']),
            user=config['user'],
            password=config['password'],
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        cursor.execute('SELECT VERSION()')
        version = cursor.fetchone()
        cursor.close()
        connection.close()
        
        print(f"✓ MySQL连接成功! (版本: {version[0]})")
        return True
        
    except Exception as e:
        print(f"✗ MySQL连接失败!")
        print(f"错误信息: {e}")
        print("\n请检查MySQL服务是否运行,以及用户名密码是否正确")
        return False


def backup_database(config):
    """备份数据库"""
    print_step(3, "备份现有数据库")
    
    try:
        connection = pymysql.connect(
            host=config['host'],
            port=int(config['port']),
            user=config['user'],
            password=config['password'],
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        cursor.execute('SHOW DATABASES')
        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        
        if config['database'] in databases:
            print(f"✓ 检测到数据库 '{config['database']}' 已存在")
            
            if confirm_action("是否需要备份现有数据库?"):
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = f"backup_{config['database']}_{timestamp}.sql"
                
                try:
                    # 使用 mysqldump 备份 (需要系统安装 mysqldump)
                    import subprocess
                    backup_cmd = f"mysqldump -h{config['host']} -P{config['port']} -u{config['user']} -p{config['password']} {config['database']} > {backup_file}"
                    subprocess.run(backup_cmd, shell=True, check=True)
                    print(f"✓ 数据库备份成功: {backup_file}")
                    print(f"\n备份文件保存在: {os.path.abspath(backup_file)}")
                except Exception as e:
                    print(f"✗ 备份失败: {e}")
                    if not confirm_action("备份失败,是否继续初始化?"):
                        return False
        else:
            print(f"✓ 数据库 '{config['database']}' 不存在,将创建新数据库")
        
        return True
        
    except Exception as e:
        print(f"✗ 检查数据库时出错: {e}")
        return False


def drop_database(config):
    """删除旧数据库"""
    print_step(4, "删除旧数据库")
    
    if not confirm_action(f"⚠️  确认删除数据库 '{config['database']}' 吗? (所有数据将丢失)"):
        print("操作已取消")
        return False
    
    try:
        connection = pymysql.connect(
            host=config['host'],
            port=int(config['port']),
            user=config['user'],
            password=config['password'],
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        cursor.execute(f"DROP DATABASE IF EXISTS `{config['database']}`")
        cursor.close()
        connection.close()
        
        print(f"✓ 数据库 '{config['database']}' 已删除")
        return True
        
    except Exception as e:
        print(f"✗ 删除数据库失败!")
        print(f"错误信息: {e}")
        return False


def init_database(config):
    """初始化数据库"""
    print_step(5, "初始化数据库")
    
    # 获取SQL脚本路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file = os.path.join(script_dir, 'init_complete.sql')
    
    if not os.path.exists(sql_file):
        print(f"✗ SQL脚本不存在: {sql_file}")
        return False
    
    print(f"使用SQL脚本: {sql_file}")
    
    try:
        # 读取SQL文件
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 连接数据库
        connection = pymysql.connect(
            host=config['host'],
            port=int(config['port']),
            user=config['user'],
            password=config['password'],
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # 分割并执行SQL语句
        statements = []
        current_statement = []
        
        for line in sql_content.split('\n'):
            # 跳过注释和空行
            stripped = line.strip()
            if stripped.startswith('--') or not stripped:
                continue
            
            current_statement.append(line)
            
            # 如果行以分号结束,这是一个完整的语句
            if stripped.endswith(';'):
                statement = '\n'.join(current_statement).strip()
                if statement:
                    statements.append(statement)
                current_statement = []
        
        # 添加最后一个语句(如果有)
        if current_statement:
            statement = '\n'.join(current_statement).strip()
            if statement:
                statements.append(statement)
        
        # 执行所有SQL语句
        print(f"\n开始执行 {len(statements)} 条SQL语句...")
        success_count = 0
        
        for i, statement in enumerate(statements, 1):
            try:
                cursor.execute(statement)
                connection.commit()
                success_count += 1
                if i % 10 == 0:
                    print(f"  已执行: {i}/{len(statements)}")
            except Exception as e:
                print(f"\n⚠ 语句 {i} 执行失败: {str(e)[:100]}")
                # 继续执行其他语句
                continue
        
        cursor.close()
        connection.close()
        
        print(f"\n✓ 数据库初始化成功! (成功: {success_count}/{len(statements)})")
        return True
        
    except Exception as e:
        print(f"✗ 数据库初始化失败!")
        print(f"错误信息: {e}")
        return False


def verify_initialization(config):
    """验证初始化结果"""
    print_step(6, "验证初始化结果")
    
    try:
        connection = pymysql.connect(
            host=config['host'],
            port=int(config['port']),
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # 检查表数量
        cursor.execute('SHOW TABLES')
        tables = [row[0] for row in cursor.fetchall()]
        table_count = len(tables)
        
        print(f"✓ 成功创建 {table_count} 个表")
        
        # 检查关键表
        key_tables = [
            'users',
            'projects',
            'project_members',
            'project_member_permissions',
            'agents',
            'simple_jobs',
            'agent_install_history'
        ]
        
        print("\n检查关键表:")
        for table in key_tables:
            if table in tables:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} (缺失)")
        
        # 检查默认用户
        cursor.execute('SELECT username, role FROM users WHERE username="admin"')
        admin_user = cursor.fetchone()
        
        if admin_user:
            print("\n✓ 默认管理员账户已创建")
            print("  用户名: admin")
            print("  密码: admin123")
            print("  ⚠️  请登录后立即修改密码!")
        else:
            print("\n⚠ 警告: 默认管理员账户未找到")
        
        # 检查默认项目
        cursor.execute('SELECT project_code, project_name FROM projects WHERE project_code="DEFAULT"')
        default_project = cursor.fetchone()
        
        if default_project:
            print("\n✓ 默认项目已创建")
            print("  项目代码: DEFAULT")
            print(f"  项目名称: {default_project[1]}")
        else:
            print("\n⚠ 警告: 默认项目未找到")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"✗ 验证失败: {e}")
        return False


def print_summary():
    """打印总结信息"""
    print("\n" + "=" * 70)
    print("  数据库初始化完成!")
    print("=" * 70)
    print("\n下一步操作:")
    print("  1. 启动应用服务")
    print("  2. 使用 admin/admin123 登录系统")
    print("  3. 立即修改管理员密码")
    print("  4. 创建项目和用户")
    print("\n详细文档:")
    print("  - 快速开始: docs/RBAC_README.md")
    print("  - 使用示例: docs/RBAC_USAGE_EXAMPLES.md")
    print("=" * 70)


def main():
    """主函数"""
    print_banner()
    
    try:
        # 1. 读取配置文件
        config = get_mysql_credentials()
        if not config:
            print("\n初始化失败: 无法读取配置文件")
            sys.exit(1)
        
        # 2. 测试连接
        if not test_connection(config):
            print("\n初始化失败: 无法连接到MySQL")
            sys.exit(1)
        
        # 3. 备份数据库
        if not backup_database(config):
            print("\n初始化已取消")
            sys.exit(0)
        
        # 4. 删除旧数据库
        if not drop_database(config):
            print("\n初始化已取消")
            sys.exit(0)
        
        # 5. 初始化数据库
        if not init_database(config):
            print("\n初始化失败: 数据库初始化出错")
            sys.exit(1)
        
        # 6. 验证结果
        if not verify_initialization(config):
            print("\n警告: 验证过程出现问题,请手动检查")
        
        # 7. 打印总结
        print_summary()
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
