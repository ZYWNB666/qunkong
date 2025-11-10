"""
简单作业管理API
"""
import asyncio
import threading
from flask import Blueprint, request, jsonify
from app.api.auth import require_auth
from app.models.simple_jobs import SimpleJobManager
from app.models import DatabaseManager

# 创建蓝图
simple_jobs_bp = Blueprint('simple_jobs', __name__, url_prefix='/api/simple-jobs')

# 全局变量
job_manager = None
server_instance = None


def init_simple_jobs(db_manager: DatabaseManager, server):
    """初始化简单作业管理"""
    global job_manager, server_instance
    job_manager = SimpleJobManager(db_manager)
    server_instance = server


# ==================== 作业管理 ====================

@simple_jobs_bp.route('', methods=['GET'])
@require_auth
def get_jobs():
    """获取作业列表"""
    try:
        project_id = request.args.get('project_id', type=int)
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        jobs = job_manager.get_all_jobs(project_id=project_id, limit=limit, offset=offset)
        return jsonify({'jobs': jobs, 'total': len(jobs)})
        
    except Exception as e:
        return jsonify({'error': f'获取作业列表失败: {str(e)}'}), 500


@simple_jobs_bp.route('/<job_id>', methods=['GET'])
@require_auth
def get_job(job_id):
    """获取作业详情"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({'error': '作业不存在'}), 404
        
        return jsonify({'job': job})
        
    except Exception as e:
        return jsonify({'error': f'获取作业失败: {str(e)}'}), 500


@simple_jobs_bp.route('', methods=['POST'])
@require_auth
def create_job():
    """创建作业"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供作业信息'}), 400
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        project_id = data.get('project_id')
        target_agent_id = data.get('target_agent_id', '').strip()
        env_vars = data.get('env_vars', {})
        steps = data.get('steps', [])
        
        if not name:
            return jsonify({'error': '请提供作业名称'}), 400
        
        if not project_id:
            return jsonify({'error': '请提供项目ID'}), 400
        
        if not target_agent_id:
            return jsonify({'error': '请选择目标Agent'}), 400
        
        if not steps:
            return jsonify({'error': '请至少添加一个步骤'}), 400
        
        user_id = request.current_user['user_id']
        
        # 创建作业
        job_id = job_manager.create_job(
            name=name,
            description=description,
            project_id=project_id,
            target_agent_id=target_agent_id,
            env_vars=env_vars,
            created_by=user_id
        )
        
        if not job_id:
            return jsonify({'error': '创建作业失败'}), 500
        
        # 添加步骤
        for i, step in enumerate(steps):
            step_name = step.get('step_name', f'步骤{i+1}')
            script_content = step.get('script_content', '')
            target_agent_id = step.get('target_agent_id', target_agent_id)  # 如果步骤没有指定agent，使用作业级别的agent
            timeout = step.get('timeout', 300)
            
            if not script_content:
                continue
            
            job_manager.add_step(
                job_id=job_id,
                step_name=step_name,
                script_content=script_content,
                step_order=i + 1,
                timeout=timeout,
                target_agent_id=target_agent_id
            )
        
        return jsonify({
            'message': '作业创建成功',
            'job_id': job_id
        })
        
    except Exception as e:
        return jsonify({'error': f'创建作业失败: {str(e)}'}), 500


