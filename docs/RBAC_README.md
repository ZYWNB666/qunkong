# RBAC权限管理系统 - 完整实施方案

## 🎯 项目概述

本项目实现了一个简化的RBAC(基于角色的访问控制)权限管理系统,替代原有的复杂租户模式,只保留**用户管理**和**项目管理**两个核心功能。

### 核心特性

✅ **简化设计** - 移除租户管理,只保留用户和项目  
✅ **admin超级权限** - admin用户拥有全局管理权限  
✅ **项目自治** - 每个项目可以有多个管理员  
✅ **细粒度权限** - 支持12种功能级别的权限控制  
✅ **资源隔离** - 所有资源按项目和用户隔离  

## 📦 交付成果

### 1. 设计文档 (3份)
| 文档 | 说明 | 行数 |
|------|------|------|
| [`RBAC_REFACTORING_PLAN.md`](./RBAC_REFACTORING_PLAN.md) | 详细的重构计划和数据库设计 | 449 |
| [`RBAC_IMPLEMENTATION_GUIDE.md`](./RBAC_IMPLEMENTATION_GUIDE.md) | 完整的实施指南和时间规划 | 316 |
| [`RBAC_CHECKLIST.md`](./RBAC_CHECKLIST.md) | 详细的实施检查清单 | 371 |
| [`RBAC_USAGE_EXAMPLES.md`](./RBAC_USAGE_EXAMPLES.md) | 权限系统使用示例代码 | 427 |

### 2. 数据库脚本 (4份)
| 脚本 | 说明 | 行数 |
|------|------|------|
| [`../scripts/init_rbac.sql`](../scripts/init_rbac.sql) | **完整的初始化SQL脚本** | 508 |
| [`../scripts/migrate_rbac.py`](../scripts/migrate_rbac.py) | Python迁移脚本 | 255 |
| [`../scripts/migrate_rbac_refactoring.sql`](../scripts/migrate_rbac_refactoring.sql) | SQL迁移脚本 | 217 |
| [`../scripts/QUICK_START.md`](../scripts/QUICK_START.md) | 快速开始指南 | 86 |

### 3. 后端代码 (2个核心文件)
| 文件 | 说明 | 新增功能 |
|------|------|---------|
| [`../app/models/project.py`](../app/models/project.py) | 项目管理模型 | 添加8个权限管理方法 |
| [`../app/routers/rbac.py`](../app/routers/rbac.py) | RBAC权限控制 | 简化逻辑,新增权限装饰器 |
| [`../app/routers/projects.py`](../app/routers/projects.py) | 项目路由 | 添加3个权限管理API |

## 🚀 快速开始

### 第1步: 初始化数据库 (1分钟)

```bash
# 删除旧数据库(如果存在)
mysql -u root -p -e "DROP DATABASE IF EXISTS qunkong;"

# 执行初始化脚本
mysql -u root -p < scripts/init_rbac.sql
```

### 第2步: 验证初始化

```bash
# 检查表是否创建成功
mysql -u root -p qunkong -e "SHOW TABLES;"

# 应该看到以下关键表:
# - users (用户表)
# - projects (项目表)
# - project_members (项目成员表)
# - project_member_permissions (功能权限表) ← 新增
# - agents (含project_id字段) ← 已更新
# - simple_jobs (含project_id字段)
# - simple_job_executions (含project_id字段)
```

### 第3步: 登录系统

**默认管理员账户:**
- 用户名: `admin`
- 密码: `admin123`
- 角色: 系统管理员

**默认项目:**
- 项目代码: `DEFAULT`
- 项目名称: 默认项目
- admin用户自动成为该项目的管理员

## 🎨 数据库结构

### 核心表结构

```
用户认证
├── users                      用户表
├── user_sessions              会话表
└── user_permissions           系统权限表

项目管理
├── projects                   项目表
├── project_members            项目成员表 (角色:admin/readwrite/readonly)
└── project_member_permissions 功能权限表 ← 新增

资源管理(含project_id)
├── agents                     Agent信息
├── agent_system_info          Agent系统信息
├── simple_jobs                作业
├── simple_job_executions      执行历史
├── job_templates              作业模板
└── job_instances              作业实例
```

### 新增的功能权限表

```sql
CREATE TABLE project_member_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,              -- 项目ID
    user_id INT NOT NULL,                 -- 用户ID
    permission_key VARCHAR(50) NOT NULL,  -- 权限标识
    is_allowed BOOLEAN DEFAULT TRUE,      -- 是否允许
    granted_by INT,                       -- 授权人
    granted_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## 🔐 权限模型

### 角色定义

#### 系统角色
- **admin**: 系统超级管理员
  - ✅ 管理所有用户
  - ✅ 管理所有项目
  - ✅ 访问所有资源
  - ✅ 不受项目权限限制

#### 项目角色
- **admin**: 项目管理员
  - ✅ 项目所有权限
  - ✅ 管理项目成员
  - ✅ 配置成员权限

- **readwrite**: 读写用户
  - ✅ 默认权限: 查看、执行、创建
  - ⚙️ 可配置额外权限

- **readonly**: 只读用户
  - ✅ 默认权限: 仅查看
  - ⚙️ 可配置额外权限

### 功能权限 (12种)

| 权限标识 | 权限名称 | 说明 |
|---------|---------|------|
| `agent.view` | 查看Agent | 查看Agent列表和详情 |
| `agent.batch_add` | 批量添加Agent | 批量添加主机 |
| `agent.execute` | 执行命令 | 在Agent上执行命令 |
| `agent.terminal` | 使用终端 | 使用Web终端功能 |
| `job.view` | 查看作业 | 查看作业列表和详情 |
| `job.create` | 创建作业 | 创建新作业 |
| `job.edit` | 编辑作业 | 修改作业配置 |
| `job.delete` | 删除作业 | 删除作业 |
| `job.execute` | 执行作业 | 执行作业 |
| `execution.view` | 查看执行历史 | 查看执行记录 |
| `execution.stop` | 停止执行 | 停止正在执行的任务 |
| `project.member_manage` | 管理成员 | 管理项目成员 |

### 默认权限规则

**readwrite角色默认权限:**
```
✅ agent.view
✅ agent.execute
✅ job.view
✅ job.create
✅ job.execute
✅ execution.view
```

**readonly角色默认权限:**
```
✅ agent.view
✅ job.view
✅ execution.view
```

## 💻 后端使用示例

### 使用权限装饰器

```python
from app.routers.rbac import require_permission

