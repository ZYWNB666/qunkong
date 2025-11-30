"""
Agent批量安装 API 路由
"""
import asyncio
import io
import json
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import paramiko
from app.routers.deps import get_current_user, get_server
from app.routers.rbac import require_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Agent批量安装"])

# 线程池，用于并发执行SSH安装任务（增加到50个并发）
executor = ThreadPoolExecutor(max_workers=50)


class HostConfig(BaseModel):
    """主机配置"""
    username: str
    ip: str
    port: int = 22
    password: Optional[str] = None


class InstallResult(BaseModel):
    """安装结果"""
    ip: str
    username: str
    port: int
    success: bool
    agent_id: Optional[str] = None
    message: str


def generate_agent_id() -> str:
    """生成Agent ID"""
    return f"agent-{uuid.uuid4().hex[:16]}"


def get_agent_install_script(agent_id: str, server_url: str, download_url: str, agent_md5: str) -> str:
    """生成Agent安装脚本"""
    script = f"""#!/bin/bash
set -e

# Agent配置
AGENT_ID="{agent_id}"
SERVER_URL="{server_url}"
DOWNLOAD_URL="{download_url}"
EXPECTED_MD5="{agent_md5}"
INSTALL_DIR="/usr/local/qunkong-agent"
SERVICE_NAME="qunkong-agent"

echo "开始安装Qunkong Agent..."
echo "Agent ID: $AGENT_ID"
echo "Server URL: $SERVER_URL"
echo "Download URL: $DOWNLOAD_URL"

# 创建安装目录
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# 下载Agent程序
echo "下载Agent程序..."
if command -v wget > /dev/null; then
    wget -O qunkong-agent $DOWNLOAD_URL
elif command -v curl > /dev/null; then
    curl -L -o qunkong-agent $DOWNLOAD_URL
else
    echo "错误: 需要wget或curl命令"
    exit 1
fi

# 验证MD5
echo "验证文件完整性..."
if command -v md5sum > /dev/null; then
    ACTUAL_MD5=$(md5sum qunkong-agent | awk '{{print $1}}')
elif command -v md5 > /dev/null; then
    ACTUAL_MD5=$(md5 -q qunkong-agent)
else
    echo "警告: 无法验证MD5，跳过校验"
    ACTUAL_MD5="$EXPECTED_MD5"
fi

if [ "$ACTUAL_MD5" != "$EXPECTED_MD5" ]; then
    echo "错误: MD5校验失败"
    echo "期望: $EXPECTED_MD5"
    echo "实际: $ACTUAL_MD5"
    exit 1
fi
echo "MD5校验通过"

# 设置执行权限
chmod +x qunkong-agent

# 创建配置文件
cat > config.json <<EOF
{{
  "agent_id": "$AGENT_ID",
  "server_url": "$SERVER_URL",
  "heartbeat_interval": 30,
  "log_level": "INFO"
}}
EOF

# 创建systemd服务文件
cat > /etc/systemd/system/${{SERVICE_NAME}}.service <<EOF
[Unit]
Description=Qunkong Agent Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/qunkong-agent
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 重载systemd并启动服务
echo "启动Agent服务..."
systemctl daemon-reload
systemctl enable ${{SERVICE_NAME}}
systemctl start ${{SERVICE_NAME}}

# 检查服务状态
if systemctl is-active --quiet ${{SERVICE_NAME}}; then
    echo "Agent安装成功并已启动"
    exit 0
else
    echo "Agent启动失败"
    systemctl status ${{SERVICE_NAME}}
    exit 1
fi
"""
    return script