@simple_jobs_bp.route('/<job_id>', methods=['PUT'])
@require_auth
def update_job(job_id):
    """更新作业"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供更新信息'}), 400
        
        # 更新作业基本信息
        success = job_manager.update_job(
            job_id=job_id,
            name=data.get('name'),
            description=data.get('description'),
            target_agent_id=data.get('target_agent_id'),
            env_vars=data.get('env_vars')
        )
        
        if not success:
            return jsonify({'error': '更新作业失败'}), 500
        
        # 处理步骤更新
        steps = data.get('steps', [])
        if steps is not None:  # 如果提供了步骤信息，则更新步骤
            # 获取当前作业的所有步骤
            job = job_manager.get_job(job_id)
            if job:
                # 删除旧步骤
                for old_step in job['steps']:
                    job_manager.delete_step(old_step['id'])
                
                # 添加新步骤
                for i, step in enumerate(steps):
                    step_name = step.get('step_name', f'步骤{i+1}')
                    script_content = step.get('script_content', '')
                    timeout = step.get('timeout', 300)
                    
                    if not script_content:
                        continue
                    
                    job_manager.add_step(
                        job_id=job_id,
                        step_name=step_name,
                        script_content=script_content,
                        step_order=i + 1,
                        timeout=timeout
                    )
        
        return jsonify({'message': '作业更新成功'})
        
    except Exception as e:
        return jsonify({'error': f'更新作业失败: {str(e)}'}), 500


@simple_jobs_bp.route('/<job_id>', methods=['DELETE'])
@require_auth
def delete_job(job_id):
    """删除作业"""
    try:
        success = job_manager.delete_job(job_id)
        
        if not success:
            return jsonify({'error': '删除作业失败'}), 500
        
        return jsonify({'message': '作业删除成功'})
        
    except Exception as e:
        return jsonify({'error': f'删除作业失败: {str(e)}'}), 500


# ==================== 步骤管理 ====================

@simple_jobs_bp.route('/<job_id>/steps', methods=['POST'])
@require_auth
def add_step(job_id):
    """添加作业步骤"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供步骤信息'}), 400
        
        step_name = data.get('step_name', '').strip()
        script_content = data.get('script_content', '').strip()
        timeout = data.get('timeout', 300)
        
        if not step_name:
            return jsonify({'error': '请提供步骤名称'}), 400
        
        if not script_content:
            return jsonify({'error': '请提供脚本内容'}), 400
        
        step_id = job_manager.add_step(
            job_id=job_id,
            step_name=step_name,
            script_content=script_content,
            timeout=timeout
        )
        
        if not step_id:
            return jsonify({'error': '添加步骤失败'}), 500
        
        return jsonify({
            'message': '步骤添加成功',
            'step_id': step_id
        })
        
    except Exception as e:
        return jsonify({'error': f'添加步骤失败: {str(e)}'}), 500


