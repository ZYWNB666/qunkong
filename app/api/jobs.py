"""
作业管理API路由
"""
from flask import Blueprint, request, jsonify
from app.api.auth import require_auth, require_permission
from app.models.jobs import JobManager
from app.models import DatabaseManager

# 创建作业蓝图
jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')

# 全局作业管理器
job_manager = None

def init_jobs(db_manager: DatabaseManager):
    """初始化作业管理器"""
    global job_manager
    job_manager = JobManager(db_manager)

@jobs_bp.route('/templates', methods=['GET'])
@require_auth
def get_job_templates():
    """获取作业模板列表"""
    try:
        category = request.args.get('category')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        templates = job_manager.get_all_templates(category, limit, offset)
        return jsonify({
            'templates': templates,
            'total': len(templates)
        })
        
    except Exception as e:
        return jsonify({'error': f'获取作业模板失败: {str(e)}'}), 500

@jobs_bp.route('/templates/<template_id>', methods=['GET'])
@require_auth
def get_job_template(template_id):
    """获取作业模板详情"""
    try:
        template = job_manager.get_template_by_id(template_id)
        if not template:
            return jsonify({'error': '作业模板不存在'}), 404
        
        return jsonify({'template': template})
        
    except Exception as e:
        return jsonify({'error': f'获取作业模板失败: {str(e)}'}), 500

@jobs_bp.route('/templates', methods=['POST'])
@require_auth
@require_permission('job_management')
def create_job_template():
    """创建作业模板"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供作业模板信息'}), 400
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        category = data.get('category', 'custom')
        tags = data.get('tags', [])
        steps = data.get('steps', [])
        default_params = data.get('default_params', {})
        
        if not name:
            return jsonify({'error': '请提供作业模板名称'}), 400
        
        if not steps:
            return jsonify({'error': '请提供作业步骤'}), 400
        
        # 验证步骤格式
        for i, step in enumerate(steps):
            if not step.get('name'):
                return jsonify({'error': f'第{i+1}个步骤缺少名称'}), 400
            if not step.get('type'):
                return jsonify({'error': f'第{i+1}个步骤缺少类型'}), 400
        
        user_id = request.current_user['user_id']
        template_id = job_manager.create_template(
            name=name,
            description=description,
            category=category,
            tags=tags,
            steps=steps,
            default_params=default_params,
            created_by=user_id
        )
        
        if not template_id:
            return jsonify({'error': '创建作业模板失败'}), 500
        
        return jsonify({
            'message': '作业模板创建成功',
            'template_id': template_id
        })
        
    except Exception as e:
        return jsonify({'error': f'创建作业模板失败: {str(e)}'}), 500

@jobs_bp.route('/instances', methods=['GET'])
@require_auth
def get_job_instances():
    """获取作业实例列表"""
    try:
        status = request.args.get('status')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        instances = job_manager.get_all_job_instances(status, limit, offset)
        return jsonify({
            'instances': instances,
            'total': len(instances)
        })
        
    except Exception as e:
        return jsonify({'error': f'获取作业实例失败: {str(e)}'}), 500

@jobs_bp.route('/instances/<job_id>', methods=['GET'])
@require_auth
def get_job_instance(job_id):
    """获取作业实例详情"""
    try:
        instance = job_manager.get_job_instance(job_id)
        if not instance:
            return jsonify({'error': '作业实例不存在'}), 404
        
        return jsonify({'instance': instance})
        
    except Exception as e:
        return jsonify({'error': f'获取作业实例失败: {str(e)}'}), 500

@jobs_bp.route('/instances', methods=['POST'])
@require_auth
@require_permission('job_execution')
def create_job_instance():
    """创建作业实例"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供作业信息'}), 400
        
        template_id = data.get('template_id', '').strip()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        params = data.get('params', {})
        target_hosts = data.get('target_hosts', [])
        priority = data.get('priority', 5)
        
        if not template_id:
            return jsonify({'error': '请选择作业模板'}), 400
        
        if not name:
            return jsonify({'error': '请提供作业名称'}), 400
        
        if not target_hosts:
            return jsonify({'error': '请选择目标主机'}), 400
        
        user_id = request.current_user['user_id']
        job_id = job_manager.create_job_instance(
            template_id=template_id,
            name=name,
            params=params,
            target_hosts=target_hosts,
            created_by=user_id,
            description=description,
            priority=priority
        )
        
        if not job_id:
            return jsonify({'error': '创建作业实例失败'}), 500
        
        return jsonify({
            'message': '作业实例创建成功',
            'job_id': job_id
        })
        
    except Exception as e:
        return jsonify({'error': f'创建作业实例失败: {str(e)}'}), 500

