"""
QueenBee应用主模块
"""
from flask import Flask
from app.api.routes import api_bp, init_api

def create_app():
    """创建Flask应用"""
    app = Flask(__name__, 
                static_folder='static',
                static_url_path='/static',
                template_folder='templates')
    
    # 注册蓝图
    app.register_blueprint(api_bp)
    
    return app
