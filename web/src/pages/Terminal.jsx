import React, { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Terminal as XTerm } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import * as Zmodem from 'zmodem.js/src/zmodem_browser'
import '@xterm/xterm/css/xterm.css'
import { Layout, List, Card, Tag, Button, Space, message, Tabs, Modal, Progress, Dropdown } from 'antd'
import { DesktopOutlined, ReloadOutlined, UploadOutlined, CopyOutlined, CloseOutlined, SyncOutlined } from '@ant-design/icons'
import { agentApi } from '../utils/api'

const { Sider, Content } = Layout

const Terminal = () => {
  const { agentId } = useParams()
  const navigate = useNavigate()
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState(agentId || '')
  const [tabs, setTabs] = useState([])
  const terminalsRef = useRef({})

  useEffect(() => {
    loadAgents()
  }, [])

  useEffect(() => {
    if (agentId && agents.length > 0 && tabs.length === 0) {
      const agent = agents.find(a => a.id === agentId)
      if (agent) {
        handleAddTab(agent)
      }
    }
  }, [agentId, agents.length, tabs.length])

  const loadAgents = async () => {
    try {
      setLoading(true)
      const response = await agentApi.getAgents()
      // 显示所有 agent，不再过滤在线状态
      setAgents(response.agents || [])
    } catch (error) {
      message.error('加载 Agent 列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAddTab = (agent, forceNew = false) => {
    // 如果不是强制新建，检查是否已存在
    if (!forceNew && tabs.find(tab => tab.key === agent.id)) {
      setActiveTab(agent.id)
      return
    }

    // 生成唯一的key，如果是复制的话，添加时间戳
    const tabKey = forceNew ? `${agent.id}_${Date.now()}` : agent.id

    const newTab = {
      key: tabKey,
      label: agent.hostname,
      agent: agent,
      agentId: agent.id // 保存原始agent id
    }

    setTabs(prev => [...prev, newTab])
    setActiveTab(tabKey)
  }

  const handleRemoveTab = (targetKey) => {
    const terminal = terminalsRef.current[targetKey]
    if (terminal) {
      if (terminal.ws) terminal.ws.close()
      if (terminal.term) terminal.term.dispose()
      delete terminalsRef.current[targetKey]
    }

    const newTabs = tabs.filter(tab => tab.key !== targetKey)
    setTabs(newTabs)

    if (newTabs.length === 0) {
      setActiveTab('')
      // 不跳转，保持在当前页面
    } else if (targetKey === activeTab) {
      const index = tabs.findIndex(tab => tab.key === targetKey)
      const nextTab = newTabs[index] || newTabs[index - 1]
      setActiveTab(nextTab.key)
    }
  }

  // 复制终端
  const handleCopyTab = (targetKey) => {
    const tab = tabs.find(t => t.key === targetKey)
    if (tab) {
      handleAddTab(tab.agent, true)
      message.success('已复制终端')
    }
  }

  // 刷新终端
  const handleRefreshTab = (targetKey) => {
    const terminal = terminalsRef.current[targetKey]
    if (terminal) {
      // 关闭旧连接
      if (terminal.ws) terminal.ws.close()
      if (terminal.term) terminal.term.dispose()
      delete terminalsRef.current[targetKey]
    }

    const tab = tabs.find(t => t.key === targetKey)
    if (tab) {
      // 触发重新渲染
      setTabs(prev => prev.map(t => 
        t.key === targetKey ? { ...t, refreshKey: Date.now() } : t
      ))
      message.success('终端已刷新')
    }
  }

  // 获取标签页右键菜单
  const getTabContextMenu = (targetKey) => ({
    items: [
      {
        key: 'copy',
        icon: <CopyOutlined />,
        label: '复制终端',
        onClick: () => handleCopyTab(targetKey)
      },
      {
        key: 'refresh',
        icon: <SyncOutlined />,
        label: '刷新终端',
        onClick: () => handleRefreshTab(targetKey)
      },
      {
        type: 'divider'
      },
      {
        key: 'close',
        icon: <CloseOutlined />,
        label: '关闭终端',
        danger: true,
        onClick: () => handleRemoveTab(targetKey)
      }
    ]
  })

  useEffect(() => {
    if (activeTab && terminalsRef.current[activeTab]) {
      setTimeout(() => {
        const terminal = terminalsRef.current[activeTab]
        if (terminal && terminal.fitAddon) {
          terminal.fitAddon.fit()
        }
      }, 100)
    }
  }, [activeTab])

  useEffect(() => {
    return () => {
      Object.keys(terminalsRef.current).forEach(agentId => {
        const terminal = terminalsRef.current[agentId]
        if (terminal) {
          if (terminal.ws) terminal.ws.close()
          if (terminal.term) terminal.term.dispose()
          delete terminalsRef.current[agentId]
        }
      })
    }
  }, [])

  return (
    <Layout style={{ height: '100vh', overflow: 'hidden' }}>
      <Sider width={250} style={{ background: '#fff', borderRight: '1px solid #e8e8e8', overflow: 'auto' }}>
        <div style={{ padding: '16px', borderBottom: '1px solid #e8e8e8', position: 'sticky', top: 0, background: '#fff', zIndex: 1 }}>
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <h3 style={{ margin: 0 }}>Agent 列表</h3>
            <Button icon={<ReloadOutlined />} size="small" onClick={loadAgents} />
          </Space>
          <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
            💡 点击添加终端标签
          </div>
          <div style={{ marginTop: 4, fontSize: 12, color: '#52c41a' }}>
            🚀 支持 sz/rz 文件传输
          </div>
        </div>
        <List
          loading={loading}
          dataSource={agents}
          renderItem={agent => {
            const isActive = tabs.find(tab => tab.key === agent.id)
            const isOnline = agent.status === 'ONLINE'
            return (
              <List.Item
                style={{
                  padding: '8px 16px',
                  cursor: 'pointer',
                  background: isActive ? '#e6f7ff' : 'transparent',
                  borderLeft: isActive ? '3px solid #1890ff' : '3px solid transparent'
                }}
                onClick={() => handleAddTab(agent)}
              >
                <div style={{ width: '100%' }}>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '14px'
                  }}>
                    <DesktopOutlined style={{ fontSize: 16 }} />
                    <span style={{ 
                      color: isOnline ? '#52c41a' : '#ff4d4f',
                      fontWeight: 500
                    }}>
                      ({agent.hostname}) {agent.ip_address}
                    </span>
                  </div>
                </div>
              </List.Item>
            )
          }}
        />
      </Sider>
      <Layout>
        <Content style={{ height: '100vh', overflow: 'hidden', background: '#1e1e1e' }}>
          {tabs.length > 0 ? (
            <Tabs
              type="editable-card"
              activeKey={activeTab}
              onChange={setActiveTab}
              onEdit={(targetKey, action) => {
                if (action === 'remove') handleRemoveTab(targetKey)
              }}
              hideAdd
              style={{ height: '100%' }}
              tabBarStyle={{ 
                margin: 0, 
                background: '#1e1e1e',
                borderBottom: '1px solid #333',
                paddingLeft: 8
              }}
              items={tabs.map(tab => ({
                key: tab.key,
                label: (
                  <Dropdown
                    menu={getTabContextMenu(tab.key)}
                    trigger={['contextMenu']}
                  >
                  <span style={{ color: '#d4d4d4' }}>
                    <DesktopOutlined style={{ marginRight: 6 }} />
                    {tab.label}
                  </span>
                  </Dropdown>
                ),
                children: (
                  <TerminalPane 
                    key={`${tab.key}_${tab.refreshKey || 0}`}
                    agentId={tab.agentId || tab.key}
                    agent={tab.agent}
                    isActive={activeTab === tab.key}
                    terminalsRef={terminalsRef}
                  />
                )
              }))}
            />
          ) : (
            <div style={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#999'
            }}>
              <Card>
                <Space direction="vertical" align="center">
                  <DesktopOutlined style={{ fontSize: 48, color: '#999' }} />
                  <p>请从左侧选择一个 Agent 连接终端</p>
                  <p style={{ fontSize: 12, color: '#999' }}>支持同时打开多个终端，通过标签页切换</p>
                  <p style={{ fontSize: 12, color: '#52c41a' }}>✨ 支持 sz/rz 文件传输功能</p>
                </Space>
              </Card>
            </div>
          )}
        </Content>
      </Layout>
    </Layout>
  )
}

