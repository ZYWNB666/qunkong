-- ============================================================
-- Qunkong RBAC权限管理系统 - 完整数据库初始化脚本
-- 创建时间: 2025-11-29
-- 版本: v2.0 (RBAC简化版)
-- 说明: 简化的RBAC模型,只保留用户管理和项目管理
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS qunkong CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE qunkong;

SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- 用户认证相关表
-- ============================================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(32) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' COMMENT 'admin:系统管理员, user:普通用户',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    login_count INT DEFAULT 0,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 用户会话表
CREATE TABLE IF NOT EXISTS user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_token_hash (token_hash),
    INDEX idx_user_id (user_id),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话表';

-- 用户权限表(保留,用于系统级权限)
CREATE TABLE IF NOT EXISTS user_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    permission VARCHAR(50) NOT NULL,
    resource VARCHAR(100),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY unique_user_permission (user_id, permission, resource),
    INDEX idx_user_id (user_id),
    INDEX idx_permission (permission)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户系统权限表';

-- ============================================================
-- 项目管理表
-- ============================================================

-- 项目表
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_code VARCHAR(50) UNIQUE NOT NULL,
    project_name VARCHAR(100) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_project_code (project_code),
    INDEX idx_status (status),
    INDEX idx_created_by (created_by),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目表';

