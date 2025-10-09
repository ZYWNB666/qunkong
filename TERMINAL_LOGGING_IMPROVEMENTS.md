# 终端日志优化说明

## 问题描述

之前的终端日志显示原始字符，包括退格键(`\x7f`)和回车键(`\r`)，不够直观：

```
INFO:__main__:收到终端输入 jQOKwxdOtNW2eZi_FoDzh_UKLKHutfxyccojiXkzqZA: '\x7f'
INFO:__main__:写入PTY字节数: 1
INFO:__main__:收到终端输入 jQOKwxdOtNW2eZi_FoDzh_UKLKHutfxyccojiXkzqZA: 'l'
INFO:__main__:写入PTY字节数: 1
INFO:__main__:收到终端输入 jQOKwxdOtNW2eZi_FoDzh_UKLKHutfxyccojiXkzqZA: 's'
INFO:__main__:写入PTY字节数: 1
INFO:__main__:收到终端输入 jQOKwxdOtNW2eZi_FoDzh_UKLKHutfxyccojiXkzqZA: '\r'
```

## 优化方案

### 1. 命令缓冲机制

- 添加 `command_buffers` 字典来跟踪每个终端会话的当前输入
- 实时构建用户正在输入的完整命令

### 2. 智能字符处理

- **回车键** (`\r`, `\n`): 显示完整执行的命令
- **退格键** (`\x7f`): 从缓冲区删除字符，显示当前输入状态
- **Ctrl+C** (`\x03`): 显示中断操作，清空缓冲区
- **Ctrl+D** (`\x04`): 显示EOF操作
- **Tab键** (`\t`): 显示自动补全操作
- **方向键**: 识别并显示方向键操作
- **可打印字符**: 添加到命令缓冲区

### 3. 日志级别控制

- 添加 `log_level` 参数控制日志详细程度
- 支持 `DEBUG`, `INFO`, `WARNING` 三个级别
- 命令行参数 `--verbose` 启用详细日志

## 优化后的日志效果

### 正常命令执行
```
INFO:__main__:用户执行命令 [jQOKwxdO...]: ls -la
INFO:__main__:用户执行命令 [jQOKwxdO...]: cd /home/user
INFO:__main__:用户执行命令 [jQOKwxdO...]: cat file.txt
```

### 退格和编辑操作（DEBUG级别）
```
DEBUG:__main__:用户退格 [jQOKwxdO...], 当前输入: 'l'
DEBUG:__main__:用户退格 [jQOKwxdO...], 当前输入: ''
DEBUG:__main__:用户输入中 [jQOKwxdO...]: 'ls -la'
```

### 特殊操作
```
INFO:__main__:用户中断命令 [jQOKwxdO...]: Ctrl+C
INFO:__main__:用户发送EOF [jQOKwxdO...]: Ctrl+D
DEBUG:__main__:用户按下Tab键 [jQOKwxdO...], 当前输入: 'ls'
DEBUG:__main__:用户按上方向键 [jQOKwxdO...]
```

## 使用方法

### 启动Agent（普通模式）
```bash
python app/client.py --server your-server --port 8765
```

### 启动Agent（详细日志模式）
```bash
python app/client.py --server your-server --port 8765 --verbose
```

## 技术实现

### 核心改进

1. **命令缓冲区管理**
   ```python
   self.command_buffers = {}  # session_id -> current_command_buffer
   ```

2. **智能字符识别**
   ```python
   if data == '\r' or data == '\n':  # 回车键 - 命令执行
       command = self.command_buffers[session_id].strip()
       if command:
           logger.info(f"用户执行命令 [{session_id[:8]}...]: {command}")
   elif data == '\x7f':  # 退格键
       if self.command_buffers[session_id]:
           self.command_buffers[session_id] = self.command_buffers[session_id][:-1]
   ```

3. **会话清理**
   ```python
   # 清理命令缓冲区
   if session_id in self.command_buffers:
       del self.command_buffers[session_id]
   ```

## 优势

1. **可读性**: 直接显示用户执行的完整命令
2. **调试友好**: DEBUG模式下显示详细的输入过程
3. **性能优化**: 减少无意义的日志输出
4. **会话隔离**: 每个终端会话独立的命令缓冲区
5. **资源管理**: 会话结束时自动清理缓冲区

## 配置选项

- `log_level`: 控制日志详细程度 (`DEBUG`, `INFO`, `WARNING`)
- `--verbose`: 命令行参数启用详细日志
- Session ID截断: 只显示前8位，避免日志过长

这些改进让终端操作日志更加人性化和易读，同时保持了系统的性能和稳定性。
