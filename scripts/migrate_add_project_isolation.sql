-- 数据库迁移脚本：为现有数据库添加项目隔离字段
-- 使用说明：如果你的数据库已经存在且没有project_id字段，运行此脚本
-- 如果是新数据库，程序启动时会自动创建包含project_id的表结构

-- 注意：MySQL不支持 IF NOT EXISTS 在 ALTER TABLE ADD COLUMN 中
-- 请确保在运行前备份数据库

-- 1. 为 agents 表添加 project_id（可为NULL，允许公共Agent池）
-- 如果字段已存在会报错，可以忽略
ALTER TABLE agents ADD COLUMN project_id INT AFTER status;
ALTER TABLE agents ADD INDEX idx_project_id (project_id);

-- 2. 为 execution_history 表添加 project_id（可为NULL）
ALTER TABLE execution_history ADD COLUMN project_id INT AFTER target_hosts;
ALTER TABLE execution_history ADD INDEX idx_project_id (project_id);

-- 3. 为 simple_jobs 表添加 project_id（NOT NULL，必须属于项目）
-- 先添加字段允许NULL，更新数据后再设置NOT NULL
ALTER TABLE simple_jobs ADD COLUMN project_id INT AFTER description;
UPDATE simple_jobs SET project_id = 1 WHERE project_id IS NULL;
-- ALTER TABLE simple_jobs MODIFY COLUMN project_id INT NOT NULL;
ALTER TABLE simple_jobs ADD INDEX idx_project_id (project_id);

-- 4. 为 simple_job_executions 表添加 project_id
ALTER TABLE simple_job_executions ADD COLUMN project_id INT AFTER job_id;
UPDATE simple_job_executions SET project_id = 1 WHERE project_id IS NULL;
-- ALTER TABLE simple_job_executions MODIFY COLUMN project_id INT NOT NULL;
ALTER TABLE simple_job_executions ADD INDEX idx_project_id (project_id);

-- 5. 为 job_templates 表添加 project_id
ALTER TABLE job_templates ADD COLUMN project_id INT AFTER description;
UPDATE job_templates SET project_id = 1 WHERE project_id IS NULL;
-- ALTER TABLE job_templates MODIFY COLUMN project_id INT NOT NULL;
ALTER TABLE job_templates ADD INDEX idx_project_id (project_id);

-- 6. 为 job_instances 表添加 project_id
ALTER TABLE job_instances ADD COLUMN project_id INT AFTER description;
UPDATE job_instances SET project_id = 1 WHERE project_id IS NULL;
-- ALTER TABLE job_instances MODIFY COLUMN project_id INT NOT NULL;
ALTER TABLE job_instances ADD INDEX idx_project_id (project_id);

-- 7. 为 job_step_executions 表添加 project_id
ALTER TABLE job_step_executions ADD COLUMN project_id INT AFTER job_instance_id;
UPDATE job_step_executions SET project_id = 1 WHERE project_id IS NULL;
-- ALTER TABLE job_step_executions MODIFY COLUMN project_id INT NOT NULL;
ALTER TABLE job_step_executions ADD INDEX idx_project_id (project_id);

-- 完成提示
SELECT '项目隔离字段添加完成！' AS status;
SELECT '注意：现有数据已关联到项目ID=1，请根据实际情况调整' AS notice;
