-- SQL性能优化脚本
-- 创建时间: 2025-11-28
-- 说明: 添加复合索引和优化查询性能

USE qunkong;

-- ============================================================
-- 1. 添加复合索引优化联表查询
-- ============================================================

-- 优化 get_agent_system_info 的 LEFT JOIN 查询
-- 由于经常通过 agent_id JOIN 查询，确保主键索引存在
-- PRIMARY KEY 已存在，无需额外索引

-- 优化 agents 表的常用查询组合
ALTER TABLE agents 
ADD INDEX IF NOT EXISTS idx_status_last_heartbeat (status, last_heartbeat);

-- 优化按项目和状态查询
ALTER TABLE agents 
ADD INDEX IF NOT EXISTS idx_project_status (project_id, status);

-- ============================================================
-- 2. 优化 JSON 字段查询（MySQL 5.7+）
-- ============================================================

-- 如果需要查询 JSON 字段中的特定值，可以创建虚拟列和索引
-- 示例：按操作系统类型查询
-- ALTER TABLE agent_system_info 
-- ADD COLUMN os_name VARCHAR(100) AS (JSON_UNQUOTE(JSON_EXTRACT(system_info, '$.os'))) VIRTUAL,
-- ADD INDEX idx_os_name (os_name);

-- ============================================================
-- 3. 分析表统计信息（提高查询优化器效率）
-- ============================================================

ANALYZE TABLE agents;
ANALYZE TABLE agent_system_info;
ANALYZE TABLE execution_history;
ANALYZE TABLE simple_jobs;
ANALYZE TABLE simple_job_executions;

-- ============================================================
-- 4. 查看当前索引使用情况
-- ============================================================

-- 查看 agents 表索引
SHOW INDEX FROM agents;

-- 查看 agent_system_info 表索引
SHOW INDEX FROM agent_system_info;

-- ============================================================
-- 5. 性能优化建议
-- ============================================================

/*
1. 定期清理历史数据
   - 设置执行历史保留天数（如30天）
   - 使用分区表存储历史数据

2. 使用连接池
   - 减少连接建立开销
   - 当前代码中每次查询都创建新连接，建议使用连接池

3. 批量操作
   - 使用批量INSERT/UPDATE减少网络往返

4. 读写分离（生产环境）
   - 主库写入，从库读取
   - 减轻主库压力

5. 缓存策略
   - 已实现：内存缓存实时资源信息（30秒TTL）
   - 可扩展：Redis缓存热点数据

6. 查询优化
   - 使用 EXPLAIN 分析慢查询
   - 避免 SELECT *，只查询需要的字段
   - 合理使用 LIMIT

7. 数据库配置优化
   - innodb_buffer_pool_size（建议设置为系统内存的50-70%）
   - max_connections（根据实际并发调整）
   - query_cache（MySQL 8.0已移除）
*/

-- ============================================================
-- 6. 慢查询监控
-- ============================================================

-- 启用慢查询日志
SET GLOBAL slow_query_log = 1;
SET GLOBAL long_query_time = 1;  -- 记录执行时间超过1秒的查询
SET GLOBAL log_queries_not_using_indexes = 1;  -- 记录未使用索引的查询

-- 查看慢查询日志位置
SHOW VARIABLES LIKE 'slow_query_log_file';

-- 查看当前慢查询数量
SHOW GLOBAL STATUS LIKE 'Slow_queries';

