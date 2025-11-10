# -*- coding: utf-8 -*-
"""
用户管理API路由
"""
from flask import Blueprint, request, jsonify
from functools import wraps
from app.api.auth import require_auth


# 创建用户管理蓝图
users_bp = Blueprint('users', __name__, url_prefix='/api/users')

# 全局auth_manager将在init_users中设置
auth_manager = None


def init_users(db_manager):
    """初始化用户管理"""
    global auth_manager
    from app.api.auth import auth_manager as am
    auth_manager = am


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


@users_bp.route('', methods=['GET'])
@require_auth
def get_users():
    """获取用户列表（所有登录用户都可以查看，用于项目成员管理）"""
    try:
        # 获取查询参数
        role = request.args.get('role')
        is_active = request.args.get('is_active')
        search = request.args.get('search')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))

        # 转换is_active参数
        is_active_bool = None
        if is_active is not None:
            is_active_bool = is_active.lower() in ['true', '1', 'yes']

        # 计算偏移量
        offset = (page - 1) * page_size

        # 获取用户列表
        users = auth_manager.get_all_users(
            role=role,
            is_active=is_active_bool,
            search=search,
            limit=page_size,
            offset=offset
        )

        # 获取总数
        total = auth_manager.count_users(role=role, is_active=is_active_bool)

        return jsonify({
            'users': users,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        })

    except Exception as e:
        return jsonify({'error': f'获取用户列表失败: {str(e)}'}), 500