def install_agent_on_host(
    host_config: HostConfig,
    ssh_key_content: Optional[str],
    server_url: str,
    agent_download_url: str,
    agent_md5: str,
    project_id: int,
    batch_id: str,
    user_id: int,
    db_connection
) -> InstallResult:
    """在单个主机上安装Agent"""
    ip = host_config.ip
    username = host_config.username
    port = host_config.port
    
    # 插入初始历史记录
    cursor = db_connection.cursor()
    cursor.execute("""
        INSERT INTO agent_install_history
        (project_id, user_id, batch_id, ip, username, port, download_url, agent_md5, status, message)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'running', '开始安装...')
    """, (project_id, user_id, batch_id, ip, username, port, agent_download_url, agent_md5))
    history_id = cursor.lastrowid
    db_connection.commit()
    
    try:
        # 生成Agent ID
        agent_id = generate_agent_id()
        
        # 创建SSH客户端
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 连接SSH
        connect_kwargs = {
            'hostname': ip,
            'port': port,
            'username': username,
            'timeout': 30,
        }
        
        if ssh_key_content:
            # 使用密钥认证
            key_file = io.StringIO(ssh_key_content)
            pkey = paramiko.RSAKey.from_private_key(key_file)
            connect_kwargs['pkey'] = pkey
        else:
            # 使用密码认证
            connect_kwargs['password'] = host_config.password
        
        logger.info(f"正在连接到 {ip}:{port} (用户: {username})")
        ssh.connect(**connect_kwargs)
        
        # 生成安装脚本
        install_script = get_agent_install_script(agent_id, server_url, agent_download_url, agent_md5)
        
        # 上传并执行安装脚本
        logger.info(f"在 {ip} 上执行安装脚本...")
        
        # 创建临时脚本文件
        script_path = f'/tmp/install_qunkong_agent_{agent_id}.sh'
        sftp = ssh.open_sftp()
        with sftp.file(script_path, 'w') as f:
            f.write(install_script)
        sftp.close()
        
        # 执行安装脚本
        stdin, stdout, stderr = ssh.exec_command(f'bash {script_path}')
        exit_code = stdout.channel.recv_exit_status()
        
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        # 清理临时文件
        ssh.exec_command(f'rm -f {script_path}')
        
        ssh.close()
        
        if exit_code == 0:
            logger.info(f"Agent安装成功: {ip} (Agent ID: {agent_id})")
            
            # 更新历史记录为成功
            cursor.execute("""
                UPDATE agent_install_history
                SET status='success', agent_id=%s, message='安装成功', command_output=%s, updated_at=NOW()
                WHERE id=%s
            """, (agent_id, output, history_id))
            db_connection.commit()
            
            # 为批量安装的agent设置project_id和添加"batch_install"标签
            try:
                cursor.execute("""
                    UPDATE agents
                    SET tags = JSON_ARRAY('batch_install'),
                        project_id = %s
                    WHERE id = %s
                """, (project_id, agent_id))
                db_connection.commit()
                logger.info(f"已为Agent {agent_id} 设置项目ID {project_id} 并添加batch_install标签")
                
                # 同时添加到project_agents表，确保权限关联
                cursor.execute("""
                    INSERT INTO project_agents (project_id, agent_id, can_execute, can_terminal, assigned_by)
                    VALUES (%s, %s, TRUE, TRUE, %s)
                    ON DUPLICATE KEY UPDATE
                    can_execute = TRUE,
                    can_terminal = TRUE,
                    status = 'active'
                """, (project_id, agent_id, user_id))
                db_connection.commit()
                logger.info(f"已将Agent {agent_id} 添加到项目 {project_id} 的权限表")
            except Exception as e:
                logger.warning(f"设置项目和标签失败: {e}")
            
            return InstallResult(
                ip=ip,
                username=username,
                port=port,
                success=True,
                agent_id=agent_id,
                message="安装成功"
            )
        else:
            logger.error(f"Agent安装失败: {ip}\n输出: {output}\n错误: {error}")
            
            # 更新历史记录为失败
            cursor.execute("""
                UPDATE agent_install_history
                SET status='failed', message=%s, command_output=%s, updated_at=NOW()
                WHERE id=%s
            """, (f"安装失败: {error or output}", output + '\n' + error, history_id))
            db_connection.commit()
            
            return InstallResult(
                ip=ip,
                username=username,
                port=port,
                success=False,
                agent_id=None,
                message=f"安装失败: {error or output}"
            )
            
    except paramiko.AuthenticationException as e:
        logger.error(f"SSH认证失败: {ip}")
        cursor.execute("""
            UPDATE agent_install_history
            SET status='failed', message='SSH认证失败，请检查用户名和密码/密钥', updated_at=NOW()
            WHERE id=%s
        """, (history_id,))
        db_connection.commit()
        return InstallResult(
            ip=ip,
            username=username,
            port=port,
            success=False,
            agent_id=None,
            message="SSH认证失败，请检查用户名和密钥"
        )
    except paramiko.SSHException as e:
        logger.error(f"SSH连接错误: {ip} - {str(e)}")
        cursor.execute("""
            UPDATE agent_install_history
            SET status='failed', message=%s, updated_at=NOW()
            WHERE id=%s
        """, (f"SSH连接错误: {str(e)}", history_id))
        db_connection.commit()
        return InstallResult(
            ip=ip,
            username=username,
            port=port,
            success=False,
            agent_id=None,
            message=f"SSH连接错误: {str(e)}"
        )
    except Exception as e:
        logger.error(f"安装Agent失败: {ip} - {str(e)}")
        cursor.execute("""
            UPDATE agent_install_history
            SET status='failed', message=%s, updated_at=NOW()
            WHERE id=%s
        """, (f"安装失败: {str(e)}", history_id))
        db_connection.commit()
        return InstallResult(
            ip=ip,
            username=username,
            port=port,
            success=False,
            agent_id=None,
            message=f"安装失败: {str(e)}"
        )