@jobs_bp.route('/instances/<job_id>/execute', methods=['POST'])
@require_auth
@require_permission('job_execution')
def execute_job_instance(job_id):
    """执行作业实例"""
    try:
        # 这里需要实现作业执行逻辑
        # 暂时返回成功消息
        return jsonify({
            'message': '作业执行已启动',
            'job_id': job_id
        })
        
    except Exception as e:
        return jsonify({'error': f'执行作业失败: {str(e)}'}), 500

@jobs_bp.route('/instances/<job_id>/stop', methods=['POST'])
@require_auth
@require_permission('job_execution')
def stop_job_instance(job_id):
    """停止作业实例"""
    try:
        # 这里需要实现作业停止逻辑
        # 暂时返回成功消息
        return jsonify({
            'message': '作业停止成功',
            'job_id': job_id
        })
        
    except Exception as e:
        return jsonify({'error': f'停止作业失败: {str(e)}'}), 500

@jobs_bp.route('/categories', methods=['GET'])
@require_auth
def get_job_categories():
    """获取作业分类"""
    try:
        categories = [
            {'value': 'monitoring', 'label': '系统监控'},
            {'value': 'deployment', 'label': '应用部署'},
            {'value': 'maintenance', 'label': '系统维护'},
            {'value': 'backup', 'label': '数据备份'},
            {'value': 'security', 'label': '安全检查'},
            {'value': 'custom', 'label': '自定义'}
        ]
        
        return jsonify({'categories': categories})
        
    except Exception as e:
        return jsonify({'error': f'获取作业分类失败: {str(e)}'}), 500

@jobs_bp.route('/step-types', methods=['GET'])
@require_auth
def get_step_types():
    """获取步骤类型"""
    try:
        step_types = [
            {
                'value': 'script',
                'label': '脚本执行',
                'description': '执行Shell或Python脚本',
                'fields': [
                    {'name': 'script_type', 'label': '脚本类型', 'type': 'select', 'options': ['shell', 'python']},
                    {'name': 'script', 'label': '脚本内容', 'type': 'textarea'},
                    {'name': 'timeout', 'label': '超时时间(秒)', 'type': 'number', 'default': 300},
                    {'name': 'continue_on_error', 'label': '出错时继续', 'type': 'boolean', 'default': False}
                ]
            },
            {
                'value': 'file_transfer',
                'label': '文件传输',
                'description': '上传或下载文件',
                'fields': [
                    {'name': 'action', 'label': '操作类型', 'type': 'select', 'options': ['upload', 'download']},
                    {'name': 'local_path', 'label': '本地路径', 'type': 'text'},
                    {'name': 'remote_path', 'label': '远程路径', 'type': 'text'},
                    {'name': 'timeout', 'label': '超时时间(秒)', 'type': 'number', 'default': 600}
                ]
            },
            {
                'value': 'wait',
                'label': '等待',
                'description': '等待指定时间',
                'fields': [
                    {'name': 'duration', 'label': '等待时间(秒)', 'type': 'number', 'default': 10}
                ]
            },
            {
                'value': 'condition',
                'label': '条件判断',
                'description': '根据条件决定是否继续',
                'fields': [
                    {'name': 'condition', 'label': '判断条件', 'type': 'text'},
                    {'name': 'action_on_true', 'label': '条件为真时的操作', 'type': 'select', 'options': ['continue', 'skip', 'stop']},
                    {'name': 'action_on_false', 'label': '条件为假时的操作', 'type': 'select', 'options': ['continue', 'skip', 'stop']}
                ]
            }
        ]
        
        return jsonify({'step_types': step_types})
        
    except Exception as e:
        return jsonify({'error': f'获取步骤类型失败: {str(e)}'}), 500