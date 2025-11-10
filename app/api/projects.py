# -*- coding: utf-8 -*-
"""
项目管理API路由
"""
from flask import Blueprint, request, jsonify
from functools import wraps
from app.api.auth import require_auth
from app.models.project import ProjectManager
from app.models import DatabaseManager


# 创建项目管理蓝图
projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')

# 全局项目管理器
project_manager = None


def init_projects(db_manager: DatabaseManager):
    """初始化项目管理器"""
    global project_manager
    project_manager = ProjectManager(db_manager)


def require_project_admin(project_id_param='project_id'):
    """项目管理员权限装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'error': '未认证'}), 401

            # 获取项目ID
            project_id = kwargs.get(project_id_param)
            if not project_id:
                return jsonify({'error': '缺少项目ID'}), 400

            # 系统管理员拥有所有权限
            if request.current_user['role'] in ['admin', 'super_admin']:
                return f(*args, **kwargs)

            # 检查项目权限
            if not project_manager.check_project_permission(
                request.current_user['user_id'],
                project_id,
                'admin'
            ):
                return jsonify({'error': '权限不足，需要项目管理员权限'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


@projects_bp.route('', methods=['GET'])
@require_auth
def get_projects():
    """获取项目列表"""
    try:
        # 获取查询参数
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))

        # 计算偏移量
        offset = (page - 1) * page_size

        # 普通用户只能查看自己参与的项目
        if request.current_user['role'] not in ['admin', 'super_admin']:
            projects = project_manager.get_all_projects(
                status=status,
                user_id=request.current_user['user_id'],
                limit=page_size,
                offset=offset
            )
        else:
            # 管理员可以查看所有项目
            projects = project_manager.get_all_projects(
                status=status,
                limit=page_size,
                offset=offset
            )

        return jsonify({
            'projects': projects,
            'page': page,
            'page_size': page_size
        })

    except Exception as e:
        return jsonify({'error': f'获取项目列表失败: {str(e)}'}), 500


@projects_bp.route('/<int:project_id>', methods=['GET'])
@require_auth
def get_project(project_id):
    """获取项目详情"""
    try:
        # 检查权限
        if request.current_user['role'] not in ['admin', 'super_admin']:
            if not project_manager.check_project_permission(
                request.current_user['user_id'],
                project_id
            ):
                return jsonify({'error': '权限不足'}), 403

        project = project_manager.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': '项目不存在'}), 404

        # 获取项目成员
        members = project_manager.get_project_members(project_id)
        project['members'] = members

        return jsonify({'project': project})

    except Exception as e:
        return jsonify({'error': f'获取项目信息失败: {str(e)}'}), 500


@projects_bp.route('', methods=['POST'])
@require_auth
def create_project():
    """创建项目，创建者自动成为项目管理员，项目代码自动生成"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供项目信息'}), 400

        project_name = data.get('project_name', '').strip()
        description = data.get('description', '')

        # 验证输入
        if not project_name:
            return jsonify({'error': '请提供项目名称'}), 400

        # 创建项目（创建者自动成为管理员，项目代码自动生成）
        project = project_manager.create_project(
            project_name=project_name,
            description=description,
            created_by=request.current_user['user_id']
        )

        if not project:
            return jsonify({'error': '创建项目失败'}), 400

        return jsonify({
            'message': '项目创建成功，您已成为项目管理员',
            'project': project
        }), 201

    except Exception as e:
        return jsonify({'error': f'创建项目失败: {str(e)}'}), 500


