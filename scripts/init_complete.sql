-- Qunkong 数据库完整初始化脚本
-- 创建时间: 2025-11-28
-- 包含所有表结构和索引

-- 创建数据库
CREATE DATABASE IF NOT EXISTS qunkong CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE qunkong;

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
    status VARCHAR(20) DEFAULT 'OFFLINE',
    project_id INT,
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
    INDEX idx_last_heartbeat (last_heartbeat),
    INDEX idx_project_id (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Agent 系统信息表
CREATE TABLE IF NOT EXISTS agent_system_info (
    agent_id VARCHAR(64) PRIMARY KEY,
    hostname VARCHAR(255),
    ip_address VARCHAR(45),
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 执行历史表
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
    INDEX idx_start_time (start_time),
    INDEX idx_status (status),
    INDEX idx_project_id (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
    role VARCHAR(20) DEFAULT 'user',
    default_tenant_id INT DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    login_count INT DEFAULT 0,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_default_tenant_id (default_tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户权限表
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 租户管理表
-- ============================================================

-- 租户表
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 租户成员表
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 租户资源使用统计表
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 项目管理表
-- ============================================================

-- 项目表
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_code VARCHAR(50) UNIQUE NOT NULL,
    project_name VARCHAR(100) NOT NULL,
    description TEXT,
    tenant_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    INDEX idx_project_code (project_code),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 项目成员表
CREATE TABLE IF NOT EXISTS project_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    role VARCHAR(50) DEFAULT 'project_member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invited_by INT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (invited_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY unique_project_user (project_id, user_id),
    INDEX idx_project_id (project_id),
    INDEX idx_user_id (user_id),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
    INDEX idx_created_at (created_at),
    INDEX idx_project_id (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 作业主机组表
CREATE TABLE IF NOT EXISTS simple_job_host_groups (
    id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL,
    group_name VARCHAR(255) NOT NULL,
    host_ids JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES simple_jobs(id) ON DELETE CASCADE,
    INDEX idx_job_id (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 作业变量表
CREATE TABLE IF NOT EXISTS simple_job_variables (
    id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL,
    var_name VARCHAR(100) NOT NULL,
    var_value TEXT,
    var_type VARCHAR(50) DEFAULT 'string',
    is_sensitive BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES simple_jobs(id) ON DELETE CASCADE,
    UNIQUE KEY unique_job_var (job_id, var_name),
    INDEX idx_job_id (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 作业步骤表
CREATE TABLE IF NOT EXISTS simple_job_steps (
    id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL,
    step_num INT NOT NULL,
    step_name VARCHAR(255) NOT NULL,
    step_type VARCHAR(50) DEFAULT 'script',
    script_content TEXT,
    timeout INT DEFAULT 300,
    target_host_group VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES simple_jobs(id) ON DELETE CASCADE,
    UNIQUE KEY unique_job_step (job_id, step_num),
    INDEX idx_job_id (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 作业执行历史表
CREATE TABLE IF NOT EXISTS simple_job_executions (
    id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    start_time DATETIME,
    end_time DATETIME,
    current_step INT DEFAULT 0,
    total_steps INT DEFAULT 0,
    runtime_vars JSON,
    results JSON,
    logs TEXT,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES simple_jobs(id) ON DELETE CASCADE,
    INDEX idx_job_id (job_id),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 说明
-- ============================================================
-- 1. 所有表使用 utf8mb4 字符集，支持emoji和特殊字符
-- 2. agents 表增加了 os_type 字段用于存储操作系统类型
-- 3. 外键约束确保数据一致性
-- 4. 索引优化查询性能
-- 5. 支持多租户、多项目隔离

