#!/usr/bin/env python3
"""
检查数据库表结构
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models import DatabaseManager

def check_table_structure():
    """检查agents表的结构"""
    print("=== 检查agents表结构 ===")
    
    try:
        db = DatabaseManager()
        conn = db._get_connection()
        cursor = conn.cursor()
        
        # 查看表结构
        cursor.execute("DESCRIBE agents")
        columns = cursor.fetchall()
        
        print("agents表的字段:")
        for col in columns:
            print(f"  {col['Field']}: {col['Type']} - {col['Null']} - {col['Default']}")
        
        # 检查是否有external_ip字段
        has_external_ip = any(col['Field'] == 'external_ip' for col in columns)
        print(f"\nexternal_ip字段存在: {'是' if has_external_ip else '否'}")
        
        # 如果没有external_ip字段，手动添加
        if not has_external_ip:
            print("\n正在添加external_ip字段...")
            cursor.execute("ALTER TABLE agents ADD COLUMN external_ip VARCHAR(45) DEFAULT '' AFTER ip_address")
            cursor.execute("ALTER TABLE agents ADD INDEX idx_external_ip (external_ip)")
            print("external_ip字段添加成功!")
        
        conn.close()
        
    except Exception as e:
        print(f"检查表结构失败: {e}")

if __name__ == "__main__":
    check_table_structure()
