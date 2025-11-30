# RBAC权限系统使用示例

## 📋 概述

本文档提供RBAC权限系统的实际使用示例,帮助开发者快速集成权限检查。

## 🔐 权限检查方式

### 方式1: 使用require_permission装饰器(推荐)

最简单的方式,直接在路由中声明需要的权限:

```python
from app.routers.rbac import require_permission
from fastapi import APIRouter, Depends, Query

router = APIRouter()

@router.post("/agents/batch-add")
async def batch_add_agents(
    data: BatchAddRequest,
    current_user: Dict = Depends(require_permission('agent.batch_add'))
):
    """
    批量添加Agent
    自动检查用户是否有 agent.batch_add 权限
    project_id 会自动从Query参数获取
    """
    project_id = current_user['current_project_id']
    # 执行批量添加逻辑
    ...
```

### 方式2: 手动检查权限

如果需要更灵活的权限检查:

```python
from app.routers.rbac import PermissionChecker
from app.routers.deps import get_current_user

@router.post("/jobs/execute")
async def execute_job(
    job_id: str,
    project_id: int = Query(...),
    current_user: Dict = Depends(get_current_user)
):
    """手动检查权限"""
    checker = PermissionChecker.get_instance()
    
    # 检查是否有执行权限
    if not checker.check_permission_key(
        user_id=current_user['user_id'],
        project_id=project_id,
        permission_key='job.execute',
        user_role=current_user['role']
    ):
        raise HTTPException(403, "没有执行作业的权限")
    
    # 执行作业逻辑
    ...
```

### 方式3: 使用ProjectManager检查

在业务逻辑中检查权限:

```python
from app.models.project import ProjectManager

def check_and_execute(db, user_id, project_id, user_role):
    project_mgr = ProjectManager(db)
    
    # 检查权限
    if not project_mgr.check_permission(
        project_id=project_id,
        user_id=user_id,
        permission_key='job.create',
        user_role=user_role
    ):
        return {"error": "没有创建作业的权限"}
    
    # 执行业务逻辑
    ...
```

## 🎯 常见使用场景

### 场景1: Agent管理API

```python
from app.routers.rbac import require_permission

# 查看Agent列表 - 需要 agent.view 权限
@router.get("/agents")
async def get_agents(
    current_user: Dict = Depends(require_permission('agent.view'))
):
    project_id = current_user['current_project_id']
    # 返回该项目的agents
    agents = db.get_project_agents(project_id)
    return {'agents': agents}

# 批量添加Agent - 需要 agent.batch_add 权限
@router.post("/agents/batch-add")
async def batch_add_agents(
    data: BatchAddRequest,
    current_user: Dict = Depends(require_permission('agent.batch_add'))
):
    project_id = current_user['current_project_id']
    # 执行批量添加
    ...

# 执行命令 - 需要 agent.execute 权限
@router.post("/agents/{agent_id}/execute")
async def execute_command(
    agent_id: str,
    data: CommandRequest,
    current_user: Dict = Depends(require_permission('agent.execute'))
):
    # 执行命令
    ...
```

### 场景2: 作业管理API

```python
# 查看作业 - 需要 job.view 权限
@router.get("/simple-jobs")
async def get_jobs(
    current_user: Dict = Depends(require_permission('job.view'))
):
    project_id = current_user['current_project_id']
    jobs = job_manager.get_all_jobs(project_id=project_id)
    return {'jobs': jobs}

# 创建作业 - 需要 job.create 权限
@router.post("/simple-jobs")
async def create_job(
    data: CreateJobRequest,
    current_user: Dict = Depends(require_permission('job.create'))
):
    project_id = current_user['current_project_id']
    job_id = job_manager.create_job(
        name=data.name,
        project_id=project_id,
        created_by=current_user['user_id']
    )
    return {'job_id': job_id}

# 执行作业 - 需要 job.execute 权限
@router.post("/simple-jobs/{job_id}/execute")
async def execute_job(
    job_id: str,
    current_user: Dict = Depends(require_permission('job.execute'))
):
    # 执行作业
    ...
```

### 场景3: 项目管理员功能

```python
from app.routers.rbac import require_project_admin

# 管理项目成员 - 需要项目admin角色
@router.post("/projects/{project_id}/members")
async def add_member(
    project_id: int,
    data: MemberRequest,
    current_user: Dict = Depends(require_project_admin)
):
    """
    require_project_admin 会自动检查:
    1. 用户是否是系统admin
    2. 用户是否是项目admin
    """
    project_manager.add_project_member(
        project_id=project_id,
        user_id=data.user_id,
        role=data.role,
        invited_by=current_user['user_id']
    )
    return {'message': '成员添加成功'}
```

