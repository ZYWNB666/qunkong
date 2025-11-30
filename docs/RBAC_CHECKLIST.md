# RBAC重构实施检查清单

## ✅ 准备阶段 (已完成)

- [x] **需求分析** - 明确重构目标和原则
- [x] **数据模型设计** - 设计新的RBAC权限模型
- [x] **数据库表设计** - 定义新表和字段
- [x] **API权限定义** - 明确各API的权限要求
- [x] **迁移脚本编写** - SQL和Python版本
- [x] **文档编写** - 完整的实施指南

## 📋 实施阶段检查清单

### Phase 1: 数据库迁移

#### 迁移前检查
- [ ] 确认数据库连接配置正确
- [ ] 完成数据库完整备份
- [ ] 记录备份文件路径和时间
- [ ] 验证备份文件完整性

#### 执行迁移
- [ ] 执行 `python scripts/migrate_rbac.py`
- [ ] 检查迁移日志无错误
- [ ] 验证新表创建成功
- [ ] 验证字段添加成功
- [ ] 确认数据迁移完整

#### 迁移后验证
```sql
-- 检查project_member_permissions表
SELECT COUNT(*) FROM project_member_permissions;

-- 检查agents.project_id
SELECT COUNT(*) FROM agents WHERE project_id IS NOT NULL;

-- 检查默认项目
SELECT * FROM projects WHERE project_code = 'DEFAULT';

-- 检查默认项目管理员
SELECT u.username, pm.role 
FROM project_members pm
JOIN users u ON pm.user_id = u.id
WHERE pm.project_id = (SELECT id FROM projects WHERE project_code = 'DEFAULT');
```

### Phase 2: 后端代码更新

#### 2.1 更新数据库模型 (`app/models/project.py`)
- [ ] 添加 `grant_permission()` 方法
- [ ] 添加 `revoke_permission()` 方法
- [ ] 添加 `check_permission()` 方法
- [ ] 添加 `get_user_permissions()` 方法
- [ ] 添加 `set_user_permissions()` 方法
- [ ] 添加单元测试

#### 2.2 更新RBAC权限逻辑 (`app/routers/rbac.py`)
- [ ] 移除租户权限检查逻辑
- [ ] 简化权限检查流程
- [ ] 添加功能权限检查装饰器
- [ ] 更新依赖注入函数
- [ ] 添加权限缓存机制

#### 2.3 更新API路由

**用户管理 (`app/routers/users.py`)**
- [ ] 确保只有admin可以管理用户
- [ ] 移除租户相关参数
- [ ] 添加权限检查

**项目管理 (`app/routers/projects.py`)**
- [ ] 添加项目成员权限管理接口
- [ ] 实现权限配置API
- [ ] 添加权限查询API
- [ ] 测试项目admin权限

**Agent管理 (`app/routers/agents.py`)**
- [ ] 移除tenant_id参数
- [ ] 添加project_id必需参数
- [ ] 添加`agent.view`权限检查
- [ ] 添加`agent.batch_add`权限检查
- [ ] 添加`agent.execute`权限检查
- [ ] 添加`agent.terminal`权限检查

**作业管理 (`app/routers/simple_jobs.py`)**
- [ ] 确保project_id正确传递
- [ ] 添加`job.view`权限检查
- [ ] 添加`job.create`权限检查
- [ ] 添加`job.edit`权限检查
- [ ] 添加`job.delete`权限检查
- [ ] 添加`job.execute`权限检查

**执行历史 (`app/routers/simple_jobs.py`)**
- [ ] 添加`execution.view`权限检查
- [ ] 添加`execution.stop`权限检查
- [ ] 确保只返回有权限的执行记录

#### 2.4 代码审查
- [ ] 所有API都有权限检查
- [ ] 移除所有租户相关代码
- [ ] 确保project_id正确使用
- [ ] 检查错误处理逻辑
- [ ] 验证日志记录完整

### Phase 3: 前端代码更新

#### 3.1 移除租户管理
- [ ] 删除 `web/src/pages/TenantManagement.jsx`
- [ ] 从 `web/src/App.jsx` 移除租户路由
- [ ] 从导航菜单移除租户管理
- [ ] 移除租户选择器组件
- [ ] 清理租户相关状态管理

#### 3.2 添加权限配置界面
- [ ] 创建 `web/src/components/PermissionConfig.jsx`
- [ ] 创建 `web/src/pages/ProjectMemberPermissions.jsx`
- [ ] 实现权限配置表单
- [ ] 实现权限批量操作
- [ ] 添加权限变更日志

