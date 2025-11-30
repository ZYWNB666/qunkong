# RBAC用户权限管理重构计划

## 一、重构目标

### 1.1 核心原则
- **简化设计**:只保留用户管理和项目管理,移除租户管理
- **admin超级权限**:admin用户独立于所有项目,拥有全局管理权限
- **项目自治**:每个项目可以有多个管理员,管理员完全控制项目
- **细粒度权限**:支持功能级别的权限控制(如批量添加主机、执行作业等)
- **资源隔离**:所有资源(作业、执行历史、agent等)按项目和用户隔离

### 1.2 角色定义

#### 系统角色
- **admin**: 系统超级管理员
  - 可以管理所有用户
  - 可以访问和管理所有项目
  - 可以创建项目并分配管理员
  - 独立于项目权限体系之外

#### 项目角色
- **admin**: 项目管理员
  - 拥有项目所有权限
  - 可以管理项目成员
  - 可以配置成员的功能权限
  - 可以管理项目的所有资源
  
- **readwrite**: 读写用户
  - 可以查看项目资源
  - 可以创建和执行作业
  - 可以管理自己创建的资源
  - 功能权限受项目管理员控制
  
- **readonly**: 只读用户
  - 只能查看项目资源
  - 不能创建、修改、删除资源
  - 功能权限受项目管理员控制

## 二、数据库设计

### 2.1 保留的表

#### users表 (已存在,无需修改)
```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(32) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',  -- 'admin' 或 'user'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    login_count INT DEFAULT 0
);
```