@users_bp.route('/<int:user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    """获取用户详情"""
    try:
        # 检查权限：只有管理员或用户本人可以查看
        if request.current_user['role'] not in ['admin', 'super_admin'] and \
           request.current_user['user_id'] != user_id:
            return jsonify({'error': '权限不足'}), 403

        user = auth_manager.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        return jsonify({'user': user})

    except Exception as e:
        return jsonify({'error': f'获取用户信息失败: {str(e)}'}), 500


@users_bp.route('', methods=['POST'])
@require_auth
@require_admin
def create_user():
    """创建用户"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供用户信息'}), 400

        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'user')

        # 验证输入
        if not username or len(username) < 3:
            return jsonify({'error': '用户名至少3个字符'}), 400

        if not email or '@' not in email:
            return jsonify({'error': '请提供有效的邮箱地址'}), 400

        if not password or len(password) < 6:
            return jsonify({'error': '密码至少6个字符'}), 400

        # 验证角色
        valid_roles = ['user', 'admin', 'tenant_admin', 'tenant_member']
        if role not in valid_roles:
            return jsonify({'error': f'无效的角色，允许的角色: {", ".join(valid_roles)}'}), 400

        # 创建用户
        success = auth_manager.register_user(username, email, password, role)
        if not success:
            return jsonify({'error': '用户名或邮箱已存在'}), 400

        # 获取新创建的用户信息
        user = auth_manager.get_user_by_username(username)

        return jsonify({
            'message': '用户创建成功',
            'user': user
        }), 201

    except Exception as e:
        return jsonify({'error': f'创建用户失败: {str(e)}'}), 500


@users_bp.route('/<int:user_id>', methods=['PUT'])
@require_auth
def update_user(user_id):
    """更新用户信息"""
    try:
        # 检查权限：只有管理员或用户本人可以更新
        if request.current_user['role'] not in ['admin', 'super_admin'] and \
           request.current_user['user_id'] != user_id:
            return jsonify({'error': '权限不足'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供更新信息'}), 400

        # 非管理员只能更新自己的基本信息
        if request.current_user['role'] not in ['admin', 'super_admin']:
            # 移除敏感字段
            data.pop('role', None)
            data.pop('is_active', None)

        # 更新用户
        success = auth_manager.update_user(user_id, **data)
        if not success:
            return jsonify({'error': '更新失败，用户名或邮箱可能已存在'}), 400

        # 获取更新后的用户信息
        user = auth_manager.get_user_by_id(user_id)

        return jsonify({
            'message': '用户信息更新成功',
            'user': user
        })

    except Exception as e:
        return jsonify({'error': f'更新用户信息失败: {str(e)}'}), 500


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@require_auth
@require_admin
def delete_user(user_id):
    """删除用户"""
    try:
        # 不允许删除自己
        if request.current_user['user_id'] == user_id:
            return jsonify({'error': '不能删除自己的账号'}), 400

        # 不允许删除admin用户
        user = auth_manager.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        if user['username'] == 'admin':
            return jsonify({'error': '不能删除默认管理员账号'}), 400

        success = auth_manager.delete_user(user_id)
        if not success:
            return jsonify({'error': '删除用户失败'}), 500

        return jsonify({'message': '用户删除成功'})

    except Exception as e:
        return jsonify({'error': f'删除用户失败: {str(e)}'}), 500


@users_bp.route('/<int:user_id>/password', methods=['PUT'])
@require_auth
def change_password(user_id):
    """修改用户密码"""
    try:
        # 检查权限：只有管理员或用户本人可以修改密码
        if request.current_user['role'] not in ['admin', 'super_admin'] and \
           request.current_user['user_id'] != user_id:
            return jsonify({'error': '权限不足'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供密码信息'}), 400

        new_password = data.get('new_password', '')

        # 如果是用户本人修改，需要验证当前密码
        if request.current_user['user_id'] == user_id and \
           request.current_user['role'] not in ['admin', 'super_admin']:
            current_password = data.get('current_password', '')
            if not current_password:
                return jsonify({'error': '请提供当前密码'}), 400

            # 验证当前密码
            user = auth_manager.get_user_by_username(request.current_user['username'])
            if not auth_manager.verify_password(current_password, user['password_hash'], user['salt']):
                return jsonify({'error': '当前密码错误'}), 400

        if len(new_password) < 6:
            return jsonify({'error': '新密码至少6个字符'}), 400

        success = auth_manager.change_user_password(user_id, new_password)
        if not success:
            return jsonify({'error': '修改密码失败'}), 500

        return jsonify({'message': '密码修改成功'})

    except Exception as e:
        return jsonify({'error': f'修改密码失败: {str(e)}'}), 500


@users_bp.route('/<int:user_id>/role', methods=['PUT'])
@require_auth
@require_admin
def update_user_role(user_id):
    """修改用户角色"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供角色信息'}), 400

        role = data.get('role')
        if not role:
            return jsonify({'error': '请提供角色'}), 400

        valid_roles = ['user', 'admin', 'tenant_admin', 'tenant_member']
        if role not in valid_roles:
            return jsonify({'error': f'无效的角色，允许的角色: {", ".join(valid_roles)}'}), 400

        # 不允许修改admin用户的角色
        user = auth_manager.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        if user['username'] == 'admin':
            return jsonify({'error': '不能修改默认管理员的角色'}), 400

        success = auth_manager.update_user(user_id, role=role)
        if not success:
            return jsonify({'error': '修改角色失败'}), 500

        # 获取更新后的用户信息
        user = auth_manager.get_user_by_id(user_id)

        return jsonify({
            'message': '用户角色修改成功',
            'user': user
        })

    except Exception as e:
        return jsonify({'error': f'修改用户角色失败: {str(e)}'}), 500


@users_bp.route('/<int:user_id>/status', methods=['PUT'])
@require_auth
@require_admin
def update_user_status(user_id):
    """启用/禁用用户"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供状态信息'}), 400

        is_active = data.get('is_active')
        if is_active is None:
            return jsonify({'error': '请提供is_active参数'}), 400

        # 不允许禁用自己
        if request.current_user['user_id'] == user_id and not is_active:
            return jsonify({'error': '不能禁用自己的账号'}), 400

        # 不允许禁用admin用户
        user = auth_manager.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        if user['username'] == 'admin' and not is_active:
            return jsonify({'error': '不能禁用默认管理员账号'}), 400

        success = auth_manager.update_user(user_id, is_active=is_active)
        if not success:
            return jsonify({'error': '修改状态失败'}), 500

        # 获取更新后的用户信息
        user = auth_manager.get_user_by_id(user_id)

        return jsonify({
            'message': f'用户已{"启用" if is_active else "禁用"}',
            'user': user
        })

    except Exception as e:
        return jsonify({'error': f'修改用户状态失败: {str(e)}'}), 500


@users_bp.route('/stats', methods=['GET'])
@require_auth
@require_admin
def get_user_stats():
    """获取用户统计信息"""
    try:
        total = auth_manager.count_users()
        active = auth_manager.count_users(is_active=True)
        inactive = auth_manager.count_users(is_active=False)
        admins = auth_manager.count_users(role='admin')
        users = auth_manager.count_users(role='user')

        return jsonify({
            'total': total,
            'active': active,
            'inactive': inactive,
            'admins': admins,
            'users': users
        })

    except Exception as e:
        return jsonify({'error': f'获取统计信息失败: {str(e)}'}), 500