#### 3.3 实现功能权限控制
- [ ] 创建权限检查Hook `usePermission()`
- [ ] 创建权限上下文Provider
- [ ] 更新所有需要权限控制的组件
- [ ] 根据权限显示/隐藏功能按钮
- [ ] 添加权限不足提示

#### 3.4 更新API调用
- [ ] 移除所有tenant_id参数
- [ ] 确保project_id正确传递
- [ ] 更新错误处理逻辑
- [ ] 添加权限错误处理

### Phase 4: 测试验证

#### 4.1 单元测试
- [ ] 权限模型单元测试
- [ ] 权限检查逻辑测试
- [ ] API权限测试
- [ ] 前端组件测试

#### 4.2 集成测试
- [ ] admin用户全局权限测试
- [ ] 项目admin权限测试
- [ ] readwrite用户权限测试
- [ ] readonly用户权限测试

#### 4.3 功能测试
- [ ] 用户登录和认证
- [ ] 项目创建和管理
- [ ] 项目成员管理
- [ ] 权限配置和生效
- [ ] Agent管理功能
- [ ] 作业管理功能
- [ ] 执行历史查看

#### 4.4 边界测试
- [ ] 未授权访问测试
- [ ] 跨项目访问测试
- [ ] 权限变更即时生效测试
- [ ] 并发访问测试
- [ ] 异常情况处理

#### 4.5 性能测试
- [ ] 权限检查性能
- [ ] API响应时间
- [ ] 数据库查询优化
- [ ] 缓存效果验证

#### 4.6 安全测试
- [ ] 权限绕过测试
- [ ] SQL注入测试
- [ ] XSS攻击测试
- [ ] CSRF攻击测试

### Phase 5: 上线部署

#### 5.1 上线前准备
- [ ] 完成所有测试
- [ ] 准备上线文档
- [ ] 准备回滚方案
- [ ] 通知相关人员

#### 5.2 上线步骤
- [ ] 停止应用服务
- [ ] 备份生产数据库
- [ ] 执行数据库迁移
- [ ] 部署新代码
- [ ] 启动应用服务
- [ ] 验证基本功能
- [ ] 监控系统状态

#### 5.3 上线后验证
- [ ] 检查日志无异常
- [ ] 验证用户可以正常登录
- [ ] 验证权限正确生效
- [ ] 验证所有功能正常
- [ ] 收集用户反馈

#### 5.4 监控和优化
- [ ] 监控API错误率
- [ ] 监控响应时间
- [ ] 收集性能指标
- [ ] 优化慢查询
- [ ] 调整权限配置

## 🔄 回滚方案

### 情况1: 数据库迁移失败
```bash
# 停止服务
systemctl stop qunkong

# 恢复数据库
mysql -u root -p qunkong < backup_YYYYMMDD_HHMMSS.sql

# 启动服务
systemctl start qunkong
```

### 情况2: 代码部署后功能异常
```bash
# 回滚代码
git checkout <previous-commit>

# 重启服务
systemctl restart qunkong
```

### 情况3: 权限配置错误
- 直接修改数据库恢复权限配置
- 或使用备份恢复

## 📊 进度跟踪

| 阶段 | 任务数 | 已完成 | 进度 | 预计完成时间 |
|------|--------|--------|------|-------------|
| 准备阶段 | 6 | 6 | 100% | ✅ 已完成 |
| Phase 1 | 9 | 0 | 0% | - |
| Phase 2 | 25 | 0 | 0% | - |
| Phase 3 | 14 | 0 | 0% | - |
| Phase 4 | 24 | 0 | 0% | - |
| Phase 5 | 16 | 0 | 0% | - |

## 📝 注意事项

1. **备份至关重要**
   - 每个阶段前都要备份
   - 验证备份可用性
   - 记录备份位置

2. **分阶段实施**
   - 不要一次性修改太多
   - 每个阶段独立测试
   - 确认无误后继续

3. **保持沟通**
   - 及时报告进度
   - 遇到问题立即反馈
   - 记录所有变更

4. **文档同步**
   - 更新技术文档
   - 更新用户手册
   - 记录已知问题

## ✅ 验收标准

重构完成的验收标准:
- ✅ 所有API都有正确的权限控制
- ✅ admin用户可以管理所有资源
- ✅ 项目管理员可以完全控制项目
- ✅ 普通用户只能访问有权限的资源
- ✅ 功能权限配置生效
- ✅ 前端正确显示/隐藏功能按钮
- ✅ 所有测试通过
- ✅ 性能无明显下降
- ✅ 用户反馈良好
- ✅ 文档完整更新

---

**检查清单版本:** v1.0  
**创建日期:** 2025-11-29  
**最后更新:** 2025-11-29