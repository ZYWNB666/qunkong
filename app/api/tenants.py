# -*- coding: utf-8 -*-
"""
租户管理API路由
"""
from flask import Blueprint, request, jsonify
from functools import wraps
from app.api.auth import require_auth
from app.models.tenant import TenantManager
from app.models import DatabaseManager


# 创建租户管理蓝图
tenants_bp = Blueprint('tenants', __name__, url_prefix='/api/tenants')

# 全局租户管理器
tenant_manager = None


def init_tenants(db_manager: DatabaseManager):
    """初始化租户管理器"""
    global tenant_manager
    tenant_manager = TenantManager(db_manager)


def require_admin(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(request, 'current_user'):
            return jsonify({'error': '未认证'}), 401

        if request.current_user['role'] not in ['admin', 'super_admin']:
            return jsonify({'error': '权限不足，需要管理员权限'}), 403

        return f(*args, **kwargs)
    return decorated_function


def require_tenant_admin(tenant_id_param='tenant_id'):
    """租户管理员权限装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'error': '未认证'}), 401

            # 获取租户ID
            tenant_id = kwargs.get(tenant_id_param)
            if not tenant_id:
                return jsonify({'error': '缺少租户ID'}), 400

            # 系统管理员拥有所有权限
            if request.current_user['role'] in ['admin', 'super_admin']:
                return f(*args, **kwargs)

            # 检查租户权限
            if not tenant_manager.check_tenant_permission(
                request.current_user['user_id'],
                tenant_id,
                'tenant_admin'
            ):
                return jsonify({'error': '权限不足，需要租户管理员权限'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


@tenants_bp.route('', methods=['GET'])
@require_auth
def get_tenants():
    """获取租户列表"""
    try:
        # 获取查询参数
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))

        # 计算偏移量
        offset = (page - 1) * page_size

        # 系统管理员可以查看所有租户
        if request.current_user['role'] in ['admin', 'super_admin']:
            tenants = tenant_manager.get_all_tenants(
                status=status,
                limit=page_size,
                offset=offset
            )
        else:
            # 普通用户只能查看自己所属的租户
            tenants = tenant_manager.get_user_tenants(request.current_user['user_id'])

        return jsonify({
            'tenants': tenants,
            'page': page,
            'page_size': page_size
        })

    except Exception as e:
        return jsonify({'error': f'获取租户列表失败: {str(e)}'}), 500


@tenants_bp.route('/<int:tenant_id>', methods=['GET'])
@require_auth
def get_tenant(tenant_id):
    """获取租户详情"""
    try:
        # 检查权限
        if request.current_user['role'] not in ['admin', 'super_admin']:
            if not tenant_manager.check_tenant_permission(
                request.current_user['user_id'],
                tenant_id
            ):
                return jsonify({'error': '权限不足'}), 403

        tenant = tenant_manager.get_tenant_by_id(tenant_id)
        if not tenant:
            return jsonify({'error': '租户不存在'}), 404

        # 获取租户成员
        members = tenant_manager.get_tenant_members(tenant_id)
        tenant['members'] = members

        return jsonify({'tenant': tenant})

    except Exception as e:
        return jsonify({'error': f'获取租户信息失败: {str(e)}'}), 500


@tenants_bp.route('', methods=['POST'])
@require_auth
@require_admin
def create_tenant():
    """创建租户"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供租户信息'}), 400

        tenant_code = data.get('tenant_code', '').strip()
        tenant_name = data.get('tenant_name', '').strip()
        description = data.get('description', '')
        max_users = data.get('max_users', 10)
        max_agents = data.get('max_agents', 50)
        max_concurrent_jobs = data.get('max_concurrent_jobs', 10)
        storage_quota_gb = data.get('storage_quota_gb', 100)
        contact_name = data.get('contact_name', '')
        contact_email = data.get('contact_email', '')
        contact_phone = data.get('contact_phone', '')

        # 验证输入
        if not tenant_code or len(tenant_code) < 2:
            return jsonify({'error': '租户代码至少2个字符'}), 400

        if not tenant_name:
            return jsonify({'error': '请提供租户名称'}), 400

        # 创建租户
        tenant_id = tenant_manager.create_tenant(
            tenant_code=tenant_code,
            tenant_name=tenant_name,
            description=description,
            max_users=max_users,
            max_agents=max_agents,
            max_concurrent_jobs=max_concurrent_jobs,
            storage_quota_gb=storage_quota_gb,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            created_by=request.current_user['user_id']
        )

        if not tenant_id:
            return jsonify({'error': '租户代码已存在'}), 400

        # 获取新创建的租户信息
        tenant = tenant_manager.get_tenant_by_id(tenant_id)

        return jsonify({
            'message': '租户创建成功',
            'tenant': tenant
        }), 201

    except Exception as e:
        return jsonify({'error': f'创建租户失败: {str(e)}'}), 500


@tenants_bp.route('/<int:tenant_id>', methods=['PUT'])
@require_auth
@require_tenant_admin()
def update_tenant(tenant_id):
    """更新租户信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供更新信息'}), 400

        # 更新租户
        success = tenant_manager.update_tenant(tenant_id, **data)
        if not success:
            return jsonify({'error': '更新失败'}), 400

        # 获取更新后的租户信息
        tenant = tenant_manager.get_tenant_by_id(tenant_id)

        return jsonify({
            'message': '租户信息更新成功',
            'tenant': tenant
        })

    except Exception as e:
        return jsonify({'error': f'更新租户信息失败: {str(e)}'}), 500


@tenants_bp.route('/<int:tenant_id>', methods=['DELETE'])
@require_auth
@require_admin
def delete_tenant(tenant_id):
    """删除租户"""
    try:
        # 不允许删除默认租户
        tenant = tenant_manager.get_tenant_by_id(tenant_id)
        if not tenant:
            return jsonify({'error': '租户不存在'}), 404

        if tenant['tenant_code'] == 'default':
            return jsonify({'error': '不能删除默认租户'}), 400

        success = tenant_manager.delete_tenant(tenant_id)
        if not success:
            return jsonify({'error': '删除租户失败'}), 500

        return jsonify({'message': '租户删除成功'})

    except Exception as e:
        return jsonify({'error': f'删除租户失败: {str(e)}'}), 500


@tenants_bp.route('/<int:tenant_id>/members', methods=['GET'])
@require_auth
def get_tenant_members(tenant_id):
    """获取租户成员列表"""
    try:
        # 检查权限
        if request.current_user['role'] not in ['admin', 'super_admin']:
            if not tenant_manager.check_tenant_permission(
                request.current_user['user_id'],
                tenant_id
            ):
                return jsonify({'error': '权限不足'}), 403

        members = tenant_manager.get_tenant_members(tenant_id)

        return jsonify({'members': members})

    except Exception as e:
        return jsonify({'error': f'获取租户成员列表失败: {str(e)}'}), 500


@tenants_bp.route('/<int:tenant_id>/members', methods=['POST'])
@require_auth
@require_tenant_admin()
def add_tenant_member(tenant_id):
    """添加租户成员"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供成员信息'}), 400

        user_id = data.get('user_id')
        role = data.get('role', 'tenant_member')

        if not user_id:
            return jsonify({'error': '请提供用户ID'}), 400

        # 验证角色
        valid_roles = ['tenant_admin', 'tenant_member']
        if role not in valid_roles:
            return jsonify({'error': f'无效的角色，允许的角色: {", ".join(valid_roles)}'}), 400

        # 添加成员
        success = tenant_manager.add_tenant_member(
            tenant_id,
            user_id,
            role,
            invited_by=request.current_user['user_id']
        )

        if not success:
            return jsonify({'error': '添加成员失败'}), 500

        return jsonify({'message': '成员添加成功'}), 201

    except Exception as e:
        return jsonify({'error': f'添加租户成员失败: {str(e)}'}), 500


@tenants_bp.route('/<int:tenant_id>/members/<int:user_id>', methods=['DELETE'])
@require_auth
@require_tenant_admin()
def remove_tenant_member(tenant_id, user_id):
    """移除租户成员"""
    try:
        # 不允许移除自己
        if request.current_user['user_id'] == user_id:
            return jsonify({'error': '不能移除自己'}), 400

        success = tenant_manager.remove_tenant_member(tenant_id, user_id)
        if not success:
            return jsonify({'error': '移除成员失败'}), 500

        return jsonify({'message': '成员移除成功'})

    except Exception as e:
        return jsonify({'error': f'移除租户成员失败: {str(e)}'}), 500


@tenants_bp.route('/<int:tenant_id>/members/<int:user_id>/role', methods=['PUT'])
@require_auth
@require_tenant_admin()
def update_member_role(tenant_id, user_id):
    """更新租户成员角色"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供角色信息'}), 400

        role = data.get('role')
        if not role:
            return jsonify({'error': '请提供角色'}), 400

        # 验证角色
        valid_roles = ['tenant_admin', 'tenant_member']
        if role not in valid_roles:
            return jsonify({'error': f'无效的角色，允许的角色: {", ".join(valid_roles)}'}), 400

        success = tenant_manager.update_member_role(tenant_id, user_id, role)
        if not success:
            return jsonify({'error': '更新角色失败'}), 500

        return jsonify({'message': '成员角色更新成功'})

    except Exception as e:
        return jsonify({'error': f'更新成员角色失败: {str(e)}'}), 500


@tenants_bp.route('/my-tenants', methods=['GET'])
@require_auth
def get_my_tenants():
    """获取当前用户的租户列表"""
    try:
        tenants = tenant_manager.get_user_tenants(request.current_user['user_id'])

        return jsonify({'tenants': tenants})

    except Exception as e:
        return jsonify({'error': f'获取租户列表失败: {str(e)}'}), 500