const TerminalPane = ({ agentId, terminalsRef }) => {
  const containerRef = useRef(null)
  const [transferProgress, setTransferProgress] = useState({ visible: false, percent: 0, name: '', type: '' })
  const [uploadModalVisible, setUploadModalVisible] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const zmodemSessionRef = useRef(null)
  const initializedRef = useRef(false)
  const fileInputRef = useRef(null)
  const pendingUploadSessionRef = useRef(null)

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  // 文件选择处理
  const handleFilesSelected = (files) => {
    setSelectedFiles(Array.from(files))
  }

  // 开始上传
  const handleStartUpload = async () => {
    if (selectedFiles.length === 0) {
      message.warning('请先选择文件')
      return
    }

    const session = pendingUploadSessionRef.current
    if (!session) {
      message.error('上传会话已失效')
      setUploadModalVisible(false)
      return
    }

    setUploadModalVisible(false)
    const term = terminalsRef.current[agentId]?.term

    try {
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i]
        try {
          term.writeln(`\x1b[36m发送文件: ${file.name} (${formatFileSize(file.size)})\x1b[0m`)
          
          setTransferProgress({
            visible: true,
            percent: 0,
            name: file.name,
            type: 'upload'
          })

          const arrayBuffer = await file.arrayBuffer()
          const fileData = new Uint8Array(arrayBuffer)
          
          // 创建offer对象
          const offerPayload = {
            name: file.name,
            size: file.size,
            mode: 0o100644,
            mtime: new Date(file.lastModified),
            files_remaining: selectedFiles.length - i,
            bytes_remaining: fileData.length
          }

          // 发送offer
          const transfer = await session.send_offer(offerPayload)
          
          if (transfer) {
            let offset = 0
            const chunkSize = 8192
            
            while (offset < fileData.length) {
              const chunk = fileData.slice(offset, Math.min(offset + chunkSize, fileData.length))
              await transfer.send(chunk)
              offset += chunk.length
              
              const percent = Math.round((offset / fileData.length) * 100)
              setTransferProgress(prev => ({ ...prev, percent }))
            }
            
            await transfer.end()
            term.writeln(`\x1b[32m✓ 文件已发送: ${file.name}\x1b[0m`)
          } else {
            term.writeln(`\x1b[31m✗ 文件被拒绝: ${file.name}\x1b[0m`)
          }
          
        } catch (error) {
          console.error('上传错误:', error)
          term.writeln(`\x1b[31m发送失败: ${file.name} - ${error.message}\x1b[0m`)
        }
      }

      try {
        await session.close()
      } catch (e) {
        console.warn('关闭会话失败:', e)
      }
      term.writeln('\x1b[32m传输完成!\x1b[0m\r\n')
      
    } catch (error) {
      console.error('传输过程错误:', error)
      term.writeln(`\x1b[31m传输失败: ${error.message}\x1b[0m\r\n`)
    } finally {
      setTransferProgress({ visible: false, percent: 0, name: '', type: '' })
      zmodemSessionRef.current = null
      pendingUploadSessionRef.current = null
      setSelectedFiles([])
    }
  }

  useEffect(() => {
    if (!containerRef.current || initializedRef.current) return
    
    initializedRef.current = true

    const term = new XTerm({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Consolas, "Courier New", monospace',
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4'
      },
      scrollback: 1000,
      scrollOnInput: true,
      convertEol: true
    })

    const fitAddon = new FitAddon()
    const webLinksAddon = new WebLinksAddon()
    
    term.loadAddon(fitAddon)
    term.loadAddon(webLinksAddon)
    term.open(containerRef.current)
    
    setTimeout(() => fitAddon.fit(), 100)

    const wsUrl = `ws://${__WEBSOCKET_HOST__}:${__WEBSOCKET_PORT__}/terminal/${agentId}`
    const ws = new WebSocket(wsUrl)
    ws.binaryType = 'arraybuffer'

    // 先初始化 terminalsRef
    terminalsRef.current[agentId] = {
      term,
      ws,
      fitAddon,
      containerRef,
      connected: false
    }

    // ZMODEM 检测缓冲区
    let zmodemDetector = new Zmodem.Sentry({
      to_terminal: (octets) => {
        // 只在非ZMODEM会话期间输出到终端
        if (!zmodemSessionRef.current) {
          term.write(new Uint8Array(octets))
        }
      },
      sender: (octets) => {
        // 发送ZMODEM数据到服务器
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(new Uint8Array(octets))
        } else {
          console.error('WebSocket未连接，无法发送ZMODEM数据')
        }
      },
      on_detect: (detection) => {
        handleZmodemSession(detection)
      },
      on_retract: () => {
        // ZMODEM 会话结束，清理状态
        zmodemSessionRef.current = null
      }
    })

    const handleZmodemSession = async (detection) => {
      term.writeln('\r\n\x1b[32m检测到 ZMODEM 传输...\x1b[0m')
      
      const session = detection.confirm()
      zmodemSessionRef.current = session

      // ZMODEM会话类型是从前端（本地）角度定义的：
      // - receive: 前端接收文件（对应服务器的sz命令，下载）
      // - send: 前端发送文件（对应服务器的rz命令，上传）
      if (session.type === 'receive') {
        // sz 命令 - 从服务器下载文件到本地
        term.writeln('\x1b[36m开始下载文件...\x1b[0m')
        await handleFileDownload(session, term)
      } else if (session.type === 'send') {
        // rz 命令 - 从本地上传文件到服务器
        term.writeln('\x1b[36m开始上传文件...\x1b[0m')
        await handleFileUpload(session, term)
      } else {
        term.writeln(`\x1b[31m未知的会话类型: ${session.type}\x1b[0m`)
      }
    }

    const handleFileDownload = async (session, term) => {
      try {
        term.writeln('\x1b[33m准备接收文件...\x1b[0m')
        
        // 使用Promise处理offer事件
        const processOffers = () => {
          return new Promise((resolve, reject) => {
            let fileCount = 0
            let sessionEnded = false
            
            // 设置超时：如果10秒内没有收到session_end，自动结束
            const timeout = setTimeout(() => {
              if (!sessionEnded) {
                term.writeln(`\x1b[33m传输超时，已接收 ${fileCount} 个文件\x1b[0m\r\n`)
                resolve()
              }
            }, 10000)
            
            session.on('offer', async (xfer) => {
              try {
                fileCount++
                const fileName = xfer.get_details().name
                const fileSize = xfer.get_details().size
                
                term.writeln(`\x1b[36m接收文件: ${fileName} (${formatFileSize(fileSize)})\x1b[0m`)
                
                setTransferProgress({
                  visible: true,
                  percent: 0,
                  name: fileName,
                  type: 'download'
                })

                const chunks = []
                
                xfer.on('input', (chunk) => {
                  chunks.push(new Uint8Array(chunk))
                  const received = chunks.reduce((sum, c) => sum + c.length, 0)
                  const percent = Math.round((received / fileSize) * 100)
                  setTransferProgress(prev => ({ ...prev, percent }))
                })

                await xfer.accept()
                
                // 合并所有块
                const totalLength = chunks.reduce((sum, c) => sum + c.length, 0)
                const fileData = new Uint8Array(totalLength)
                let offset = 0
                chunks.forEach(chunk => {
                  fileData.set(chunk, offset)
                  offset += chunk.length
                })
                
                // 下载文件
                const blob = new Blob([fileData])
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = fileName
                document.body.appendChild(a)
                a.click()
                document.body.removeChild(a)
                URL.revokeObjectURL(url)

                term.writeln(`\x1b[32m✓ 文件已保存: ${fileName}\x1b[0m`)
                
                // 单文件传输完成后，等待1秒看是否有session_end，否则自动结束
                setTimeout(() => {
                  if (!sessionEnded && fileCount === 1) {
                    sessionEnded = true
                    clearTimeout(timeout)
                    term.writeln(`\x1b[32m传输完成!\x1b[0m\r\n`)
                    resolve()
                  }
                }, 1000)
              } catch (error) {
                term.writeln(`\x1b[31m接收失败: ${error.message}\x1b[0m`)
                clearTimeout(timeout)
                reject(error)
              }
            })
            
            session.on('session_end', () => {
              if (!sessionEnded) {
                sessionEnded = true
                clearTimeout(timeout)
                term.writeln(`\x1b[32m传输完成! 共接收 ${fileCount} 个文件\x1b[0m\r\n`)
                resolve()
              }
            })
            
            // 开始接收
            session.start()
          })
        }
        
        await processOffers()
        
      } catch (error) {
        term.writeln(`\x1b[31m传输失败: ${error.message}\x1b[0m\r\n`)
      } finally {
        setTransferProgress({ visible: false, percent: 0, name: '', type: '' })
        zmodemSessionRef.current = null
      }
    }

    const handleFileUpload = async (session, term) => {
      try {
        term.writeln('\x1b[33m准备发送文件...\x1b[0m')
        term.writeln('\x1b[36m请选择或拖入要上传的文件\x1b[0m')

        // 保存session供后续使用
        pendingUploadSessionRef.current = session
        
        // 显示上传modal
        setUploadModalVisible(true)
        setSelectedFiles([])
        
      } catch (error) {
        term.writeln(`\x1b[31m传输失败: ${error.message}\x1b[0m\r\n`)
        setTransferProgress({ visible: false, percent: 0, name: '', type: '' })
        zmodemSessionRef.current = null
      }
    }

    ws.onopen = () => {
      terminalsRef.current[agentId].connected = true
      term.writeln('\x1b[32mConnected to agent...\x1b[0m')
      term.writeln('\x1b[36m提示: 使用 sz 命令下载文件, 使用 rz 命令上传文件\x1b[0m')
      term.scrollToBottom()
      
      setTimeout(() => {
        if (ws.readyState === WebSocket.OPEN) {
          const resizeMsg = {
            type: 'terminal_resize',
            cols: term.cols,
            rows: term.rows
          }
          ws.send(JSON.stringify(resizeMsg))
        }
      }, 100)
    }

    ws.onmessage = (event) => {
      try {
        if (event.data instanceof ArrayBuffer) {
          // 二进制数据 - 通过 ZMODEM 检测器处理
          const buffer = new Uint8Array(event.data)
          try {
            zmodemDetector.consume(buffer)
          } catch (e) {
            // ZMODEM处理错误，如果会话已结束，直接输出到终端
            if (!zmodemSessionRef.current) {
              console.warn('ZMODEM会话已结束，忽略协议错误:', e.message)
              term.write(buffer)
            } else {
              throw e
            }
          }
        } else {
          // 文本数据 - JSON 消息
          const msg = JSON.parse(event.data)
          if (msg.type === 'terminal_data' && msg.data) {
            // 检查是否是二进制数据（base64编码）
            if (msg.is_binary) {
              const binaryString = atob(msg.data)
              const bytes = new Uint8Array(binaryString.length)
              for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i)
              }
              try {
                zmodemDetector.consume(bytes)
              } catch (e) {
                // ZMODEM处理错误，如果会话已结束，直接输出到终端
                if (!zmodemSessionRef.current) {
                  console.warn('ZMODEM会话已结束，忽略协议错误，直接输出')
                  term.write(bytes)
                } else {
                  throw e
                }
              }
            } else {
              // 普通文本数据，直接转换为字节数组
              const encoder = new TextEncoder()
              const bytes = encoder.encode(msg.data)
              try {
                zmodemDetector.consume(bytes)
              } catch (e) {
                // ZMODEM处理错误，如果会话已结束，直接输出到终端
                if (!zmodemSessionRef.current) {
                  console.warn('ZMODEM会话已结束，忽略协议错误，直接输出')
                  term.write(bytes)
                } else {
                  throw e
                }
              }
            }
          } else if (msg.type === 'terminal_ready') {
            term.writeln('\x1b[32m\r\nTerminal ready!\x1b[0m')
            term.scrollToBottom()
          } else if (msg.type === 'error') {
            term.writeln(`\r\n\x1b[31mError: ${msg.message}\x1b[0m`)
            term.scrollToBottom()
          }
        }
      } catch (e) {
        console.error('处理消息失败:', e)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      if (terminalsRef.current[agentId]) {
        terminalsRef.current[agentId].connected = false
      }
      term.writeln('\r\n\x1b[31mConnection error!\x1b[0m')
      term.scrollToBottom()
    }

    ws.onclose = () => {
      if (terminalsRef.current[agentId]) {
        terminalsRef.current[agentId].connected = false
      }
      term.writeln('\r\n\x1b[33mConnection closed!\x1b[0m')
      term.scrollToBottom()
    }

    term.onData((data) => {
      if (zmodemSessionRef.current) {
        // ZMODEM 会话活动时，不发送普通输入
        return
      }
      
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data)
      }
    })

    // 窗口大小调整
    const handleResize = () => {
      if (fitAddon && term && ws && ws.readyState === WebSocket.OPEN) {
        fitAddon.fit()
        const resizeMsg = {
          type: 'terminal_resize',
          cols: term.cols,
          rows: term.rows
        }
        ws.send(JSON.stringify(resizeMsg))
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      initializedRef.current = false
      window.removeEventListener('resize', handleResize)
      if (ws) ws.close()
      if (term) term.dispose()
      if (terminalsRef.current[agentId]) {
        delete terminalsRef.current[agentId]
      }
    }
  }, [agentId])

  return (
    <>
      <div 
        ref={containerRef}
        style={{ 
          height: 'calc(100vh - 70px)',
          width: '100%',
          padding: 10,
          background: '#1e1e1e',
          overflow: 'hidden'
        }} 
      />
      
      {/* 传输进度Modal */}
      <Modal
        title={
          <Space>
            {transferProgress.type === 'download' ? '📥 下载文件' : '📤 上传文件'}
          </Space>
        }
        open={transferProgress.visible}
        footer={null}
        closable={false}
        centered
      >
        <div style={{ padding: '20px 0' }}>
          <div style={{ marginBottom: 10, fontSize: 14 }}>
            <strong>{transferProgress.name}</strong>
          </div>
          <Progress 
            percent={transferProgress.percent} 
            status="active"
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />
          <div style={{ marginTop: 10, textAlign: 'center', color: '#999' }}>
            {transferProgress.type === 'download' ? '正在下载...' : '正在上传...'}
          </div>
        </div>
      </Modal>

      {/* 文件上传选择Modal */}
      <Modal
        title={
          <Space>
            <UploadOutlined />
            <span>选择上传文件</span>
          </Space>
        }
        open={uploadModalVisible}
        onOk={handleStartUpload}
        onCancel={() => {
          setUploadModalVisible(false)
          setSelectedFiles([])
          if (pendingUploadSessionRef.current) {
            pendingUploadSessionRef.current.close()
            pendingUploadSessionRef.current = null
          }
          zmodemSessionRef.current = null
          const term = terminalsRef.current[agentId]?.term
          if (term) {
            term.writeln('\x1b[33m\r\n上传已取消\x1b[0m\r\n')
          }
        }}
        okText="开始上传"
        cancelText="取消"
        width={600}
        centered
      >
        <div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: 'none' }}
            onChange={(e) => handleFilesSelected(e.target.files)}
          />
          
          <div
            style={{
              border: `2px dashed ${isDragging ? '#1890ff' : '#d9d9d9'}`,
              borderRadius: 8,
              padding: 40,
              textAlign: 'center',
              background: isDragging ? '#e6f7ff' : '#fafafa',
              cursor: 'pointer',
              transition: 'all 0.3s'
            }}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault()
              setIsDragging(true)
            }}
            onDragLeave={(e) => {
              e.preventDefault()
              setIsDragging(false)
            }}
            onDrop={(e) => {
              e.preventDefault()
              setIsDragging(false)
              handleFilesSelected(e.dataTransfer.files)
            }}
          >
            <UploadOutlined style={{ fontSize: 48, color: isDragging ? '#1890ff' : '#999', marginBottom: 16 }} />
            <div style={{ fontSize: 16, marginBottom: 8 }}>
              {isDragging ? '松开鼠标上传文件' : '点击或拖拽文件到此处'}
            </div>
            <div style={{ fontSize: 12, color: '#999' }}>
              支持单个或批量上传
            </div>
          </div>

          {selectedFiles.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontWeight: 'bold', marginBottom: 8 }}>
                已选择 {selectedFiles.length} 个文件：
              </div>
              <div style={{ maxHeight: 200, overflow: 'auto', border: '1px solid #e8e8e8', borderRadius: 4, padding: 8 }}>
                {selectedFiles.map((file, index) => (
                  <div key={index} style={{ 
                    padding: '8px 12px', 
                    marginBottom: 4, 
                    background: '#f5f5f5', 
                    borderRadius: 4,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      📄 {file.name}
                    </span>
                    <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>
                      {formatFileSize(file.size)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </Modal>
    </>
  )
}

export default Terminal