### 场景4: 系统管理员功能

```python
from app.routers.rbac import require_system_admin

# 用户管理 - 需要系统admin
@router.post("/users")
async def create_user(
    data: CreateUserRequest,
    current_user: Dict = Depends(require_system_admin)
):
    """只有系统管理员可以创建用户"""
    auth_manager.register_user(
        username=data.username,
        email=data.email,
        password=data.password,
        role=data.role
    )
    return {'message': '用户创建成功'}

# 创建项目 - 需要系统admin
@router.post("/projects")
async def create_project(
    data: CreateProjectRequest,
    current_user: Dict = Depends(require_system_admin)
):
    """只有系统管理员可以创建项目"""
    project = project_manager.create_project(
        project_name=data.name,
        description=data.description,
        created_by=current_user['user_id']
    )
    return {'project': project}
```

## 🔧 权限管理API使用

### 获取所有可用权限

```python
GET /api/projects/{project_id}/permissions

Response:
{
    "permissions": [
        {"key": "agent.view", "name": "查看Agent"},
        {"key": "agent.batch_add", "name": "批量添加Agent"},
        {"key": "job.create", "name": "创建作业"},
        ...
    ]
}
```

### 获取用户权限

```python
GET /api/projects/{project_id}/members/{user_id}/permissions

Response:
{
    "permissions": ["agent.view", "job.view", "job.create", "job.execute"]
}

# 如果是admin用户,返回:
{
    "permissions": ["*"]  # 表示所有权限
}
```

### 设置用户权限

```python
POST /api/projects/{project_id}/members/{user_id}/permissions
Content-Type: application/json

{
    "permissions": ["agent.view", "agent.execute", "job.view", "job.create", "job.execute"]
}

Response:
{
    "message": "权限设置成功"
}
```

## 📊 权限层级说明

### 系统角色
1. **admin** (系统管理员)
   - 拥有所有权限
   - 不受项目限制
   - 可以管理所有用户和项目

### 项目角色
1. **admin** (项目管理员)
   - 拥有项目所有权限
   - 可以管理项目成员
   - 可以配置成员权限

2. **readwrite** (读写用户)
   - 默认权限: `agent.view`, `agent.execute`, `job.view`, `job.create`, `job.execute`, `execution.view`
   - 可由项目admin添加其他权限

3. **readonly** (只读用户)
   - 默认权限: `agent.view`, `job.view`, `execution.view`
   - 可由项目admin添加其他权限

## ⚠️ 注意事项

### 1. project_id必需
所有需要权限检查的API都必须包含`project_id`参数:

```python
# ✅ 正确
@router.get("/agents")
async def get_agents(
    project_id: int = Query(...),  # 必需
    current_user: Dict = Depends(require_permission('agent.view'))
):
    ...

# ❌ 错误 - 缺少project_id
@router.get("/agents")
async def get_agents(
    current_user: Dict = Depends(require_permission('agent.view'))
):
    ...
```

### 2. admin用户特殊处理
系统admin用户拥有所有权限,不需要检查具体权限:

```python
# 系统会自动处理,无需手动判断
if current_user['role'] == 'admin':
    # 自动通过所有权限检查
```

### 3. 权限粒度
功能权限是可选的,如果没有明确设置,会使用角色的默认权限:

```python
# 用户A: readwrite角色,没有明确设置权限
# 自动拥有: agent.view, agent.execute, job.view, job.create, job.execute, execution.view

# 用户B: readwrite角色,明确设置了权限
# 只拥有明确设置的权限,覆盖默认权限
```

## 🚀 快速集成步骤

### 步骤1: 确定需要的权限
```python
# 例如: 批量添加Agent功能
permission_key = 'agent.batch_add'
```

### 步骤2: 添加权限检查
```python
@router.post("/agents/batch-add")
async def batch_add_agents(
    data: BatchAddRequest,
    current_user: Dict = Depends(require_permission('agent.batch_add'))
):
    project_id = current_user['current_project_id']
    # 业务逻辑
    ...
```

### 步骤3: 测试权限
```python
# 1. 以admin用户登录 - 应该可以访问
# 2. 以普通用户登录 - 如果没有权限,应该返回403
# 3. 配置权限后再测试 - 应该可以访问
```

## 📚 相关文档

- [RBAC重构计划](./RBAC_REFACTORING_PLAN.md) - 完整的设计文档
- [实施指南](./RBAC_IMPLEMENTATION_GUIDE.md) - 详细的实施步骤
- [检查清单](./RBAC_CHECKLIST.md) - 完整的检查项

---

**文档版本:** v1.0  
**最后更新:** 2025-11-29