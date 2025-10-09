# -*- coding: utf-8 -*-
"""
Qunkong Agent 客户端 - Linux专用版本
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
import pty
import select
import termios
import struct
import fcntl
import signal
import threading
import queue
import requests
import time
import sys
import tempfile

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QunkongAgent:
    """Qunkong Agent 客户端"""
    
    def __init__(self, server_host="localhost", server_port=8765, agent_id=None, log_level="INFO"):
        self.server_host = server_host
        self.server_port = server_port
        self.hostname = platform.node()
        
        # 设置日志级别
        if log_level == "DEBUG":
            logger.setLevel(logging.DEBUG)
        elif log_level == "INFO":
            logger.setLevel(logging.INFO)
        elif log_level == "WARNING":
            logger.setLevel(logging.WARNING)
        
        # 获取内网IP
        self.ip = self.get_local_ip()  # 内网IP
        logger.info(f"获取内网IP: {self.ip}")
        
        # 获取外网IP
        self.external_ip = self.get_external_ip()  # 外网IP
        logger.info(f"获取外网IP: {self.external_ip}")
        
        # 如果没有指定agent_id，使用内网IP的MD5值
        self.agent_id = agent_id or hashlib.md5(self.ip.encode('utf-8')).hexdigest()
        self.websocket = None
        self.running = False
        # 终端会话管理 - PTY终端
        self.terminal_sessions = {}  # session_id -> {'pty_fd': fd, 'process': process, 'thread': thread, 'output_queue': queue}
        self.current_directory = os.path.expanduser("~")  # 当前工作目录
        # 命令缓冲区，用于记录完整的用户命令
        self.command_buffers = {}  # session_id -> current_command_buffer

    def get_local_ip(self):
        """获取本地内网IP地址"""
        import socket
        try:
            # 优先获取内网IP地址
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 连接到局域网地址来获取内网IP
            s.connect(("10.254.254.254", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            # 如果上面失败，尝试其他方法获取内网IP
            try:
                import socket
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                # 确保是内网IP（不是127.0.0.1）
                if local_ip != "127.0.0.1":
                    return local_ip
            except:
                pass
            return "127.0.0.1"

    def get_external_ip(self):
        """获取外网IP地址"""
        import socket
        
        # 方法1：通过连接外部服务器获取（这个方法通常能获取到外网IP）
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            external_ip = s.getsockname()[0]
            s.close()
            
            # 检查是否是内网IP，如果是则尝试其他方法
            if not self._is_private_ip(external_ip):
                logger.info(f"通过socket获取外网IP: {external_ip}")
                return external_ip
        except Exception as e:
            logger.warning(f"方法1获取外网IP失败: {e}")
        
        # 方法2：通过HTTP请求获取外网IP
        try:
            response = requests.get('https://httpbin.org/ip', timeout=10)
            if response.status_code == 200:
                external_ip = response.json().get('origin', '').split(',')[0].strip()
                logger.info(f"通过HTTP请求获取外网IP: {external_ip}")
                return external_ip
        except Exception as e:
            logger.warning(f"方法2获取外网IP失败: {e}")
        
        # 方法3：使用其他免费IP查询服务
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=10)
            if response.status_code == 200:
                external_ip = response.json().get('ip', '').strip()
                logger.info(f"通过ipify获取外网IP: {external_ip}")
                return external_ip
        except Exception as e:
            logger.warning(f"方法3获取外网IP失败: {e}")
        
        logger.warning("所有方法都无法获取外网IP")
        return None
    
    def _is_private_ip(self, ip):
        """检查是否是私有IP地址"""
        try:
            import ipaddress
            ip_obj = ipaddress.IPv4Address(ip)
            return ip_obj.is_private
        except:
            # 简单检查常见的私有IP段
            if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                return True
            if ip.startswith('127.') or ip == 'localhost':
                return True
            return False

    def get_system_info(self):
        """获取系统信息"""
        try:
            import os
            import subprocess

            # 基本信息
            system_info = {
                'platform': 'Linux',
                'system': 'Linux',
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version(),
                'hostname': platform.node(),
                'architecture': platform.architecture()[0]
            }

            logger.info("收集到系统信息: {}".format(system_info))

            # CPU信息
            try:
                cpu_info = {
                    'cpu_count': psutil.cpu_count(),
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                    'cpu_times': psutil.cpu_times()._asdict()
                }

                # 获取CPU型号信息
                try:
                    with open('/proc/cpuinfo', 'r') as f:
                        for line in f:
                            if line.startswith('model name'):
                                cpu_info['model'] = line.split(':')[1].strip()
                                break
                except:
                    pass

            except Exception as e:
                logger.warning("获取CPU信息失败: {}".format(e))
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
                logger.warning("获取内存信息失败: {}".format(e))
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
                            'percent': round(partition_usage.percent, 1)
                        })
                    except (PermissionError, OSError):
                        # 跳过无法访问的分区
                        continue
            except Exception as e:
                logger.warning("获取磁盘信息失败: {}".format(e))
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
                logger.warning("获取网络信息失败: {}".format(e))
                network_info = []

            # 系统特定信息 - 只支持Linux
            system_specific = {}
            try:
                system_specific = self._get_linux_info()
            except Exception as e:
                logger.warning("获取系统特定信息失败: {}".format(e))
                system_specific = {}

            # 格式化系统信息以匹配前端显示需求
            formatted_system_info = {
                # 操作系统信息
                'os': "Linux {}".format(system_info.get('release', '')),
                'kernel': system_info.get('version', 'Unknown'),
                'architecture': system_info.get('architecture', 'Unknown'),
                'hostname': system_info.get('hostname', 'Unknown'),
                
                # CPU信息
                'cpu': self._format_cpu_info(cpu_info),
                'cpu_usage': psutil.cpu_percent(interval=1),
                'cpu_count': cpu_info.get('cpu_count', 0),
                
                # 内存信息
                'memory': self._format_memory_info(memory_info),
                'memory_usage': memory_info.get('percent', 0) if memory_info else 0,
                
                # 磁盘信息
                'disk': self._format_disk_info(disk_info),
                'disk_usage': self._get_disk_usage_percent(disk_info),
                
                # 网络信息
                'network': self._format_network_info(network_info),
                
                # 系统运行时间和负载
                'uptime': self._get_system_uptime(),
                'load_average': self._get_load_average(),
            }

            return {
                'system_info': formatted_system_info,
                'cpu_info': cpu_info,
                'memory_info': memory_info,
                'disk_info': disk_info,
                'network_info': network_info,
                'system_specific': system_specific
            }
        except Exception as e:
            logger.error("获取系统信息失败: {}".format(e))
            return {}

    def _get_linux_info(self):
        """获取Linux系统信息"""
        import subprocess
        import os

        info = {}
        try:
            # 获取Linux发行版信息
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            info['os_name'] = line.split('=', 1)[1].strip().strip('"')
                        elif line.startswith('VERSION_ID='):
                            info['os_version'] = line.split('=', 1)[1].strip().strip('"')
                        elif line.startswith('ID='):
                            info['distribution'] = line.split('=', 1)[1].strip().strip('"')
            
            # 获取内核信息
            result = subprocess.run(['uname', '-r'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info['kernel_version'] = result.stdout.strip()
                
            # 获取系统架构
            result = subprocess.run(['uname', '-m'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info['architecture'] = result.stdout.strip()
                
            # 获取用户信息
            info['username'] = os.environ.get('USER', 'Unknown')
            info['home'] = os.environ.get('HOME', '/root')
            
        except Exception as e:
            logger.warning(f"获取Linux信息失败: {e}")
            
        return info

    def _format_cpu_info(self, cpu_info):
        """格式化CPU信息"""
        if not cpu_info:
            return "Unknown CPU"
        
        cpu_model = cpu_info.get('model', 'Unknown CPU')
        cpu_count = cpu_info.get('cpu_count', 0)
        
        if cpu_count > 0:
            return "{} ({} cores)".format(cpu_model, cpu_count)
        return cpu_model

    def _format_memory_info(self, memory_info):
        """格式化内存信息"""
        if not memory_info:
            return "Unknown Memory"
        
        total = memory_info.get('total', 0)
        used = memory_info.get('used', 0)
        free = memory_info.get('free', 0)
        
        if total > 0:
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            return "{:.1f}GB (Used: {:.1f}GB, Free: {:.1f}GB)".format(total_gb, used_gb, free_gb)
        
        return "Unknown Memory"

    def _format_disk_info(self, disk_info):
        """格式化磁盘信息"""
        if not disk_info or len(disk_info) == 0:
            return "Unknown Disk"
        
        # 获取主要磁盘信息（通常是第一个）
        main_disk = disk_info[0] if disk_info else {}
        total = main_disk.get('total', 0)
        used = main_disk.get('used', 0)
        free = main_disk.get('free', 0)
        device = main_disk.get('device', 'Unknown')
        
        if total > 0:
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            return "{}: {:.1f}GB (Used: {:.1f}GB, Free: {:.1f}GB)".format(device, total_gb, used_gb, free_gb)
        
        return "Unknown Disk"

    def _format_network_info(self, network_info):
        """格式化网络信息"""
        if not network_info:
            return "Unknown Network"
        
        interfaces = []
        for interface in network_info:
            name = interface.get('interface', 'Unknown')
            addresses = interface.get('addresses', [])
            
            # 找到IPv4地址
            ipv4_addr = None
            for addr in addresses:
                if 'IPv4' in str(addr.get('family', '')) or addr.get('family') == '2':
                    ipv4_addr = addr.get('address')
                    break
            
            if ipv4_addr and not ipv4_addr.startswith('127.'):
                interfaces.append("{}: {}".format(name, ipv4_addr))
        
        return ', '.join(interfaces) if interfaces else "No active interfaces"

    def _get_disk_usage_percent(self, disk_info):
        """获取磁盘使用率"""
        if not disk_info or len(disk_info) == 0:
            return 0
        
        main_disk = disk_info[0] if disk_info else {}
        return main_disk.get('percent', 0)

    def _get_system_uptime(self):
        """获取系统运行时间"""
        try:
            import time
            uptime_seconds = time.time() - psutil.boot_time()
            
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            if days > 0:
                return "{} days, {} hours, {} minutes".format(days, hours, minutes)
            elif hours > 0:
                return "{} hours, {} minutes".format(hours, minutes)
            else:
                return "{} minutes".format(minutes)
        except:
            return "Unknown"

    def _get_load_average(self):
        """获取系统负载"""
        try:
            load_avg = os.getloadavg()
            return "{:.2f}, {:.2f}, {:.2f}".format(load_avg[0], load_avg[1], load_avg[2])
        except:
            return "Unknown"

    async def register_with_server(self):
        """向服务器注册"""
        # 获取系统信息
        system_info = self.get_system_info()

        register_message = {
            'type': 'register',
            'agent_id': self.agent_id,
            'hostname': self.hostname,
            'ip': self.ip,  # 内网IP
            'external_ip': self.external_ip,  # 外网IP
            'platform': 'Linux',
            'python_version': platform.python_version(),
            'system_info': system_info
        }

        logger.info(f"发送注册消息: hostname={self.hostname}, ip={self.ip}, external_ip={self.external_ip}")
        await self.websocket.send(json.dumps(register_message))
        logger.info("向服务器注册: {}".format(self.hostname))

    async def send_heartbeat(self, websocket=None):
        """发送心跳"""
        if websocket is None:
            websocket = self.websocket
        try:
            heartbeat_message = {
                'type': 'heartbeat',
                'agent_id': self.agent_id,
                'timestamp': datetime.now().isoformat()
            }
            message_json = json.dumps(heartbeat_message)
            await websocket.send(message_json)
            # 移除频繁的心跳日志，减少I/O开销
        except Exception as e:
            logger.error("send_heartbeat 内部异常: {} (类型: {})".format(e, type(e).__name__))
            raise

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
                temp_filename = "qunkong_script_{}.sh".format(task_id)
            else:
                temp_filename = "qunkong_script_{}.sh".format(int(time.time()))
            
            # 创建临时脚本文件
            temp_dir = tempfile.gettempdir()
            temp_script_path = os.path.join(temp_dir, temp_filename)
            
            # 根据脚本类型确定解释器和扩展名
            is_python = script.startswith('#!/usr/bin/env python3') or script.startswith('#!/usr/bin/python')
            
            if is_python:
                # Python脚本
                interpreter = 'python3'
                temp_script_path = temp_script_path.replace('.sh', '.py')
            else:
                # Shell脚本
                interpreter = '/bin/bash'
                if not script.startswith('#!'):
                    script = '#!/bin/bash\n' + script
            
            # 将脚本内容写入临时文件
            with open(temp_script_path, 'w', encoding='utf-8') as f:
                f.write(script)
            
            # 给脚本文件添加执行权限
            os.chmod(temp_script_path, 0o755)
            
            # 构建执行命令
            if is_python:
                cmd = [interpreter, temp_script_path]
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
            
            logger.debug("执行命令: {}".format(' '.join(cmd)))
            
            # 执行脚本
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd(),
                encoding='utf-8',
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
                    logger.debug("已删除临时脚本文件: {}".format(temp_script_path))
                except Exception as e:
                    logger.warning("删除临时脚本文件失败: {}".format(e))

    async def handle_server_message(self, message):
        """处理服务器消息"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'register_confirm':
                logger.info("注册确认: {}".format(data.get('message')))
            elif msg_type == 'execute_task':
                # 执行任务
                task_id = data.get('task_id')
                script = data.get('script')
                script_params = data.get('script_params', '')
                timeout = data.get('timeout', 7200)
                execution_user = data.get('execution_user', 'root')
                
                logger.info("收到执行任务: {}".format(task_id))
                
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
                logger.info("任务 {} 执行完成".format(task_id))
            elif msg_type == 'restart_agent':
                # 重启Agent
                logger.info("收到重启Agent命令")
                await self.handle_restart_agent()
            elif msg_type == 'restart_host':
                # 重启主机
                logger.info("收到重启主机命令")
                await self.handle_restart_host()
            elif msg_type == 'terminal_init':
                # 初始化PTY终端
                session_id = data.get('session_id')
                cols = data.get('cols', 80)
                rows = data.get('rows', 24)
                logger.info(f"收到PTY终端初始化命令: {session_id} ({cols}x{rows})")
                await self.handle_terminal_init(session_id, cols, rows)
            elif msg_type == 'terminal_input':
                # 处理终端输入
                session_id = data.get('session_id')
                input_data = data.get('data', '')
                logger.debug(f"收到终端输入: {session_id}")
                await self.handle_terminal_input(session_id, input_data)
            elif msg_type == 'terminal_resize':
                # 调整终端大小
                session_id = data.get('session_id')
                cols = data.get('cols', 80)
                rows = data.get('rows', 24)
                logger.info(f"收到调整终端大小命令: {session_id} ({cols}x{rows})")
                await self.handle_terminal_resize(session_id, cols, rows)
            elif msg_type == 'terminal_close':
                # 关闭PTY终端
                session_id = data.get('session_id')
                logger.info(f"收到终端关闭命令: {session_id}")
                await self.handle_terminal_close(session_id)
            elif msg_type == 'update_agent':
                # 更新Agent
                download_url = data.get('download_url')
                version = data.get('version', 'unknown')
                md5_expected = data.get('md5', '')
                logger.info(f"收到更新Agent命令: 版本 {version}, URL: {download_url}, MD5: {md5_expected}")
                await self.handle_update_agent(download_url, version, md5_expected)
                
        except Exception as e:
            logger.error("处理服务器消息失败: {}".format(e))

    async def handle_restart_agent(self):
        """处理重启Agent命令"""
        try:
            # 发送重启响应
            response_message = {
                'type': 'restart_agent_response',
                'agent_id': self.agent_id,
                'restart_type': 'agent',
                'success': True,
                'message': 'Agent restart initiated'
            }
            await self.websocket.send(json.dumps(response_message))
            
            logger.info("Agent重启中...")
            
            # 设置停止标志
            self.running = False
            
            # 延迟一点时间让响应发送完成
            await asyncio.sleep(1)
            
            # 重启Agent进程
            import os
            import sys
            
            # 获取当前脚本的完整路径和参数
            python_executable = sys.executable
            script_path = os.path.abspath(__file__)
            
            # 构建重启命令
            restart_cmd = [python_executable, script_path]
            
            # 添加原始启动参数（如果有的话）
            if hasattr(sys, 'argv') and len(sys.argv) > 1:
                restart_cmd.extend(sys.argv[1:])
            
            logger.info("重启命令: {}".format(' '.join(restart_cmd)))
            
            # 启动新进程
            import subprocess
            subprocess.Popen(restart_cmd, 
                           cwd=os.getcwd(),
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            
            # 退出当前进程
            os._exit(0)
            
        except Exception as e:
            logger.error("重启Agent失败: {}".format(e))
            # 发送失败响应
            try:
                error_response = {
                    'type': 'restart_agent_response',
                    'agent_id': self.agent_id,
                    'restart_type': 'agent',
                    'success': False,
                    'error_message': str(e)
                }
                await self.websocket.send(json.dumps(error_response))
            except:
                pass

    async def handle_restart_host(self):
        """处理重启主机命令"""
        try:
            import subprocess
            
            # 发送重启响应
            response_message = {
                'type': 'restart_host_response',
                'agent_id': self.agent_id,
                'restart_type': 'host',
                'success': True,
                'message': 'Host restart initiated on Linux'
            }
            await self.websocket.send(json.dumps(response_message))
            
            logger.info("主机重启中... (系统类型: Linux)")
            
            # 延迟一点时间让响应发送完成
            await asyncio.sleep(2)
            
            # 执行Linux重启命令
            try:
                # 尝试使用systemctl (systemd)
                subprocess.run(['sudo', 'systemctl', 'reboot'], check=False, timeout=5)
            except:
                try:
                    # 备用方案：使用reboot命令
                    subprocess.run(['sudo', 'reboot'], check=False, timeout=5)
                except:
                    # 最后备用方案：使用shutdown命令
                    subprocess.run(['sudo', 'shutdown', '-r', 'now'], check=False, timeout=5)
                
        except Exception as e:
            logger.error("重启主机失败: {}".format(e))
            # 发送失败响应
            try:
                error_response = {
                    'type': 'restart_host_response',
                    'agent_id': self.agent_id,
                    'restart_type': 'host',
                    'success': False,
                    'error_message': str(e)
                }
                await self.websocket.send(json.dumps(error_response))
            except:
                pass

    async def handle_update_agent(self, download_url: str, version: str, md5_expected: str = ''):
        """处理更新Agent命令"""
        try:
            logger.info(f"开始更新Agent: 版本 {version}, URL: {download_url}, MD5: {md5_expected}")
            
            # 发送更新开始响应
            response_message = {
                'type': 'update_agent_response',
                'agent_id': self.agent_id,
                'status': 'downloading',
                'version': version,
                'message': '正在下载新版本...'
            }
            await self.websocket.send(json.dumps(response_message))
            
            # 下载新版本
            import requests
            import tempfile
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.new')
            temp_path = temp_file.name
            temp_file.close()
            
            try:
                logger.info(f"下载文件到: {temp_path}")
                response = requests.get(download_url, stream=True, timeout=300)
                response.raise_for_status()
                
                # 写入文件
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                if int(progress) % 20 == 0:  # 每20%发送一次进度
                                    logger.info(f"下载进度: {progress:.1f}%")
                
                logger.info("下载完成")
                
                # 校验MD5
                if md5_expected:
                    logger.info("开始校验MD5...")
                    
                    # 计算下载文件的MD5
                    import hashlib
                    md5_hash = hashlib.md5()
                    with open(temp_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            md5_hash.update(chunk)
                    
                    md5_actual = md5_hash.hexdigest().lower()
                    md5_expected_lower = md5_expected.lower()
                    
                    logger.info(f"文件MD5: {md5_actual}")
                    logger.info(f"期望MD5: {md5_expected_lower}")
                    
                    if md5_actual != md5_expected_lower:
                        error_msg = f'MD5校验失败！期望: {md5_expected_lower}, 实际: {md5_actual}'
                        logger.error(error_msg)
                        raise Exception(error_msg)
                    
                    logger.info("MD5校验通过")
                else:
                    logger.warning("未提供MD5校验值，跳过校验")
                
                # 发送下载完成响应
                response_message = {
                    'type': 'update_agent_response',
                    'agent_id': self.agent_id,
                    'status': 'installing',
                    'version': version,
                    'message': 'MD5校验通过，正在安装...' if md5_expected else '下载完成，正在安装...'
                }
                await self.websocket.send(json.dumps(response_message))
                
                # 获取当前可执行文件路径
                current_exe = sys.executable
                
                # 检查是否为打包的二进制文件
                is_frozen = getattr(sys, 'frozen', False)
                
                if is_frozen:
                    # PyInstaller打包的二进制文件
                    current_exe = sys.executable
                else:
                    # Python脚本，查找二进制文件位置
                    possible_paths = [
                        '/opt/qunkong-agent/qunkong-agent',
                        '/usr/local/bin/qunkong-agent',
                        '/usr/bin/qunkong-agent'
                    ]
                    
                    current_exe = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            current_exe = path
                            break
                    
                    if not current_exe:
                        raise Exception("无法找到当前可执行文件")
                
                logger.info(f"当前可执行文件: {current_exe}")
                
                # 备份当前版本
                backup_path = current_exe + '.backup'
                if os.path.exists(current_exe):
                    import shutil
                    shutil.copy2(current_exe, backup_path)
                    logger.info(f"已备份当前版本到: {backup_path}")
                
                # 替换可执行文件
                import shutil
                shutil.move(temp_path, current_exe)
                os.chmod(current_exe, 0o755)
                
                # 更新版本信息
                version_file = os.path.join(os.path.dirname(current_exe), 'version.txt')
                with open(version_file, 'w') as f:
                    f.write(f"{version}\n")
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                logger.info("安装完成")
                
                # 发送更新成功响应
                response_message = {
                    'type': 'update_agent_response',
                    'agent_id': self.agent_id,
                    'status': 'success',
                    'version': version,
                    'message': f'更新成功，版本: {version}，正在重启...'
                }
                await self.websocket.send(json.dumps(response_message))
                
                # 延迟后重启agent
                await asyncio.sleep(2)
                
                # 检查是否由systemd管理
                is_systemd = os.path.exists('/etc/systemd/system/qunkong-agent.service')
                
                if is_systemd:
                    # 由systemd管理，直接退出让systemd重启
                    logger.info("检测到systemd管理，退出进程让systemd重启...")
                    os._exit(0)
                else:
                    # 手动重启
                    logger.info("手动重启Agent...")
                    restart_cmd = [current_exe]
                    if hasattr(sys, 'argv') and len(sys.argv) > 1:
                        restart_cmd.extend(sys.argv[1:])
                    
                    import subprocess
                    subprocess.Popen(restart_cmd, 
                                   cwd=os.getcwd(),
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                    os._exit(0)
                    
            except Exception as e:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e
                
        except Exception as e:
            logger.error(f"更新Agent失败: {e}")
            # 发送失败响应
            try:
                error_response = {
                    'type': 'update_agent_response',
                    'agent_id': self.agent_id,
                    'status': 'failed',
                    'version': version,
                    'error_message': str(e)
                }
                await self.websocket.send(json.dumps(error_response))
            except:
                pass

    async def handle_terminal_init(self, session_id: str, cols: int = 80, rows: int = 24):
        """初始化PTY终端"""
        try:
            # 创建PTY
            master_fd, slave_fd = pty.openpty()
            
            # 设置终端大小
            self.set_terminal_size(master_fd, cols, rows)
            
            # 启动shell进程
            shell = "/bin/bash"  # 可以改为 /bin/zsh 或其他shell
            env = os.environ.copy()
            env.update({
                'TERM': 'xterm-256color',
                'SHELL': shell,
                'PS1': f'[\\u@{self.hostname} \\W]$ ',
                'HOME': os.path.expanduser('~'),
                'PATH': env.get('PATH', '/usr/local/bin:/usr/bin:/bin'),
            })
            
            # 使用subprocess.Popen而不是asyncio，因为PTY需要同步处理
            process = subprocess.Popen(
                [shell],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env,
                cwd=self.current_directory,
                preexec_fn=os.setsid
            )
            
            # 关闭slave_fd，只保留master_fd
            os.close(slave_fd)
            
            # 设置master_fd为非阻塞
            fcntl.fcntl(master_fd, fcntl.F_SETFL, os.O_NONBLOCK)
            
            # 创建输出队列
            output_queue = queue.Queue()
            
            # 保存会话信息
            self.terminal_sessions[session_id] = {
                'master_fd': master_fd,
                'process': process,
                'thread': None,
                'running': True,
                'cols': cols,
                'rows': rows,
                'output_queue': output_queue
            }
            
            # 启动读取PTY输出的线程
            read_thread = threading.Thread(
                target=self.pty_read_thread,
                args=(session_id, master_fd, output_queue),
                daemon=True
            )
            read_thread.start()
            self.terminal_sessions[session_id]['thread'] = read_thread
            
            # 启动处理输出队列的异步任务
            asyncio.create_task(self.process_pty_output_queue(session_id))
            
            # 发送初始化成功消息
            ready_response = {
                'type': 'terminal_ready',
                'session_id': session_id,
                'cols': cols,
                'rows': rows
            }
            await self.websocket.send(json.dumps(ready_response))
            
            logger.info(f"PTY终端 {session_id} 初始化成功 ({cols}x{rows})")
            
        except Exception as e:
            logger.error(f"PTY终端初始化失败: {e}")
            await self.send_terminal_error(session_id, f"终端初始化失败: {str(e)}")
    
    def set_terminal_size(self, fd, cols, rows):
        """设置终端大小"""
        try:
            size = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, size)
        except Exception as e:
            logger.warning(f"设置终端大小失败: {e}")
    
    def pty_read_thread(self, session_id, master_fd, output_queue):
        """PTY读取线程 - 将PTY输出放入队列"""
        try:
            while session_id in self.terminal_sessions and self.terminal_sessions[session_id]['running']:
                try:
                    # 使用select检查是否有数据可读
                    ready, _, _ = select.select([master_fd], [], [], 0.1)
                    if not ready:
                        continue
                    
                    # 读取数据
                    data = os.read(master_fd, 1024)
                    if not data:
                        break
                    
                    # 转换为字符串
                    output = data.decode('utf-8', errors='replace')
                    # 移除频繁的日志记录，提升性能
                    
                    # 将数据放入队列
                    try:
                        output_queue.put_nowait(output)
                    except queue.Full:
                        logger.warning(f"PTY输出队列已满，丢弃数据: {session_id}")
                    
                except OSError:
                    # PTY已关闭
                    break
                except Exception as e:
                    logger.error(f"PTY读取错误: {e}")
                    break
        
        except Exception as e:
            logger.error(f"PTY读取线程异常: {e}")
        finally:
            # 标记会话结束
            if session_id in self.terminal_sessions:
                try:
                    output_queue.put_nowait(None)  # 结束标记
                except queue.Full:
                    pass
            logger.info(f"PTY读取线程结束: {session_id}")
    
    async def process_pty_output_queue(self, session_id):
        """处理PTY输出队列 - 异步发送到WebSocket"""
        try:
            while session_id in self.terminal_sessions:
                session = self.terminal_sessions[session_id]
                if not session['running']:
                    break
                
                output_queue = session['output_queue']
                
                try:
                    # 从队列中获取数据（非阻塞）
                    try:
                        output = output_queue.get_nowait()
                    except queue.Empty:
                        # 队列为空，稍等一下
                        await asyncio.sleep(0.01)
                        continue
                    
                    # 检查是否为结束标记
                    if output is None:
                        break
                    
                    # 发送数据到WebSocket
                    if self.websocket:
                        response = {
                            'type': 'terminal_data',
                            'session_id': session_id,
                            'data': output
                        }
                        try:
                            await self.websocket.send(json.dumps(response))
                        except Exception as e:
                            logger.error(f"发送PTY数据失败: {e}")
                            break
                    
                    # 标记任务完成
                    output_queue.task_done()
                    
                except Exception as e:
                    logger.error(f"处理PTY输出队列错误: {e}")
                    await asyncio.sleep(0.1)
        
        except Exception as e:
            logger.error(f"PTY输出队列处理异常: {e}")
        finally:
            # 清理会话
            if session_id in self.terminal_sessions:
                self.cleanup_terminal_session(session_id)
            logger.info(f"PTY输出队列处理结束: {session_id}")
    
    async def handle_terminal_input(self, session_id: str, data: str):
        """处理终端输入"""
        if session_id not in self.terminal_sessions:
            logger.warning(f"终端会话不存在: {session_id}")
            return
        
        try:
            session = self.terminal_sessions[session_id]
            master_fd = session['master_fd']
            
            # 初始化命令缓冲区
            if session_id not in self.command_buffers:
                self.command_buffers[session_id] = ""
            
            # 处理特殊字符
            if data == '\r' or data == '\n':  # 回车键 - 命令执行
                command = self.command_buffers[session_id].strip()
                if command:
                    logger.info(f"用户执行命令 [{session_id[:8]}...]: {command}")
                self.command_buffers[session_id] = ""  # 清空缓冲区
            elif data == '\x7f':  # 退格键
                if self.command_buffers[session_id]:
                    self.command_buffers[session_id] = self.command_buffers[session_id][:-1]
            elif data == '\x03':  # Ctrl+C
                logger.info(f"用户中断命令 [{session_id[:8]}...]: Ctrl+C")
                self.command_buffers[session_id] = ""  # 清空缓冲区
            elif data == '\x04':  # Ctrl+D
                logger.info(f"用户发送EOF [{session_id[:8]}...]: Ctrl+D")
            elif data == '\t':  # Tab键 - 不记录日志，减少性能开销
                pass
            elif data.startswith('\x1b['):  # ANSI转义序列（方向键等） - 不记录日志
                pass
            elif len(data) == 1 and ord(data) >= 32 and ord(data) <= 126:  # 单个可打印字符
                self.command_buffers[session_id] += data
                # 移除频繁的日志记录，避免性能问题
            elif len(data) > 1:  # 多字符输入（粘贴、多字节字符等）
                # 处理多字符输入，过滤掉控制字符，只保留可打印字符
                printable_chars = ''.join(char for char in data if ord(char) >= 32 and ord(char) <= 126)
                if printable_chars:
                    self.command_buffers[session_id] += printable_chars
                    # 粘贴操作才记录日志
                    if len(printable_chars) > 5:
                        logger.info(f"用户粘贴文本 [{session_id[:8]}...]: {len(printable_chars)} 字符")
            
            # 将输入写入PTY
            bytes_written = os.write(master_fd, data.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"处理终端输入失败: {e}")
            await self.send_terminal_error(session_id, f"输入处理失败: {str(e)}")
    
    async def handle_terminal_resize(self, session_id: str, cols: int, rows: int):
        """调整终端大小"""
        if session_id not in self.terminal_sessions:
            logger.warning(f"终端会话不存在: {session_id}")
            return
        
        try:
            session = self.terminal_sessions[session_id]
            master_fd = session['master_fd']
            
            # 更新终端大小
            self.set_terminal_size(master_fd, cols, rows)
            session['cols'] = cols
            session['rows'] = rows
            
            logger.info(f"终端 {session_id} 大小调整为 {cols}x{rows}")
            
        except Exception as e:
            logger.error(f"调整终端大小失败: {e}")
    
    async def handle_terminal_close(self, session_id: str):
        """关闭PTY终端"""
        try:
            if session_id in self.terminal_sessions:
                self.cleanup_terminal_session(session_id)
                logger.info(f"PTY终端 {session_id} 已关闭")
            
        except Exception as e:
            logger.error(f"关闭PTY终端失败: {e}")
    
    def cleanup_terminal_session(self, session_id: str):
        """清理终端会话"""
        try:
            if session_id not in self.terminal_sessions:
                return
            
            session = self.terminal_sessions[session_id]
            session['running'] = False
            
            # 关闭PTY
            if 'master_fd' in session:
                try:
                    os.close(session['master_fd'])
                except:
                    pass
            
            # 终止进程
            if 'process' in session and session['process']:
                try:
                    session['process'].terminate()
                    session['process'].wait(timeout=2)
                except:
                    try:
                        session['process'].kill()
                    except:
                        pass
            
            # 等待线程结束
            if 'thread' in session and session['thread']:
                try:
                    session['thread'].join(timeout=1)
                except:
                    pass
            
            # 删除会话
            del self.terminal_sessions[session_id]
            
            # 清理命令缓冲区
            if session_id in self.command_buffers:
                del self.command_buffers[session_id]
                logger.debug(f"命令缓冲区已清理: {session_id}")
            
        except Exception as e:
            logger.error(f"清理终端会话失败: {e}")
    
    async def send_terminal_error(self, session_id: str, error_msg: str):
        """发送终端错误消息"""
        try:
            response = {
                'type': 'terminal_error',
                'session_id': session_id,
                'error': error_msg
            }
            await self.websocket.send(json.dumps(response))
        except Exception as e:
            logger.error(f"发送终端错误消息失败: {e}")

    async def run(self):
        """运行Agent"""
        self.running = True
        logger.info("Agent 初始化: {} ({})".format(self.hostname, self.ip))
        logger.info("Qunkong Agent 启动: {}".format(self.hostname))
        
        # 重连参数
        max_retries = 10
        retry_delay = 5  # 初始重连延迟
        max_retry_delay = 60  # 最大重连延迟
        
        retry_count = 0
        
        while self.running and retry_count < max_retries:
            try:
                logger.info("连接到服务器: ws://{}:{}".format(self.server_host, self.server_port))
                
                # 设置WebSocket连接参数
                connect_kwargs = {
                    'ping_interval': 20,  # 每20秒发送ping
                    'ping_timeout': 10,   # ping超时时间
                    'close_timeout': 10,  # 关闭超时时间
                    'max_size': 2**20,    # 最大消息大小1MB
                    'max_queue': 32       # 最大队列大小
                }
                
                async with websockets.connect(
                    "ws://{}:{}".format(self.server_host, self.server_port),
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
                            logger.info("心跳任务启动")
                            consecutive_failures = 0
                            # 等待一段时间再开始发送心跳，确保连接稳定
                            await asyncio.sleep(1)
                            logger.info("开始发送心跳")
                            
                            try:
                                logger.info("检查心跳条件...")
                                logger.info("self.running = {}".format(self.running))
                                
                                # 检查websocket状态 - 使用正确的方法
                                try:
                                    is_closed = hasattr(websocket, 'closed') and websocket.closed
                                except:
                                    is_closed = False
                                logger.info("websocket is_closed = {}".format(is_closed))
                                
                                if not self.running:
                                    logger.error("心跳任务退出: self.running=False")
                                    return
                                if is_closed:
                                    logger.error("心跳任务退出: websocket已关闭")
                                    return
                                
                                logger.info("准备开始心跳循环")
                                logger.info("心跳循环进行中...")
                                heartbeat_count = 0
                                # 使用更简单的条件检查
                                while self.running:
                                    heartbeat_count += 1
                                    # logger.info("=== 心跳循环 #{} 开始 ===".format(heartbeat_count))
                                    # 检查连接状态
                                    try:
                                        if hasattr(websocket, 'closed') and websocket.closed:
                                            logger.warning("检测到websocket连接已关闭，退出心跳循环")
                                            break
                                    except:
                                        pass
                                    
                                    try:
                                        await self.send_heartbeat(websocket)
                                        consecutive_failures = 0  # 重置失败计数
                                        await asyncio.sleep(5)  # 每5秒发送一次心跳（降低频率）
                                    except websockets.exceptions.ConnectionClosed:
                                        logger.warning("心跳发送失败: 连接已关闭")
                                        break
                                    except Exception as e:
                                        consecutive_failures += 1
                                        logger.error("心跳发送失败: {} (类型: {})".format(e, type(e).__name__))
                                        import traceback
                                        logger.debug("心跳发送异常详情: {}".format(traceback.format_exc()))
                                        # 只有连续失败多次才退出
                                        if consecutive_failures >= 5:
                                            logger.error("心跳连续失败5次，退出心跳任务")
                                            break
                                        # 根据失败次数调整等待时间
                                        if consecutive_failures >= 3:
                                            logger.warning("连续心跳失败{}次，等待10秒后重试".format(consecutive_failures))
                                            await asyncio.sleep(10)
                                        else:
                                            await asyncio.sleep(5)  # 失败后等待重试
                                logger.info("心跳循环结束")
                            except Exception as debug_e:
                                logger.error("心跳调试过程出错: {}".format(debug_e))
                                import traceback
                                logger.error("调试异常详情: {}".format(traceback.format_exc()))
                            logger.info("心跳任务结束")
                        
                        heartbeat_task_handle = asyncio.create_task(heartbeat_task())
                        logger.info("心跳任务已创建")
                        
                        # 处理服务器消息
                        try:
                            async for message in websocket:
                                # 记录收到的消息
                                logger.info("★★★ 收到服务器消息: {}".format(message[:200] if len(message) > 200 else message))
                                
                                # 检查心跳任务是否异常结束
                                if heartbeat_task_handle.done():
                                    try:
                                        await heartbeat_task_handle
                                    except Exception as e:
                                        logger.error("心跳任务异常结束: {} (类型: {})".format(e, type(e).__name__))
                                        import traceback
                                        logger.debug("心跳任务异常详情: {}".format(traceback.format_exc()))
                                        # 重新启动心跳任务
                                        logger.info("重新启动心跳任务")
                                        heartbeat_task_handle = asyncio.create_task(heartbeat_task())
                                
                                await self.handle_server_message(message)
                        except Exception as e:
                            logger.error("消息处理循环异常: {} (类型: {})".format(e, type(e).__name__))
                            import traceback
                            logger.debug("消息处理循环异常详情: {}".format(traceback.format_exc()))
                            
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("WebSocket连接已关闭")
                    except Exception as e:
                        logger.error("处理消息时出错: {}".format(e))
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
                logger.error("无效的WebSocket URI: ws://{}:{}".format(self.server_host, self.server_port))
                break
            except OSError as e:
                logger.error("网络连接错误: {}".format(e))
            except Exception as e:
                logger.error("Agent 运行错误: {}".format(e))
            
            # 如果还在运行状态，准备重连
            if self.running and retry_count < max_retries:
                retry_count += 1
                # 使用指数退避策略，但有最大延迟限制
                current_delay = min(retry_delay * (2 ** (retry_count - 1)), max_retry_delay)
                # 为网络不稳定的情况增加额外延迟
                if retry_count > 3:
                    current_delay += 5  # 多次重连失败后增加5秒延迟
                logger.info("将在 {} 秒后尝试重连 (第 {}/{} 次)".format(current_delay, retry_count, max_retries))
                await asyncio.sleep(current_delay)
            elif retry_count >= max_retries:
                logger.error("达到最大重连次数，Agent停止运行")
                break
        
        self.running = False
        logger.info("Agent 已停止")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Qunkong Agent 客户端')
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
    
    logger.info("启动参数: 服务器={}:{}".format(args.server, args.port))
    
    agent = QunkongAgent(
        server_host=args.server,
        server_port=args.port,
        agent_id=args.agent_id,
        log_level="DEBUG" if args.verbose else "INFO"
    )
    
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("Agent 已停止")
    except Exception as e:
        logger.error("Agent 启动失败: {}".format(e))

if __name__ == '__main__':
    main()