@projects_bp.route('/<int:project_id>', methods=['PUT'])
@require_auth
@require_project_admin()
def update_project(project_id):
    """更新项目信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供更新信息'}), 400

        # 更新项目
        success = project_manager.update_project(project_id, **data)
        if not success:
            return jsonify({'error': '更新失败'}), 400

        # 获取更新后的项目信息
        project = project_manager.get_project_by_id(project_id)

        return jsonify({
            'message': '项目信息更新成功',
            'project': project
        })

    except Exception as e:
        return jsonify({'error': f'更新项目信息失败: {str(e)}'}), 500


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@require_auth
@require_project_admin()
def delete_project(project_id):
    """删除项目"""
    try:
        project = project_manager.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': '项目不存在'}), 404

        success = project_manager.delete_project(project_id)
        if not success:
            return jsonify({'error': '删除项目失败'}), 500

        return jsonify({'message': '项目删除成功'})

    except Exception as e:
        return jsonify({'error': f'删除项目失败: {str(e)}'}), 500


@projects_bp.route('/<int:project_id>/members', methods=['GET'])
@require_auth
def get_project_members(project_id):
    """获取项目成员列表"""
    try:
        # 检查权限
        if request.current_user['role'] not in ['admin', 'super_admin']:
            if not project_manager.check_project_permission(
                request.current_user['user_id'],
                project_id
            ):
                return jsonify({'error': '权限不足'}), 403

        members = project_manager.get_project_members(project_id)

        return jsonify({'members': members})

    except Exception as e:
        return jsonify({'error': f'获取项目成员列表失败: {str(e)}'}), 500


@projects_bp.route('/<int:project_id>/members', methods=['POST'])
@require_auth
@require_project_admin()
def add_project_member(project_id):
    """添加项目成员"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供成员信息'}), 400

        user_id = data.get('user_id')
        role = data.get('role', 'readonly')

        if not user_id:
            return jsonify({'error': '请提供用户ID'}), 400

        # 验证角色
        valid_roles = ['admin', 'readwrite', 'readonly']
        if role not in valid_roles:
            return jsonify({'error': f'无效的角色，允许的角色: {", ".join(valid_roles)}'}), 400

        # 添加成员
        success = project_manager.add_project_member(
            project_id,
            user_id,
            role,
            invited_by=request.current_user['user_id']
        )

        if not success:
            return jsonify({'error': '添加成员失败'}), 500

        return jsonify({'message': '成员添加成功'}), 201

    except Exception as e:
        return jsonify({'error': f'添加项目成员失败: {str(e)}'}), 500


@projects_bp.route('/<int:project_id>/members/<int:user_id>', methods=['DELETE'])
@require_auth
@require_project_admin()
def remove_project_member(project_id, user_id):
    """移除项目成员"""
    try:
        # 不允许移除自己
        if request.current_user['user_id'] == user_id:
            return jsonify({'error': '不能移除自己'}), 400

        success = project_manager.remove_project_member(project_id, user_id)
        if not success:
            return jsonify({'error': '移除成员失败'}), 500

        return jsonify({'message': '成员移除成功'})

    except Exception as e:
        return jsonify({'error': f'移除项目成员失败: {str(e)}'}), 500


@projects_bp.route('/<int:project_id>/members/<int:user_id>/role', methods=['PUT'])
@require_auth
@require_project_admin()
def update_member_role(project_id, user_id):
    """更新项目成员角色"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供角色信息'}), 400

        role = data.get('role')
        if not role:
            return jsonify({'error': '请提供角色'}), 400

        # 验证角色
        valid_roles = ['admin', 'readwrite', 'readonly']
        if role not in valid_roles:
            return jsonify({'error': f'无效的角色，允许的角色: {", ".join(valid_roles)}'}), 400

        success = project_manager.update_member_role(project_id, user_id, role)
        if not success:
            return jsonify({'error': '更新角色失败'}), 500

        return jsonify({'message': '成员角色更新成功'})

    except Exception as e:
        return jsonify({'error': f'更新成员角色失败: {str(e)}'}), 500


@projects_bp.route('/my-projects', methods=['GET'])
@require_auth
def get_my_projects():
    """获取当前用户的项目列表"""
    try:
        projects = project_manager.get_user_projects(request.current_user['user_id'])

        return jsonify({'projects': projects})

    except Exception as e:
        return jsonify({'error': f'获取项目列表失败: {str(e)}'}), 500
