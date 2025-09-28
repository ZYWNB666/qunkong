#!/usr/bin/env python3
"""
QueenBee 演示数据生成脚本
用于生成测试用的Agent和执行历史数据
"""
import sqlite3
import json
import random
from datetime import datetime, timedelta
import uuid

def create_demo_data():
    """创建演示数据"""
    # 连接数据库
    conn = sqlite3.connect('queenbee.db')
    cursor = conn.cursor()
    
    # 创建表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            hostname TEXT,
            ip_address TEXT,
            status TEXT,
            last_heartbeat TEXT,
            register_time TEXT,
            websocket_info TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_system_info (
            agent_id TEXT PRIMARY KEY,
            hostname TEXT,
            ip_address TEXT,
            last_heartbeat TEXT,
            status TEXT,
            register_time TEXT,
            system_info TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS execution_history (
            id TEXT PRIMARY KEY,
            script_name TEXT,
            script TEXT,
            script_params TEXT,
            target_hosts TEXT,
            status TEXT,
            created_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            timeout INTEGER,
            execution_user TEXT,
            results TEXT,
            error_message TEXT
        )
    ''')
    
    # 生成Agent数据
    agent_names = [
        'web-server-01', 'web-server-02', 'db-server-01', 'db-server-02',
        'cache-server-01', 'cache-server-02', 'app-server-01', 'app-server-02',
        'monitor-server-01', 'backup-server-01'
    ]
    
    regions = ['default', 'office', 'production', 'staging']
    statuses = ['ONLINE', 'OFFLINE']
    
    for i, hostname in enumerate(agent_names):
        agent_id = str(uuid.uuid4())
        ip = f"10.0.1.{i+10}"
        status = random.choice(statuses)
        last_heartbeat = (datetime.now() - timedelta(minutes=random.randint(0, 30))).isoformat()
        register_time = (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat()
        
        # 插入Agent数据
        cursor.execute('''
            INSERT OR REPLACE INTO agents 
            (id, hostname, ip_address, status, last_heartbeat, register_time, websocket_info)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (agent_id, hostname, ip, status, last_heartbeat, register_time, '{}'))
        
        # 插入系统信息
        system_info = {
            'os': random.choice(['Ubuntu 20.04', 'CentOS 7', 'Ubuntu 18.04', 'CentOS 8']),
            'kernel': f"Linux {random.randint(4, 5)}.{random.randint(0, 19)}.{random.randint(0, 100)}",
            'cpu': f"Intel Xeon E5-{random.randint(2600, 2699)} v4",
            'memory': f"{random.choice([8, 16, 32, 64])}GB",
            'disk': f"{random.choice([100, 200, 500, 1000])}GB SSD"
        }
        
        cursor.execute('''
            INSERT OR REPLACE INTO agent_system_info 
            (agent_id, hostname, ip_address, last_heartbeat, status, register_time, system_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (agent_id, hostname, ip, last_heartbeat, status, register_time, json.dumps(system_info)))
    
    # 生成执行历史数据
    script_names = [
        '系统健康检查', '数据库备份', '日志清理', '服务重启',
        '磁盘空间检查', '内存使用监控', '网络连接测试', '文件同步',
        '安全扫描', '性能优化'
    ]
    
    script_templates = [
        '''#!/bin/bash
echo "开始系统健康检查..."
df -h
free -m
uptime
echo "系统健康检查完成"''',
        
        '''#!/bin/bash
echo "开始数据库备份..."
mysqldump -u root -p database_name > backup_$(date +%Y%m%d_%H%M%S).sql
echo "数据库备份完成"''',
        
        '''#!/bin/bash
echo "开始清理日志文件..."
find /var/log -name "*.log" -mtime +7 -delete
echo "日志清理完成"''',
        
        '''#!/bin/bash
echo "重启服务..."
systemctl restart nginx
systemctl restart mysql
echo "服务重启完成"'''
    ]
    
    task_statuses = ['COMPLETED', 'FAILED', 'RUNNING', 'PENDING']
    
    for i in range(50):  # 生成50条执行历史
        task_id = str(uuid.uuid4())
        script_name = random.choice(script_names)
        script = random.choice(script_templates)
        status = random.choice(task_statuses)
        
        created_at = (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
        started_at = (datetime.now() - timedelta(days=random.randint(0, 30), minutes=random.randint(0, 59))).isoformat()
        
        if status in ['COMPLETED', 'FAILED']:
            completed_at = (datetime.now() - timedelta(days=random.randint(0, 30), minutes=random.randint(0, 59))).isoformat()
        else:
            completed_at = None
        
        # 随机选择目标主机
        target_agents = cursor.execute('SELECT id FROM agents LIMIT 3').fetchall()
        target_hosts = [agent[0] for agent in target_agents]
        
        # 生成执行结果
        results = {}
        for agent_id in target_hosts:
            exit_code = 0 if status == 'COMPLETED' else random.choice([0, 1])
            results[agent_id] = {
                'exit_code': exit_code,
                'stdout': f"任务执行成功\n输出信息: {script_name} 执行完成",
                'stderr': '' if exit_code == 0 else f"错误信息: {script_name} 执行失败",
                'execution_time': random.randint(1, 300)
            }
        
        cursor.execute('''
            INSERT OR REPLACE INTO execution_history 
            (id, script_name, script, script_params, target_hosts, status, 
             created_at, started_at, completed_at, timeout, execution_user, results, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_id, script_name, script, '', json.dumps(target_hosts), status,
            created_at, started_at, completed_at, 7200, 'root', 
            json.dumps(results), ''
        ))
    
    # 提交更改
    conn.commit()
    conn.close()
    
    print("演示数据生成完成！")
    print(f"- 生成了 {len(agent_names)} 个Agent")
    print(f"- 生成了 50 条执行历史记录")
    print("- 数据库文件: queenbee.db")

if __name__ == "__main__":
    create_demo_data()