@simple_jobs_bp.route('/<job_id>/steps/<step_id>', methods=['PUT'])
@require_auth
def update_step(job_id, step_id):
    """更新作业步骤"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供更新信息'}), 400
        
        success = job_manager.update_step(
            step_id=step_id,
            step_name=data.get('step_name'),
            script_content=data.get('script_content'),
            timeout=data.get('timeout')
        )
        
        if not success:
            return jsonify({'error': '更新步骤失败'}), 500
        
        return jsonify({'message': '步骤更新成功'})
        
    except Exception as e:
        return jsonify({'error': f'更新步骤失败: {str(e)}'}), 500


@simple_jobs_bp.route('/<job_id>/steps/<step_id>', methods=['DELETE'])
@require_auth
def delete_step(job_id, step_id):
    """删除作业步骤"""
    try:
        success = job_manager.delete_step(step_id)
        
        if not success:
            return jsonify({'error': '删除步骤失败'}), 500
        
        return jsonify({'message': '步骤删除成功'})
        
    except Exception as e:
        return jsonify({'error': f'删除步骤失败: {str(e)}'}), 500


# ==================== 作业执行 ====================

@simple_jobs_bp.route('/<job_id>/execute', methods=['POST'])
@require_auth
def execute_job(job_id):
    """执行作业"""
    try:
        if not server_instance:
            return jsonify({'error': '服务器未就绪'}), 500
        
        # 获取作业信息
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({'error': '作业不存在'}), 404
        
        if not job['steps']:
            return jsonify({'error': '作业没有步骤'}), 400
        
        # 检查Agent是否在线
        agent_id = job['target_agent_id']
        if agent_id not in server_instance.agents:
            return jsonify({'error': 'Agent不在线'}), 400
        
        # 创建执行记录
        execution_id = job_manager.create_execution(job_id)
        if not execution_id:
            return jsonify({'error': '创建执行记录失败'}), 500
        
        # 异步执行作业
        def run_job():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(execute_job_steps(execution_id, job))
            loop.close()
        
        thread = threading.Thread(target=run_job)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': '作业开始执行',
            'execution_id': execution_id
        })
        
    except Exception as e:
        return jsonify({'error': f'执行作业失败: {str(e)}'}), 500


async def execute_job_steps(execution_id: str, job: dict):
    """按顺序执行作业步骤"""
    try:
        # 更新状态为运行中
        job_manager.update_execution(execution_id, status='RUNNING')
        
        steps = job['steps']
        agent_id = job['target_agent_id']
        env_vars = job.get('env_vars', {})
        
        # 构建环境变量脚本
        env_script = ""
        if env_vars:
            for key, value in env_vars.items():
                env_script += f"export {key}='{value}'\n"
        
        # 按顺序执行每个步骤
        for i, step in enumerate(steps):
            step_num = i + 1
            step_name = step['step_name']
            script_content = step['script_content']
            timeout = step['timeout']
            step_agent_id = step.get('target_agent_id') or agent_id  # 优先使用步骤级别的agent，否则使用作业级别的agent
            
            # 更新当前步骤
            job_manager.update_execution(
                execution_id,
                current_step=step_num,
                log_entry=f"[步骤 {step_num}/{len(steps)}] 开始执行: {step_name} (Agent: {step_agent_id})"
            )
            
            # 组合环境变量和脚本
            full_script = env_script + "\n" + script_content
            
            # 创建任务
            task_id = server_instance.create_task(
                script=full_script,
                target_hosts=[step_agent_id],
                script_name=f"{job['name']} - {step_name}",
                script_params="",
                timeout=timeout,
                execution_user="root"
            )
            
            # 执行任务并等待结果
            await server_instance.dispatch_task(task_id)
            
            # 等待任务完成（简单轮询）
            max_wait = timeout + 10
            waited = 0
            while waited < max_wait:
                if task_id in server_instance.tasks:
                    task = server_instance.tasks[task_id]
                    if task.status in ['COMPLETED', 'SUCCEED', 'FAILED']:
                        # 任务完成
                        if task.status == 'FAILED':
                            error_msg = f"步骤 {step_name} 执行失败"
                            job_manager.update_execution(
                                execution_id,
                                status='FAILED',
                                error_message=error_msg,
                                log_entry=f"[步骤 {step_num}/{len(steps)}] 失败: {error_msg}"
                            )
                            return
                        else:
                            # 记录成功
                            job_manager.update_execution(
                                execution_id,
                                log_entry=f"[步骤 {step_num}/{len(steps)}] 完成: {step_name}"
                            )
                        break
                
                await asyncio.sleep(1)
                waited += 1
            else:
                # 超时
                error_msg = f"步骤 {step_name} 执行超时"
                job_manager.update_execution(
                    execution_id,
                    status='FAILED',
                    error_message=error_msg,
                    log_entry=f"[步骤 {step_num}/{len(steps)}] 超时"
                )
                return
        
        # 所有步骤执行成功
        job_manager.update_execution(
            execution_id,
            status='COMPLETED',
            current_step=len(steps),
            log_entry=f"作业执行完成，共 {len(steps)} 个步骤"
        )
        
    except Exception as e:
        # 执行出错
        job_manager.update_execution(
            execution_id,
            status='FAILED',
            error_message=str(e),
            log_entry=f"作业执行异常: {str(e)}"
        )


@simple_jobs_bp.route('/executions/<execution_id>', methods=['GET'])
@require_auth
def get_execution(execution_id):
    """获取执行记录"""
    try:
        execution = job_manager.get_execution(execution_id)
        if not execution:
            return jsonify({'error': '执行记录不存在'}), 404
        
        return jsonify({'execution': execution})
        
    except Exception as e:
        return jsonify({'error': f'获取执行记录失败: {str(e)}'}), 500


@simple_jobs_bp.route('/executions', methods=['GET'])
@require_auth
def get_executions():
    """获取执行历史"""
    try:
        job_id = request.args.get('job_id')
        project_id = request.args.get('project_id', type=int)
        limit = int(request.args.get('limit', 100))
        
        executions = job_manager.get_job_executions(job_id=job_id, project_id=project_id, limit=limit)
        return jsonify({'executions': executions, 'total': len(executions)})
        
    except Exception as e:
        return jsonify({'error': f'获取执行历史失败: {str(e)}'}), 500
