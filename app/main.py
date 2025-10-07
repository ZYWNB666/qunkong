"""
Qunkong 主服务器入口
"""
import asyncio
import threading
from flask import Flask, render_template
from flask_cors import CORS
from app import create_app
from app.api.routes import init_api
from app.api.auth import init_auth, auth_bp
from app.api.jobs import init_jobs, jobs_bp
from app.api.simple_jobs import init_simple_jobs, simple_jobs_bp
from app.server_core import QunkongServer

def create_flask_app():
    """创建Flask应用"""
    app = create_app()
    
    # 启用CORS支持
    CORS(app, supports_credentials=True)
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app

def start_websocket_server(server):
    """启动WebSocket服务器"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.start())

def main():
    """主函数"""
    # 创建WebSocket服务器
    websocket_server = QunkongServer(host="0.0.0.0", port=8765, web_port=5000)
    
    # 创建Flask应用
    flask_app = create_flask_app()
    
    # 初始化认证系统
    init_auth(websocket_server.db)
    
    # 初始化作业管理
    init_jobs(websocket_server.db)
    
    # 初始化简单作业管理
    init_simple_jobs(websocket_server.db, websocket_server)
    
    # 注册蓝图
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(jobs_bp)
    flask_app.register_blueprint(simple_jobs_bp)
    
    # 初始化API
    init_api(websocket_server)
    
    # 在单独线程中启动WebSocket服务器
    websocket_thread = threading.Thread(target=start_websocket_server, args=(websocket_server,))
    websocket_thread.daemon = True
    websocket_thread.start()
    
    # 启动Flask应用
    print("Web 服务器启动在 http://0.0.0.0:5000")
    print("Qunkong 服务器启动在 ws://0.0.0.0:8765")
    print("默认管理员账户: admin/admin123")
    flask_app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