@router.post("/agents/batch-install")
async def batch_install_agents(
    auth_type: str = Form(...),
    hosts: str = Form(...),
    agent_download_url: str = Form(...),
    agent_md5: str = Form(...),
    server_url: Optional[str] = Form(None),
    ssh_key: Optional[UploadFile] = File(None),
    current_user: Dict[str, Any] = Depends(require_permission('agent.batch_add'))
):
    """批量安装Agent"""
    try:
        # 从current_user中获取project_id (由require_permission注入)
        project_id = current_user.get('current_project_id')
        if not project_id:
            raise HTTPException(status_code=400, detail="缺少项目ID")
        
        # 记录接收到的参数
        logger.info(f"批量安装请求 - auth_type: {auth_type}, project_id: {project_id}")
        logger.info(f"hosts内容: {hosts[:200]}...")  # 只记录前200个字符
        
        # 获取用户ID
        user_id = current_user['user_id']
        
        # 生成批次ID
        batch_id = f"batch-{uuid.uuid4().hex[:16]}"
        
        # 解析主机列表
        try:
            hosts_list: List[HostConfig] = json.loads(hosts)
        except json.JSONDecodeError as e:
            logger.error(f"主机列表JSON解析失败: {str(e)}")
            raise HTTPException(status_code=422, detail=f"主机列表格式错误: {str(e)}")
        
        # 验证主机列表
        if not hosts_list:
            raise HTTPException(status_code=422, detail="主机列表不能为空")
        
        # 验证每个主机配置
        for i, host_dict in enumerate(hosts_list):
            try:
                HostConfig(**host_dict)
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"主机配置 #{i+1} 验证失败: {str(e)}")
        
        # 读取SSH密钥内容（如果提供）
        ssh_key_content = None
        if auth_type == 'key' and ssh_key:
            ssh_key_content = (await ssh_key.read()).decode('utf-8')
        
        # 使用自定义server_url，如果没有提供则使用环境变量或默认值
        if not server_url:
            server_url = os.getenv('QUNKONG_SERVER_URL', 'http://localhost:8000')
        
        # 获取数据库连接
        server = get_server()
        db_conn = server.db._get_connection()
        
        # 并发执行安装任务
        loop = asyncio.get_event_loop()
        tasks = []
        
        for host_config_dict in hosts_list:
            host_config = HostConfig(**host_config_dict)
            task = loop.run_in_executor(
                executor,
                install_agent_on_host,
                host_config,
                ssh_key_content,
                server_url,
                agent_download_url,
                agent_md5,
                project_id,
                batch_id,
                user_id,
                db_conn
            )
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks)
        
        # 统计结果
        success_count = sum(1 for r in results if r.success)
        
        # 关闭数据库连接
        db_conn.close()
        
        return {
            'message': f'批量安装完成，成功: {success_count}/{len(results)}',
            'batch_id': batch_id,
            'results': [r.dict() for r in results],
            'success_count': success_count,
            'total_count': len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量安装失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量安装失败: {str(e)}")


@router.get("/agents/install-history")
async def get_install_history(
    current_user: Dict[str, Any] = Depends(require_permission('agent.view'))
):
    """获取批量安装历史记录"""
    # 从用户上下文获取项目ID
    project_id = current_user.get('current_project_id', 1)
    try:
        server = get_server()
        conn = server.db._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                id, project_id, user_id, batch_id, ip, username, port,
                agent_id, status, message, download_url, agent_md5,
                created_at, updated_at
            FROM agent_install_history
            WHERE project_id = %s
            ORDER BY created_at DESC
            LIMIT 500
        """, (project_id,))
        
        history = cursor.fetchall()
        conn.close()
        
        return {'history': history}
        
    except Exception as e:
        logger.error(f"获取安装历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取安装历史失败: {str(e)}")


@router.get("/agents/install-history/{batch_id}")
async def get_batch_details(
    batch_id: str,
    current_user: Dict[str, Any] = Depends(require_permission('agent.view'))
):
    """获取指定批次的详细信息"""
    try:
        server = get_server()
        conn = server.db._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT *
            FROM agent_install_history
            WHERE batch_id = %s
            ORDER BY created_at
        """, (batch_id,))
        
        details = cursor.fetchall()
        conn.close()
        
        return {'details': details}
        
    except Exception as e:
        logger.error(f"获取批次详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取批次详情失败: {str(e)}")


@router.get("/downloads/qunkong-agent-latest")
async def download_agent():
    """下载最新的Agent程序"""
    # 这里应该返回实际的Agent可执行文件
    # 目前返回releases目录中的文件
    agent_path = "/opt/qunkong/releases/qunkong-agent-latest"
    
    if not os.path.exists(agent_path):
        raise HTTPException(status_code=404, detail="Agent程序文件不存在")
    
    from fastapi.responses import FileResponse
    return FileResponse(
        agent_path,
        media_type="application/octet-stream",
        filename="qunkong-agent"
    )