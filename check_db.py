#!/usr/bin/env python3
"""
直接查询数据库中的Agent数据
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models import DatabaseManager

def check_database():
    """检查数据库中的Agent数据"""
    print("=== 检查数据库中的Agent数据 ===")
    
    try:
        db = DatabaseManager()
        agents = db.get_all_agents()
        
        print(f"数据库中共有 {len(agents)} 个Agent:")
        print()
        
        for agent in agents:
            print(f"Agent ID: {agent['id']}")
            print(f"  主机名: {agent['hostname']}")
            print(f"  内网IP: {agent['ip_address']}")
            print(f"  外网IP: {agent.get('external_ip', 'NOT_FOUND')}")
            print(f"  状态: {agent['status']}")
            print(f"  最后心跳: {agent['last_heartbeat']}")
            print("-" * 50)
            
    except Exception as e:
        print(f"查询数据库失败: {e}")

if __name__ == "__main__":
    check_database()
