# 多租户和项目隔离实现方案

## 已完成的工作

### 1. 数据库结构更新 ✅

#### Agents表增强
- 添加 `tenant_id` 字段：关联租户
- 添加 `project_id` 字段：默认项目
- 添加 `tags` 字段：支持标签管理
- 添加相应索引以优化查询

#### 新增 project_agents 表
用于管理项目和Agent的多对多关系，支持细粒度权限控制：
- `project_id`: 项目ID
- `agent_id`: Agent ID
- `can_execute`: 是否允许执行作业
- `can_terminal`: 是否允许终端登录
- `assigned_by`: 分配者
- `status`: 状态（active/inactive）

#### 数据库方法
- `assign_agent_to_project()`: 分配Agent到项目
- `remove_agent_from_project()`: 从项目移除Agent
- `get_project_agents()`: 获取项目的Agent列表
- `check_agent_project_permission()`: 检查权限
- `update_agent_tenant()`: 更新Agent租户
- `update_agent_project()`: 更新Agent默认项目
- `get_all_agents()`: 支持租户和项目过滤

### 2. 批量添加Agent标签功能 ✅
- 批量安装的Agent自动添加 "batch_install" 标签
- Agent管理页面显示标签

### 3. 自定义Server URL ✅
- 支持批量安装时指定agent注册地址

## 待实现功能

### 1. API层更新

需要在 `app/routers/agents.py` 中实现：

```python
@router.get("/agents")
async def get_agents(
    project_id: Optional[int] = Query(None),
    tenant_id: Optional[int] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取Agent列表（支持租户和项目隔离）"""
    server = get_server()
    user_role = current_user['role']
    
    # 非admin用户只能看到自己有权限的项目的agents
    if user_role not in ['admin', 'super_admin']:
        # 获取用户的项目列表
        from app.routers.deps import get_project_manager
        project_mgr = get_project_manager()
        user_projects = project_mgr.get_user_projects(current_user['user_id'])
        
        # 过滤agents
        ...
    
    # Admin可以看到所有agents
    db_agents = server.db.get_all_agents(tenant_id=tenant_id, project_id=project_id)
    ...

@router.post("/agents/{agent_id}/assign-project")
async def assign_agent_to_project(
    agent_id: str,
    project_id: int,
    can_execute: bool = True,
    can_terminal: bool = True,
    current_user: Dict[str, Any] = Depends(require_permission('agent_management'))
):
    """将Agent分配给项目（仅admin）"""
    server = get_server()
    
    # 检查权限
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="权限不足")
    
    success = server.db.assign_agent_to_project(
        project_id=project_id,
        agent_id=agent_id,
        can_execute=can_execute,
        can_terminal=can_terminal,
        assigned_by=current_user['user_id']
    )
    
    return {'success': success}

@router.get("/projects/{project_id}/agents")
async def get_project_agents(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取项目的Agent列表"""
    from app.routers.deps import get_project_manager
    project_mgr = get_project_manager()
    
    # 检查用户是否有项目权限
    if not project_mgr.check_project_permission(
        current_user['user_id'], 
        project_id
    ):
        raise HTTPException(status_code=403, detail="无权访问此项目")
    
    server = get_server()
    agents = server.db.get_project_agents(project_id)
    return {'agents': agents}
```

### 2. 权限检查中间件

在执行作业和终端操作时添加权限检查：

```python
def check_agent_access(agent_id: str, project_id: int, 
                      permission_type: str, user_id: int):
    """检查用户是否有权限访问Agent"""
    server = get_server()
    
    # Admin有所有权限
    user = server.auth_manager.get_user_by_id(user_id)
    if user['role'] in ['admin', 'super_admin']:
        return True
    
    # 检查项目成员权限
    project_mgr = get_project_manager()
    if not project_mgr.check_project_permission(user_id, project_id):
        return False
    
    # 检查agent-project权限
    return server.db.check_agent_project_permission(
        agent_id, project_id, permission_type
    )
```

### 3. 前端更新

#### Agent管理页面
- 显示租户和项目信息
- 添加筛选器（按租户、项目）
- Admin可以看到"分配到项目"按钮

#### 项目管理页面
- 添加"Agent管理"标签页
- 显示项目的Agent列表
- 支持添加/移除Agent
- 配置execute/terminal权限

#### 批量添加页面
- 添加租户和项目选择器
- 自动设置新Agent的租户和项目

### 4. 资源配额管理

```python
def check_tenant_quota(tenant_id: int) -> Dict[str, Any]:
    """检查租户配额"""
    tenant_mgr = get_tenant_manager()
    tenant = tenant_mgr.get_tenant_by_id(tenant_id)
    
    # 统计当前使用
    conn = server.db._get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT COUNT(*) as count FROM agents WHERE tenant_id = %s',
        (tenant_id,)
    )
    current_agents = cursor.fetchone()['count']
    
    return {
        'max_agents': tenant['max_agents'],
        'current_agents': current_agents,
        'available': tenant['max_agents'] - current_agents
    }
```

### 5. 审计日志

记录所有Agent分配、权限变更操作：

```sql
CREATE TABLE agent_audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agent_id VARCHAR(64),
    action VARCHAR(50),
    old_value JSON,
    new_value JSON,
    performed_by INT,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_agent_id (agent_id),
    INDEX idx_performed_at (performed_at)
);
```

## 实施步骤

1. **Phase 1: 核心API** (已完成数据库层)
   - [ ] 实现Agent查询的租户过滤
   - [ ] 实现项目-Agent分配API
   - [ ] 添加权限检查中间件

2. **Phase 2: 前端集成**
   - [ ] Agent管理页面更新
   - [ ] 项目管理页面添加Agent标签
   - [ ] 添加权限配置界面

3. **Phase 3: 高级功能**
   - [ ] 配额管理
   - [ ] 审计日志
   - [ ] 统计报表

4. **Phase 4: 测试和优化**
   - [ ] 多租户隔离测试
   - [ ] 权限检查测试
   - [ ] 性能优化

## 安全考虑

1. **数据隔离**: 确保租户之间的数据完全隔离
2. **权限验证**: 所有API调用都要验证用户权限
3. **审计追踪**: 记录所有敏感操作
4. **配额限制**: 防止资源滥用

## 使用场景示例

### 场景1: 团队A只能访问自己项目的主机
```
用户: user_teamA (项目A成员)
权限: 只能看到和操作项目A分配的agents
结果: 无法看到项目B的agents，无法在项目B的agents上执行操作
```

### 场景2: Admin分配主机给多个项目
```
操作: Admin将agent_001分配给项目A和项目B
权限配置:
  - 项目A: can_execute=true, can_terminal=true
  - 项目B: can_execute=true, can_terminal=false
结果: 
  - 项目A成员可以执行作业和终端登录
  - 项目B成员只能执行作业，不能终端登录
```

### 场景3: 租户配额限制
```
租户X: max_agents=50
当前agents: 48
操作: 批量添加5台主机
结果: 前2台成功，后3台因超出配额被拒绝
```

## 性能优化建议

1. 使用Redis缓存用户权限
2. 数据库查询优化（已添加索引）
3. 实现权限结果缓存（5分钟TTL）
4. 批量操作使用事务

## 监控指标

- 各租户Agent数量
- 项目-Agent分配关系数量
- 权限检查失败次数
- API响应时间