-- 项目成员表
CREATE TABLE IF NOT EXISTS project_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    role VARCHAR(50) DEFAULT 'readonly' COMMENT 'admin:项目管理员, readwrite:读写, readonly:只读',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invited_by INT,
    status VARCHAR(20) DEFAULT 'active',
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (invited_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY unique_project_user (project_id, user_id),
    INDEX idx_project_id (project_id),
    INDEX idx_user_id (user_id),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目成员表';

-- 项目成员功能权限表(新增)
CREATE TABLE IF NOT EXISTS project_member_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    permission_key VARCHAR(50) NOT NULL COMMENT '功能权限标识:agent.view,agent.batch_add,job.create等',
    is_allowed BOOLEAN DEFAULT TRUE COMMENT '是否允许',
    granted_by INT COMMENT '授予权限的管理员',
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY unique_project_user_permission (project_id, user_id, permission_key),
    INDEX idx_project_user (project_id, user_id),
    INDEX idx_permission_key (permission_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目成员功能权限表';

-- ============================================================
-- Agent 管理表
-- ============================================================

-- Agent 基本信息表
CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(64) PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    external_ip VARCHAR(45) DEFAULT '',
    os_type VARCHAR(50) DEFAULT 'unknown',
    os_version VARCHAR(100) DEFAULT '',
    agent_version VARCHAR(20) DEFAULT '1.0.0',
    cpu_count INT DEFAULT 0,
    memory_total BIGINT DEFAULT 0,
    disk_total BIGINT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'offline',
    project_id INT DEFAULT NULL COMMENT '所属项目ID',
    tenant_id INT DEFAULT NULL COMMENT '保留字段,不再使用',
    last_heartbeat DATETIME,
    register_time DATETIME,
    websocket_info JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_hostname (hostname),
    INDEX idx_ip_address (ip_address),
    INDEX idx_external_ip (external_ip),
    INDEX idx_os_type (os_type),
    INDEX idx_status (status),
    INDEX idx_project_id (project_id),
    INDEX idx_last_heartbeat (last_heartbeat)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent基本信息表';

-- Agent 系统信息表
CREATE TABLE IF NOT EXISTS agent_system_info (
    agent_id VARCHAR(64) PRIMARY KEY,
    hostname VARCHAR(255),
    ip_address VARCHAR(45),
    project_id INT DEFAULT NULL COMMENT '所属项目ID',
    last_heartbeat DATETIME,
    status VARCHAR(20),
    register_time DATETIME,
    system_info JSON,
    network_info JSON,
    memory_info JSON,
    disk_info JSON,
    cpu_info JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent系统信息表';

-- Agent批量安装历史记录表
CREATE TABLE IF NOT EXISTS agent_install_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL COMMENT '项目ID',
    user_id INT NOT NULL COMMENT '执行安装的用户ID',
    batch_id VARCHAR(64) NOT NULL COMMENT '批次ID',
    ip VARCHAR(50) NOT NULL COMMENT '主机IP',
    username VARCHAR(50) NOT NULL COMMENT 'SSH用户名',
    port INT NOT NULL DEFAULT 22 COMMENT 'SSH端口',
    agent_id VARCHAR(64) COMMENT '生成的Agent ID',
    status ENUM('pending', 'running', 'success', 'failed') NOT NULL DEFAULT 'pending' COMMENT '安装状态',
    message TEXT COMMENT '安装消息或错误信息',
    command_output TEXT COMMENT '命令执行输出',
    download_url VARCHAR(500) COMMENT 'Agent下载URL',
    agent_md5 VARCHAR(64) COMMENT 'Agent MD5',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_project_id (project_id),
    INDEX idx_batch_id (batch_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent批量安装历史记录';

-- ============================================================
-- 作业管理表
-- ============================================================

-- 简单作业表
CREATE TABLE IF NOT EXISTS simple_jobs (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    project_id INT NOT NULL,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_project_id (project_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简单作业表';

-- 作业主机组表
CREATE TABLE IF NOT EXISTS simple_job_host_groups (
    id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL,
    group_name VARCHAR(255) NOT NULL,
    host_ids JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES simple_jobs(id) ON DELETE CASCADE,
    INDEX idx_job_id (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作业主机组表';

-- 作业变量表
CREATE TABLE IF NOT EXISTS simple_job_variables (
    id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL,
    var_name VARCHAR(255) NOT NULL,
    var_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES simple_jobs(id) ON DELETE CASCADE,
    UNIQUE KEY unique_job_var (job_id, var_name),
    INDEX idx_job_id (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作业变量表';

-- 作业步骤表
CREATE TABLE IF NOT EXISTS simple_job_steps (
    id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL,
    step_order INT NOT NULL,
    step_name VARCHAR(255) NOT NULL,
    script_content TEXT NOT NULL,
    host_group_id VARCHAR(64),
    timeout INT DEFAULT 300,
    FOREIGN KEY (job_id) REFERENCES simple_jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (host_group_id) REFERENCES simple_job_host_groups(id) ON DELETE SET NULL,
    INDEX idx_job_id (job_id),
    INDEX idx_step_order (step_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作业步骤表';

-- 作业执行历史表
CREATE TABLE IF NOT EXISTS simple_job_executions (
    id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL,
    job_name VARCHAR(255),
    project_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    current_step INT DEFAULT 0,
    total_steps INT DEFAULT 0,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    error_message TEXT,
    execution_log JSON,
    results JSON,
    FOREIGN KEY (job_id) REFERENCES simple_jobs(id) ON DELETE CASCADE,
    INDEX idx_job_id (job_id),
    INDEX idx_project_id (project_id),
    INDEX idx_status (status),
    INDEX idx_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作业执行历史表';

-- ============================================================
-- 执行历史表(脚本执行)
-- ============================================================

CREATE TABLE IF NOT EXISTS execution_history (
    id VARCHAR(64) PRIMARY KEY,
    task_name VARCHAR(255),
    script_name VARCHAR(255),
    target_hosts JSON,
    execution_user VARCHAR(50),
    start_time DATETIME,
    end_time DATETIME,
    status VARCHAR(20),
    results JSON,
    error_message TEXT,
    project_id INT,
    INDEX idx_task_name (task_name),
    INDEX idx_project_id (project_id),
    INDEX idx_start_time (start_time),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='脚本执行历史表';

-- ============================================================
-- 作业模板表(复杂作业系统)
-- ============================================================

CREATE TABLE IF NOT EXISTS job_templates (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    project_id INT NOT NULL,
    category VARCHAR(50) DEFAULT 'custom',
    tags JSON,
    steps JSON NOT NULL,
    default_params JSON,
    timeout INT DEFAULT 7200,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    version INT DEFAULT 1,
    INDEX idx_name (name),
    INDEX idx_project_id (project_id),
    INDEX idx_category (category),
    INDEX idx_created_by (created_by),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作业模板表';

CREATE TABLE IF NOT EXISTS job_instances (
    id VARCHAR(64) PRIMARY KEY,
    template_id VARCHAR(64),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    project_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    priority INT DEFAULT 5,
    params JSON,
    target_hosts JSON,
    steps_status JSON,
    current_step INT DEFAULT 0,
    total_steps INT DEFAULT 0,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    timeout INT DEFAULT 7200,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    error_message TEXT,
    execution_log JSON,
    FOREIGN KEY (template_id) REFERENCES job_templates(id) ON DELETE SET NULL,
    INDEX idx_template_id (template_id),
    INDEX idx_project_id (project_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_created_by (created_by),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作业实例表';

CREATE TABLE IF NOT EXISTS job_step_executions (
    id VARCHAR(64) PRIMARY KEY,
    job_instance_id VARCHAR(64) NOT NULL,
    project_id INT NOT NULL,
    step_index INT NOT NULL,
    step_name VARCHAR(255) NOT NULL,
    step_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    execution_time DECIMAL(10,3),
    task_id VARCHAR(64),
    results JSON,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    FOREIGN KEY (job_instance_id) REFERENCES job_instances(id) ON DELETE CASCADE,
    INDEX idx_job_instance_id (job_instance_id),
    INDEX idx_project_id (project_id),
    INDEX idx_step_index (step_index),
    INDEX idx_status (status),
    INDEX idx_task_id (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作业步骤执行记录表';

-- ============================================================
-- 租户相关表(保留但不再使用)
-- ============================================================

CREATE TABLE IF NOT EXISTS tenants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_code VARCHAR(50) UNIQUE NOT NULL,
    tenant_name VARCHAR(100) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    max_users INT DEFAULT 10,
    max_agents INT DEFAULT 50,
    max_concurrent_jobs INT DEFAULT 10,
    storage_quota_gb INT DEFAULT 100,
    contact_name VARCHAR(100),
    contact_email VARCHAR(100),
    contact_phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT,
    INDEX idx_tenant_code (tenant_code),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户表(保留但不再使用)';

CREATE TABLE IF NOT EXISTS tenant_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    user_id INT NOT NULL,
    role VARCHAR(50) DEFAULT 'tenant_member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invited_by INT,
    status VARCHAR(20) DEFAULT 'active',
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (invited_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY unique_tenant_user (tenant_id, user_id),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_user_id (user_id),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户成员表(保留但不再使用)';

CREATE TABLE IF NOT EXISTS tenant_usage_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    stat_date DATE NOT NULL,
    active_users INT DEFAULT 0,
    active_agents INT DEFAULT 0,
    total_jobs INT DEFAULT 0,
    successful_jobs INT DEFAULT 0,
    failed_jobs INT DEFAULT 0,
    storage_used_gb DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    UNIQUE KEY unique_tenant_date (tenant_id, stat_date),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_stat_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户使用统计表(保留但不再使用)';

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 插入初始数据
-- ============================================================

-- 注意: admin用户会由后端自动创建(使用正确的PBKDF2密码哈希)
-- 见 app/models/auth.py 的 create_default_admin() 方法

-- 插入默认项目(延迟到用户创建后)
-- 使用触发器或应用启动时自动创建

-- ============================================================
-- 完成信息
-- ============================================================

SELECT '=====================================' AS '';
SELECT 'Qunkong RBAC权限管理系统' AS '';
SELECT '数据库初始化完成!' AS '';
SELECT '=====================================' AS '';
SELECT '' AS '';
SELECT '⚠️ 重要提示:' AS '';
SELECT '  admin用户和DEFAULT项目将在' AS '';
SELECT '  首次启动应用时自动创建' AS '';
SELECT '' AS '';
SELECT '默认管理员账户:' AS '';
SELECT '  用户名: admin' AS '';
SELECT '  密码: admin123' AS '';
SELECT '  ⚠️  请登录后立即修改密码!' AS '';
SELECT '' AS '';
SELECT '下一步:' AS '';
SELECT '  1. 启动应用服务(python start_backend.py)' AS '';
SELECT '  2. admin用户会自动创建' AS '';
SELECT '  3. 使用 admin/admin123 登录' AS '';
SELECT '  4. 创建更多项目和用户' AS '';
SELECT '' AS '';
SELECT '详细文档: docs/QUICK_START.md' AS '';
SELECT '=====================================' AS '';