@router.post("/agents/batch-add")
async def batch_add_agents(
    data: BatchAddRequest,
    current_user: Dict = Depends(require_permission('agent.batch_add'))
):
    """
    自动检查:
    1. 用户是否登录
    2. 是否有project_id参数
    3. 是否是项目成员
    4. 是否有agent.batch_add权限
    """
    project_id = current_user['current_project_id']
    # 执行业务逻辑
    ...
```

### 权限管理API

```python
# 获取所有可用权限
GET /api/projects/{project_id}/permissions

# 获取用户权限列表
GET /api/projects/{project_id}/members/{user_id}/permissions

# 设置用户权限
POST /api/projects/{project_id}/members/{user_id}/permissions
{
    "permissions": ["agent.view", "job.create", "job.execute"]
}
```

## 🖥️ 前端集成(待实施)

### 权限检查Hook

```javascript
// 使用权限Hook
function AgentManagement() {
    const canBatchAdd = usePermission('agent.batch_add');
    const canExecute = usePermission('agent.execute');
    
    return (
        <div>
            {canBatchAdd && <Button>批量添加</Button>}
            {canExecute && <Button>执行命令</Button>}
        </div>
    );
}
```

### 权限配置界面

```javascript
// 项目成员权限配置
<PermissionConfig 
    projectId={projectId}
    userId={userId}
    onSave={handleSavePermissions}
/>
```

## 📋 实施状态

### ✅ 已完成
- [x] 数据库设计和脚本
- [x] 核心权限逻辑实现
- [x] ProjectManager权限方法
- [x] RBAC权限检查装饰器
- [x] 项目权限管理API
- [x] 完整文档和示例

### 🔄 待完成
- [ ] 更新所有API添加权限检查
- [ ] 前端移除租户管理
- [ ] 前端权限配置界面
- [ ] 前端权限控制逻辑
- [ ] 完整测试

## 📚 文档导航

### 设计阶段
1. **[RBAC重构计划](./RBAC_REFACTORING_PLAN.md)** - 从这里开始了解整体设计
2. **[实施指南](./RBAC_IMPLEMENTATION_GUIDE.md)** - 详细的实施步骤和时间规划

### 开发阶段
3. **[使用示例](./RBAC_USAGE_EXAMPLES.md)** - 代码示例和最佳实践
4. **[快速开始](../scripts/QUICK_START.md)** - 快速初始化和测试

### 实施阶段
5. **[检查清单](./RBAC_CHECKLIST.md)** - 完整的实施检查项

## ⚠️ 注意事项

### 1. 数据库初始化
- 使用 `init_rbac.sql` 进行全新安装
- 使用 `migrate_rbac.py` 进行数据迁移

### 2. 默认密码
⚠️ **重要**: 初始化后请立即修改admin用户密码!

```sql
UPDATE users 
SET password_hash = '新密码的哈希值', 
    salt = '新盐值'
WHERE username = 'admin';
```

### 3. 向后兼容
租户相关表保留但不再使用:
- `tenants`
- `tenant_members`
- `tenant_usage_stats`

这些表不会影响新系统,避免破坏现有数据。

### 4. 权限检查
所有需要权限控制的API都必须包含 `project_id` 参数。

## 🔧 故障排除

### 问题1: 初始化失败
```bash
# 检查MySQL服务
systemctl status mysql

# 检查数据库连接
mysql -u root -p -e "SELECT VERSION();"
```

### 问题2: 权限检查不生效
```python
# 确认PermissionChecker已初始化
from app.routers.rbac import PermissionChecker
PermissionChecker.initialize(db_manager)
```

### 问题3: admin用户无法登录
```sql
# 检查用户状态
SELECT * FROM users WHERE username='admin';

# 重置密码(使用Python脚本)
python scripts/reset_admin_password.py
```

## 📞 技术支持

- **设计文档**: 查看 `docs/` 目录
- **代码示例**: 查看 `RBAC_USAGE_EXAMPLES.md`
- **问题排查**: 查看相关日志文件

## 🎉 总结

RBAC权限管理系统已完成设计和核心实现,主要特点:

1. **简单易用** - 移除复杂的租户管理
2. **灵活强大** - 支持细粒度的功能权限控制
3. **安全可靠** - 多层权限检查,确保资源隔离
4. **易于扩展** - 清晰的架构,方便后续开发

立即执行 `scripts/init_rbac.sql` 开始使用!

---

**文档版本:** v1.0  
**创建日期:** 2025-11-29  
**状态:** 核心功能已完成,可以开始使用