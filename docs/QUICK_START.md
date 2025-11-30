# RBAC权限系统 - 快速开始指南

## 🚀 一键初始化

### 方式1: Python脚本 (推荐)

```bash
cd /opt/qunkong
python scripts/init_database.py
```

**功能:**
- ✅ 自动备份现有数据库
- ✅ 删除旧表并初始化新结构  
- ✅ 创建默认admin用户和DEFAULT项目
- ✅ 验证初始化结果

### 方式2: 直接执行SQL

```bash
mysql -u root -p < scripts/init_complete.sql
```

## 🔐 默认账户

```
用户名: admin
密码: admin123
角色: 系统管理员
```

⚠️ **重要**: 初始化后请立即修改密码!

## 📋 权限系统说明

### 角色类型

1. **admin** - 系统管理员
   - 拥有所有权限
   - 可以管理所有用户和项目
   - 独立于项目权限体系

2. **project_admin** - 项目管理员  
   - 拥有项目所有权限
   - 可以管理项目成员和权限
   - 一个项目可以有多个管理员

3. **readwrite** - 读写用户
   - 默认权限: 查看、创建、编辑、执行
   - 可以自定义调整权限

4. **readonly** - 只读用户
   - 默认权限: 仅查看
   - 可以自定义添加其他权限

### 功能权限 (12种)

| 权限键 | 说明 | 默认角色 |
|--------|------|----------|
| `agent.view` | 查看Agent | 所有 |
| `agent.batch_add` | 批量添加Agent | readwrite |
| `agent.delete` | 删除Agent | readwrite |
| `agent.restart` | 重启Agent/主机 | readwrite |
| `job.view` | 查看作业 | 所有 |
| `job.create` | 创建作业 | readwrite |
| `job.edit` | 编辑作业 | readwrite |
| `job.delete` | 删除作业 | readwrite |
| `job.execute` | 执行作业 | readwrite |
| `script.execute` | 执行脚本 | readwrite |
| `terminal.access` | 访问终端 | readwrite |
| `history.view` | 查看执行历史 | 所有 |

## 🎯 核心改进

### 1. 简化架构
- ❌ 移除复杂的租户管理
- ✅ 只保留用户管理和项目管理
- ✅ admin用户拥有全局超级权限

### 2. 细粒度权限
- ✅ 12种功能级别权限控制
- ✅ 项目管理员可控制用户功能可见性
- ✅ 例如:可以让某用户无法看到"批量添加主机"按钮

### 3. 资源隔离
所有资源按项目隔离:
- 作业 (simple_jobs)
- 执行历史 (simple_job_executions)  
- Agent (agents)
- 批量安装历史 (agent_install_history)

## 💻 使用示例

### 创建项目

```sql
-- admin用户登录后台
INSERT INTO projects (project_name, project_code, description, created_by)
VALUES ('测试项目', 'TEST001', '这是一个测试项目', 1);
```

### 添加项目成员

```sql
-- 添加用户到项目 (role可选: admin, readwrite, readonly)
INSERT INTO project_members (project_id, user_id, role, status)
VALUES (2, 3, 'readwrite', 'active');
```

### 自定义用户权限

```sql
-- 给用户添加特定权限
INSERT INTO project_member_permissions (project_id, user_id, permission_key)
VALUES 
(2, 3, 'agent.view'),
(2, 3, 'job.view'),
(2, 3, 'job.execute');
```

### 使用API管理权限

```python
import requests

# 获取所有可用权限
response = requests.get(
    'http://localhost:8000/api/projects/1/permissions',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)

# 获取用户权限
response = requests.get(
    'http://localhost:8000/api/projects/1/members/2/permissions',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)

# 设置用户权限
response = requests.post(
    'http://localhost:8000/api/projects/1/members/2/permissions',
    json={'permissions': ['agent.view', 'job.view', 'job.execute']},
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)
```

## 🔍 验证安装

### 检查数据库表

```sql
USE qunkong;

-- 查看所有表
SHOW TABLES;

-- 验证权限表
SELECT * FROM project_member_permissions LIMIT 5;

-- 验证默认用户
SELECT username, role FROM users WHERE username='admin';

-- 验证默认项目  
SELECT project_code, project_name FROM projects WHERE project_code='DEFAULT';
```

### 检查权限配置

```sql
-- 查看用户权限
SELECT 
    u.username,
    p.project_name,
    pm.role,
    GROUP_CONCAT(pmp.permission_key) as permissions
FROM users u
JOIN project_members pm ON u.id = pm.user_id
JOIN projects p ON pm.project_id = p.id
LEFT JOIN project_member_permissions pmp ON pm.project_id = pmp.project_id AND pm.user_id = pmp.user_id
WHERE u.username = 'your_username'
GROUP BY u.id, p.id;
```

## 📚 更多文档

- [完整文档](./RBAC_README.md) - 从这里开始
- [实施指南](./RBAC_IMPLEMENTATION_GUIDE.md) - 详细步骤
- [使用示例](./RBAC_USAGE_EXAMPLES.md) - 代码示例
- [后端完成总结](./RBAC_BACKEND_COMPLETED.md) - 技术细节

## 🛠️ 故障排除

### 问题1: 权限不足

```
错误: 您没有 'job.create' 权限
解决: 联系项目管理员为您添加该权限
```

### 问题2: 看不到某些功能

```
原因: 项目管理员禁用了该功能的可见性
解决: 联系项目管理员为您开启权限
```

### 问题3: 无法访问项目

```
原因: 您不是该项目的成员
解决: 联系admin将您添加到项目中
```

## 📞 技术支持

遇到问题请查看:
1. 完整文档: `docs/RBAC_README.md`
2. 检查日志输出
3. 验证MySQL配置

---

**版本**: v2.0 (RBAC简化版)  
**最后更新**: 2025-11-29