#### projects表 (已存在,无需修改)
```sql
CREATE TABLE projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_code VARCHAR(50) UNIQUE NOT NULL,
    project_name VARCHAR(100) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### project_members表 (已存在,需要调整)
```sql
CREATE TABLE project_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    role VARCHAR(50) DEFAULT 'readonly',  -- 'admin', 'readwrite', 'readonly'
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invited_by INT,
    status VARCHAR(20) DEFAULT 'active',
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    UNIQUE KEY unique_project_user (project_id, user_id)
);
```

### 2.2 新增的表

#### project_member_permissions表 (新建)
用于存储项目成员的功能权限配置

```sql
CREATE TABLE project_member_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    permission_key VARCHAR(50) NOT NULL,  -- 功能权限标识
    is_allowed BOOLEAN DEFAULT TRUE,      -- 是否允许
    granted_by INT,                       -- 授予权限的管理员
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users (id) ON DELETE SET NULL,
    UNIQUE KEY unique_project_user_permission (project_id, user_id, permission_key),
    INDEX idx_project_user (project_id, user_id)
);
```

**功能权限标识 (permission_key):**
- `agent.view` - 查看Agent
- `agent.batch_add` - 批量添加Agent
- `agent.execute` - 在Agent上执行命令
- `agent.terminal` - 使用终端功能
- `job.view` - 查看作业
- `job.create` - 创建作业
- `job.edit` - 编辑作业
- `job.delete` - 删除作业
- `job.execute` - 执行作业
- `execution.view` - 查看执行历史
- `execution.stop` - 停止执行
- `project.member_manage` - 管理项目成员(仅admin)

### 2.3 已有表的project_id字段检查

以下表已经有project_id,无需修改:
- ✅ `simple_jobs` - 有project_id
- ✅ `simple_job_executions` - 有project_id  
- ✅ `job_templates` - 有project_id
- ✅ `job_instances` - 有project_id
- ✅ `job_step_executions` - 有project_id

需要添加project_id的表:
- ❌ `agents` - 需要添加project_id字段
- ❌ `agent_system_info` - 需要添加project_id字段

### 2.4 租户相关表处理

**保留但不再使用:**
- `tenants` - 保留表结构,避免破坏现有数据
- `tenant_members` - 保留表结构
- `tenant_usage_stats` - 保留表结构

**移除对租户的依赖:**
- 不再检查租户权限
- 不再使用tenant_id进行数据过滤
- 前端移除租户管理界面

## 三、实施步骤

### 3.1 数据库迁移

#### 步骤1: 创建新表
```sql
-- 创建项目成员权限表
CREATE TABLE IF NOT EXISTS project_member_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    permission_key VARCHAR(50) NOT NULL,
    is_allowed BOOLEAN DEFAULT TRUE,
    granted_by INT,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users (id) ON DELETE SET NULL,
    UNIQUE KEY unique_project_user_permission (project_id, user_id, permission_key),
    INDEX idx_project_user (project_id, user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 步骤2: 为agents表添加project_id
```sql
-- 检查agents表是否有project_id字段
ALTER TABLE agents ADD COLUMN project_id INT DEFAULT NULL AFTER tenant_id;
ALTER TABLE agents ADD INDEX idx_project_id (project_id);

-- 检查agent_system_info表是否有project_id字段
ALTER TABLE agent_system_info ADD COLUMN project_id INT DEFAULT NULL;
```

### 3.2 后端代码重构

#### 1. 更新权限模型 (`app/models/project.py`)
- ✅ 已有项目基本功能
- 新增功能权限管理方法

#### 2. 更新RBAC权限检查 (`app/routers/rbac.py`)
- 简化权限检查逻辑,移除租户检查
- 新增功能权限检查方法
- 更新依赖注入函数

#### 3. 更新API路由
需要更新的路由文件:
- `app/routers/agents.py` - Agent管理API
- `app/routers/simple_jobs.py` - 作业管理API
- `app/routers/jobs.py` - 复杂作业API
- `app/routers/projects.py` - 项目管理API
- `app/routers/users.py` - 用户管理API

#### 4. 更新数据库模型
- `app/models/__init__.py` - 数据库管理器
- 新增功能权限相关方法

### 3.3 前端代码重构

#### 1. 移除租户管理
- 删除租户选择器组件
- 删除租户管理页面
- 更新导航菜单

#### 2. 添加功能权限控制
- 创建权限配置组件
- 在项目管理页面添加成员权限配置
- 根据权限控制功能按钮可见性

#### 3. 更新API调用
- 移除tenant_id参数
- 确保所有API调用包含project_id
- 更新错误处理

## 四、权限控制逻辑

### 4.1 访问控制流程

```
用户请求 API
    ↓
1. 身份验证 (JWT Token)
    ↓
2. 获取用户角色
    ↓
3. admin用户? 
    ├─ 是 → 允许访问所有资源
    └─ 否 → 继续检查
        ↓
4. 检查项目成员关系
    ├─ 不是成员 → 拒绝访问 (403)
    └─ 是成员 → 继续检查
        ↓
5. 检查项目角色
    ├─ admin → 允许所有项目操作
    ├─ readwrite → 检查功能权限
    └─ readonly → 只读访问
        ↓
6. 检查功能权限 (project_member_permissions)
    ├─ 有权限 → 允许操作
    └─ 无权限 → 拒绝访问 (403)
```

### 4.2 默认权限规则

#### admin角色 (项目管理员)
- 拥有项目所有权限,不受功能权限表限制
- 可以管理项目成员
- 可以配置其他成员的功能权限

#### readwrite角色
默认权限:
- ✅ `agent.view`
- ✅ `agent.execute`
- ✅ `job.view`
- ✅ `job.create`
- ✅ `job.edit` (仅自己创建的)
- ✅ `job.execute`
- ✅ `execution.view`

可选权限(由管理员配置):
- `agent.batch_add`
- `agent.terminal`
- `job.delete`
- `execution.stop`

#### readonly角色
默认权限:
- ✅ `agent.view`
- ✅ `job.view`
- ✅ `execution.view`

所有其他权限默认禁止

## 五、API权限要求

### 5.1 用户管理API (`/api/users`)
- **GET /api/users** - 仅admin
- **POST /api/users** - 仅admin
- **PUT /api/users/{id}** - 仅admin
- **DELETE /api/users/{id}** - 仅admin

### 5.2 项目管理API (`/api/projects`)
- **GET /api/projects** - 所有用户(仅返回有权限的项目)
- **POST /api/projects** - 仅admin
- **PUT /api/projects/{id}** - admin或项目admin
- **DELETE /api/projects/{id}** - admin或项目admin
- **GET /api/projects/{id}/members** - 项目成员
- **POST /api/projects/{id}/members** - admin或项目admin
- **DELETE /api/projects/{id}/members/{user_id}** - admin或项目admin

### 5.3 Agent管理API (`/api/agents`)
- **GET /api/agents** - 项目成员 + `agent.view`
- **POST /api/agents/batch-add** - 项目成员 + `agent.batch_add`
- **POST /api/agents/{id}/execute** - 项目成员 + `agent.execute`
- **POST /api/agents/{id}/terminal** - 项目成员 + `agent.terminal`

### 5.4 作业管理API (`/api/simple-jobs`)
- **GET /api/simple-jobs** - 项目成员 + `job.view`
- **POST /api/simple-jobs** - 项目成员 + `job.create`
- **PUT /api/simple-jobs/{id}** - 项目成员 + `job.edit` (或创建者)
- **DELETE /api/simple-jobs/{id}** - 项目成员 + `job.delete` (或创建者)
- **POST /api/simple-jobs/{id}/execute** - 项目成员 + `job.execute`

### 5.5 执行历史API (`/api/simple-jobs/executions`)
- **GET /api/simple-jobs/executions** - 项目成员 + `execution.view`
- **GET /api/simple-jobs/executions/{id}** - 项目成员 + `execution.view`
- **POST /api/simple-jobs/executions/{id}/stop** - 项目成员 + `execution.stop`

## 六、实施计划时间表

### Phase 1: 数据库准备 (预计1天)
- [x] 创建数据库迁移脚本
- [ ] 创建project_member_permissions表
- [ ] 为agents表添加project_id字段
- [ ] 测试数据库迁移

### Phase 2: 后端重构 (预计2-3天)
- [ ] 更新ProjectManager添加权限管理方法
- [ ] 重构RBAC权限检查逻辑
- [ ] 更新所有API路由添加权限检查
- [ ] 添加单元测试

### Phase 3: 前端重构 (预计2-3天)
- [ ] 移除租户管理相关代码
- [ ] 实现功能权限配置界面
- [ ] 更新所有组件的权限控制
- [ ] 测试UI交互

### Phase 4: 测试和优化 (预计1-2天)
- [ ] 集成测试
- [ ] 性能测试
- [ ] 安全测试
- [ ] 文档更新

## 七、注意事项

### 7.1 向后兼容性
- 保留租户相关表结构,避免破坏现有数据
- 逐步迁移,确保平滑过渡
- 提供数据迁移工具

### 7.2 安全考虑
- 所有API都必须进行权限检查
- 敏感操作需要二次确认
- 记录所有权限变更的审计日志

### 7.3 性能优化
- 权限检查结果缓存
- 批量权限查询优化
- 数据库索引优化

## 八、回滚方案

如果重构出现问题,回滚步骤:
1. 恢复数据库备份
2. 回滚代码到重构前版本
3. 清除缓存和临时数据
4. 验证系统功能正常

## 九、成功标准

重构成功的标准:
- ✅ 所有API都有正确的权限控制
- ✅ admin用户可以管理所有资源
- ✅ 项目管理员可以完全控制项目
- ✅ 普通用户只能访问有权限的资源
- ✅ 功能权限配置生效
- ✅ 前端正确显示/隐藏功能按钮
- ✅ 所有测试通过
- ✅ 性能无明显下降