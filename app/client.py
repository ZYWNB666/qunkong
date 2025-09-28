"""
QueenBee Agent 客户端
"""
import asyncio
import websockets
import json
import logging
import platform
import psutil
import hashlib
import subprocess
import os
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueenBeeAgent:
    """QueenBee Agent 客户端"""
    
    def __init__(self, server_host="localhost", server_port=8765, agent_id=None):
        self.server_host = server_host
        self.server_port = server_port
        self.hostname = platform.node()
        self.ip = self.get_local_ip()
        # 如果没有指定agent_id，使用IP的MD5值
        self.agent_id = agent_id or hashlib.md5(self.ip.encode('utf-8')).hexdigest()
        self.websocket = None
        self.running = False

    def get_local_ip(self):
        """获取本地IP地址"""
        import socket
        try:
            # 连接到服务器获取本机IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 使用服务器地址，如果是localhost则使用8.8.8.8
            target_host = self.server_host if self.server_host != 'localhost' else '8.8.8.8'
            s.connect((target_host, 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def get_system_info(self):
        """获取系统信息"""
        try:
            import os
            import subprocess

            # 基本信息
            system_info = {
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version(),
                'hostname': platform.node(),
                'architecture': platform.architecture()[0]
            }

            logger.info(f"收集到系统信息: {system_info}")

            # CPU信息
            try:
                cpu_info = {
                    'cpu_count': psutil.cpu_count(),
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                    'cpu_times': psutil.cpu_times()._asdict()
                }

                # 根据系统类型获取更详细的CPU信息
                if platform.system() == "Windows":
                    try:
                        # Windows系统获取CPU型号
                        result = subprocess.run(['wmic', 'cpu', 'get', 'name'],
                                              capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')
                            if len(lines) > 1:
                                cpu_info['model'] = lines[1].strip()
                    except:
                        pass
                else:
                    try:
                        # Linux系统获取CPU型号
                        with open('/proc/cpuinfo', 'r') as f:
                            for line in f:
                                if line.startswith('model name'):
                                    cpu_info['model'] = line.split(':')[1].strip()
                                    break
                    except:
                        pass

            except Exception as e:
                logger.warning(f"获取CPU信息失败: {e}")
                cpu_info = {}

            # 内存信息
            try:
                memory = psutil.virtual_memory()
                memory_info = {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free
                }

                # 获取交换分区信息
                try:
                    swap = psutil.swap_memory()
                    memory_info['swap'] = {
                        'total': swap.total,
                        'used': swap.used,
                        'free': swap.free,
                        'percent': swap.percent
                    }
                except:
                    pass

            except Exception as e:
                logger.warning(f"获取内存信息失败: {e}")
                memory_info = {}

            # 磁盘信息
            disk_info = []
            try:
                for partition in psutil.disk_partitions():
                    try:
                        partition_usage = psutil.disk_usage(partition.mountpoint)
                        disk_info.append({
                            'device': partition.device,
                            'mountpoint': partition.mountpoint,
                            'fstype': partition.fstype,
                            'total': partition_usage.total,
                            'used': partition_usage.used,
                            'free': partition_usage.free,
                            'percent': partition_usage.percent
                        })
                    except PermissionError:
                        continue
            except Exception as e:
                logger.warning(f"获取磁盘信息失败: {e}")
                disk_info = []

            # 网络信息
            network_info = []
            try:
                for interface, addrs in psutil.net_if_addrs().items():
                    interface_info = {
                        'interface': interface,
                        'addresses': []
                    }
                    for addr in addrs:
                        interface_info['addresses'].append({
                            'family': str(addr.family),
                            'address': addr.address,
                            'netmask': addr.netmask,
                            'broadcast': addr.broadcast
                        })
                    network_info.append(interface_info)
            except Exception as e:
                logger.warning(f"获取网络信息失败: {e}")
                network_info = []

            # 系统特定信息
            system_specific = {}
            try:
                if platform.system() == "Windows":
                    # Windows特定信息
                    system_specific = self._get_windows_info()
                else:
                    # Linux/Unix特定信息
                    system_specific = self._get_linux_info()
            except Exception as e:
                logger.warning(f"获取系统特定信息失败: {e}")
                system_specific = {}

            return {
                'system_info': system_info,
                'cpu_info': cpu_info,
                'memory_info': memory_info,
                'disk_info': disk_info,
                'network_info': network_info,
                'system_specific': system_specific
            }
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {}

    def _get_windows_info(self):
        """获取Windows特定信息"""
        import subprocess
        import os

        info = {}
        try:
            # 获取Windows版本信息
            result = subprocess.run(['ver'], capture_output=True, text=True, shell=True, timeout=5)
            if result.returncode == 0:
                info['windows_version'] = result.stdout.strip()
        except:
            pass

        try:
            # 获取计算机信息
            result = subprocess.run(['systeminfo'], capture_output=True, text=True, shell=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'OS Name:' in line:
                        info['os_name'] = line.split(':', 1)[1].strip()
                    elif 'OS Version:' in line:
                        info['os_version'] = line.split(':', 1)[1].strip()
                    elif 'System Type:' in line:
                        info['system_type'] = line.split(':', 1)[1].strip()
                    elif 'Total Physical Memory:' in line:
                        info['total_physical_memory'] = line.split(':', 1)[1].strip()
        except:
            pass

        try:
            # 获取环境变量
            info['username'] = os.environ.get('USERNAME', 'Unknown')
            info['computername'] = os.environ.get('COMPUTERNAME', 'Unknown')
        except:
            pass

        return info

    def _get_linux_info(self):
        """获取Linux特定信息"""
        import subprocess
        import os

        info = {}
        try:
            # 获取Linux发行版信息
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            info['distribution'] = line.split('=', 1)[1].strip().strip('"')
                        elif line.startswith('VERSION='):
                            info['version'] = line.split('=', 1)[1].strip().strip('"')
        except:
            pass

        try:
            # 获取内核版本
            result = subprocess.run(['uname', '-r'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info['kernel_version'] = result.stdout.strip()
        except:
            pass

        try:
            # 获取系统负载
            result = subprocess.run(['uptime'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info['uptime'] = result.stdout.strip()
        except:
            pass

        try:
            # 获取环境变量
            info['username'] = os.environ.get('USER', 'Unknown')
            info['home'] = os.environ.get('HOME', 'Unknown')
            info['shell'] = os.environ.get('SHELL', 'Unknown')
        except:
            pass

        return info

    def _convert_bash_to_batch(self, script):
        """将bash脚本转换为Windows批处理脚本的基本转换"""
        lines = script.split('\n')
        converted_lines = ['@echo off']
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # 基本的bash到批处理转换
            if line.startswith('echo '):
                # echo命令保持不变，但需要处理变量
                converted_line = line.replace('$(pwd)', '%CD%').replace('$(whoami)', '%USERNAME%')
                # 处理bash变量引用 $VAR -> %VAR%
                import re
                converted_line = re.sub(r'\$([A-Za-z_][A-Za-z0-9_]*)', r'%\1%', converted_line)
                converted_lines.append(converted_line)
            elif '=' in line and not line.startswith('if ') and not line.startswith('for '):
                # 变量赋值: VAR="value" -> set VAR=value
                if '"' in line:
                    var_name, var_value = line.split('=', 1)
                    var_value = var_value.strip().strip('"')
                    converted_lines.append(f'set {var_name}={var_value}')
                else:
                    converted_lines.append(f'set {line}')
            else:
                # 其他命令直接保留
                converted_lines.append(line)
        
        return '\n'.join(converted_lines)

    async def register_with_server(self):
        """向服务器注册"""
        # 获取系统信息
        system_info = self.get_system_info()

        register_message = {
            'type': 'register',
            'agent_id': self.agent_id,
            'hostname': self.hostname,
            'ip': self.ip,
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'system_info': system_info
        }

        await self.websocket.send(json.dumps(register_message))
        logger.info(f"向服务器注册: {self.hostname}")

    async def send_heartbeat(self):
        """发送心跳"""
        heartbeat_message = {
            'type': 'heartbeat',
            'agent_id': self.agent_id,
            'timestamp': datetime.now().isoformat()
        }
        await self.websocket.send(json.dumps(heartbeat_message))

    async def execute_script(self, script, script_params="", timeout=7200, execution_user="root", task_id=None):
        """执行脚本"""
        import subprocess
        import time
        import tempfile
        import os
        
        start_time = time.time()
        temp_script_path = None
        
        try:
            # 生成临时文件名，使用task_id作为文件名的一部分
            if task_id:
                temp_filename = f"queenbee_script_{task_id}.sh"
            else:
                temp_filename = f"queenbee_script_{int(time.time())}.sh"
            
            # 创建临时脚本文件
            temp_dir = tempfile.gettempdir()
            temp_script_path = os.path.join(temp_dir, temp_filename)
            
            # 根据脚本类型确定解释器和扩展名
            is_python = script.startswith('#!/usr/bin/env python3') or script.startswith('#!/usr/bin/python')
            is_windows = platform.system().lower() == 'windows'
            
            if is_python:
                # Python脚本
                interpreter = 'python'
                temp_script_path = temp_script_path.replace('.sh', '.py')
            else:
                # Shell脚本 - 对于Windows，我们尝试使用bash（如果可用）
                if is_windows:
                    # Windows下尝试使用bash（Git Bash, WSL等）
                    interpreter = 'bash'
                    temp_script_path = temp_script_path.replace('.sh', '.bat')
                    # 如果是bash脚本，进行基本的Windows批处理转换
                    if script.startswith('#!/bin/bash') or script.startswith('#!/bin/sh'):
                        # 移除shebang行
                        script_lines = script.split('\n')
                        if script_lines[0].startswith('#!'):
                            script = '\n'.join(script_lines[1:])
                    
                    # 进行基本的bash到批处理的转换
                    script = self._convert_bash_to_batch(script)
                else:
                    interpreter = '/bin/bash'
                    if not script.startswith('#!'):
                        script = '#!/bin/bash\n' + script
            
            # 将脚本内容写入临时文件
            with open(temp_script_path, 'w', encoding='utf-8') as f:
                f.write(script)
            
            # 给脚本文件添加执行权限（仅在非Windows系统）
            if not is_windows:
                os.chmod(temp_script_path, 0o755)
            
            # 构建执行命令
            if is_python:
                cmd = [interpreter, temp_script_path]
            elif is_windows:
                # Windows下直接执行批处理文件
                cmd = [temp_script_path]
            else:
                cmd = ['/bin/bash', temp_script_path]
            
            # 添加脚本参数
            if script_params:
                # 将参数字符串按空格分割，但要考虑引号内的空格
                import shlex
                try:
                    params = shlex.split(script_params)
                    cmd.extend(params)
                except ValueError:
                    # 如果参数解析失败，按简单空格分割
                    cmd.extend(script_params.split())
            
            logger.debug(f"执行命令: {' '.join(cmd)}")
            
            # 执行脚本
            # Windows下需要指定编码以避免GBK编码问题
            encoding = 'utf-8' if not is_windows else 'gbk'
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd(),
                encoding=encoding,
                errors='replace'  # 遇到编码错误时替换为?
            )
            
            execution_time = time.time() - start_time
            
            return {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'execution_time': execution_time
            }
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return {
                'exit_code': -1,
                'stdout': '',
                'stderr': f'脚本执行超时 (>{timeout}秒)',
                'execution_time': execution_time
            }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'exit_code': -1,
                'stdout': '',
                'stderr': f'执行错误: {str(e)}',
                'execution_time': execution_time
            }
        finally:
            # 清理临时文件
            if temp_script_path and os.path.exists(temp_script_path):
                try:
                    os.remove(temp_script_path)
                    logger.debug(f"已删除临时脚本文件: {temp_script_path}")
                except Exception as e:
                    logger.warning(f"删除临时脚本文件失败: {e}")

    async def handle_server_message(self, message):
        """处理服务器消息"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'register_confirm':
                logger.info(f"注册确认: {data.get('message')}")
            elif msg_type == 'execute_task':
                # 执行任务
                task_id = data.get('task_id')
                script = data.get('script')
                script_params = data.get('script_params', '')
                timeout = data.get('timeout', 7200)
                execution_user = data.get('execution_user', 'root')
                
                logger.info(f"收到执行任务: {task_id}")
                
                # 执行脚本，传递task_id用于生成临时文件名
                result = await self.execute_script(
                    script=script,
                    script_params=script_params,
                    timeout=timeout,
                    execution_user=execution_user,
                    task_id=task_id
                )
                
                # 发送结果
                result_message = {
                    'type': 'task_result',
                    'task_id': task_id,
                    'agent_id': self.agent_id,
                    'result': result
                }
                
                await self.websocket.send(json.dumps(result_message))
                logger.info(f"任务 {task_id} 执行完成")
                
        except Exception as e:
            logger.error(f"处理服务器消息失败: {e}")

    async def run(self):
        """运行Agent"""
        self.running = True
        logger.info(f"Agent 初始化: {self.hostname} ({self.ip})")
        logger.info(f"QueenBee Agent 启动: {self.hostname}")
        
        # 重连参数
        max_retries = 10
        retry_delay = 5  # 初始重连延迟
        max_retry_delay = 60  # 最大重连延迟
        
        retry_count = 0
        
        while self.running and retry_count < max_retries:
            try:
                logger.info(f"连接到服务器: ws://{self.server_host}:{self.server_port}")
                
                # 设置WebSocket连接参数
                connect_kwargs = {
                    'ping_interval': 20,  # 每20秒发送ping
                    'ping_timeout': 10,   # ping超时时间
                    'close_timeout': 10,  # 关闭超时时间
                    'max_size': 2**20,    # 最大消息大小1MB
                    'max_queue': 32       # 最大队列大小
                }
                
                async with websockets.connect(
                    f"ws://{self.server_host}:{self.server_port}",
                    **connect_kwargs
                ) as websocket:
                    self.websocket = websocket
                    retry_count = 0  # 连接成功，重置重试计数
                    
                    # 注册到服务器
                    await self.register_with_server()
                    
                    # 启动心跳任务
                    heartbeat_task_handle = None
                    try:
                        async def heartbeat_task():
                            while self.running and not websocket.closed:
                                try:
                                    await self.send_heartbeat()
                                    await asyncio.sleep(3)  # 每3秒发送一次心跳
                                except websockets.exceptions.ConnectionClosed:
                                    logger.warning("心跳发送失败: 连接已关闭")
                                    break
                                except Exception as e:
                                    logger.error(f"心跳发送失败: {e}")
                                    break
                        
                        heartbeat_task_handle = asyncio.create_task(heartbeat_task())
                        
                        # 处理服务器消息
                        async for message in websocket:
                            await self.handle_server_message(message)
                            
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("WebSocket连接已关闭")
                    except Exception as e:
                        logger.error(f"处理消息时出错: {e}")
                    finally:
                        # 取消心跳任务
                        if heartbeat_task_handle and not heartbeat_task_handle.done():
                            heartbeat_task_handle.cancel()
                            try:
                                await heartbeat_task_handle
                            except asyncio.CancelledError:
                                pass
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket连接意外关闭")
            except websockets.exceptions.InvalidURI:
                logger.error(f"无效的WebSocket URI: ws://{self.server_host}:{self.server_port}")
                break
            except OSError as e:
                logger.error(f"网络连接错误: {e}")
            except Exception as e:
                logger.error(f"Agent 运行错误: {e}")
            
            # 如果还在运行状态，准备重连
            if self.running and retry_count < max_retries:
                retry_count += 1
                current_delay = min(retry_delay * (2 ** (retry_count - 1)), max_retry_delay)
                logger.info(f"将在 {current_delay} 秒后尝试重连 (第 {retry_count}/{max_retries} 次)")
                await asyncio.sleep(current_delay)
            elif retry_count >= max_retries:
                logger.error("达到最大重连次数，Agent停止运行")
                break
        
        self.running = False
        logger.info("Agent 已停止")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='QueenBee Agent 客户端')
    parser.add_argument('--server', '-s', default='localhost', 
                       help='服务器地址 (默认: localhost)')
    parser.add_argument('--port', '-p', type=int, default=8765, 
                       help='服务器端口 (默认: 8765)')
    parser.add_argument('--agent-id', '-i', 
                       help='Agent ID (默认: 使用IP的MD5值)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细日志输出')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"启动参数: 服务器={args.server}:{args.port}")
    
    agent = QueenBeeAgent(
        server_host=args.server,
        server_port=args.port,
        agent_id=args.agent_id
    )
    
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("Agent 已停止")
    except Exception as e:
        logger.error(f"Agent 启动失败: {e}")

if __name__ == '__main__':
    main()
