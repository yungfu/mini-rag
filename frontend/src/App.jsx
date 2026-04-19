import React, { useState, useEffect, useRef } from 'react'
import { MessageSquare, Upload, FileText, Send, Loader2 } from 'lucide-react'
import ChatMessage from './components/ChatMessage.jsx'
import DocumentUpload from './components/DocumentUpload.jsx'
import DocumentList from './components/DocumentList.jsx'
import { chatAPI, documentAPI } from './services/api.js'

function App() {
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showDocuments, setShowDocuments] = useState(false)
  const [documents, setDocuments] = useState([])
  const [activeTab, setActiveTab] = useState('chat')
  const messagesEndRef = useRef(null)

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 获取文档列表
  useEffect(() => {
    if (showDocuments) {
      fetchDocuments()
    }
  }, [showDocuments])

  const fetchDocuments = async () => {
    try {
      const response = await documentAPI.getDocuments()
      setDocuments(response.data.documents || [])
    } catch (error) {
      console.error('获取文档列表失败:', error)
    }
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputValue,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      // 流式获取回答
      const response = await chatAPI.chatStream(inputValue, 5)
      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      let assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        sources: []
      }

      setMessages(prev => [...prev, assistantMessage])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data.trim()) {
              try {
                const parsed = JSON.parse(data)
                
                if (parsed.type === 'answer') {
                  assistantMessage.content += parsed.content
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantMessage.id ? { ...msg, content: assistantMessage.content } : msg
                  ))
                } else if (parsed.type === 'sources') {
                  assistantMessage.sources = parsed.sources
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantMessage.id ? { ...msg, sources: parsed.sources } : msg
                  ))
                } else if (parsed.type === 'error') {
                  assistantMessage.content = parsed.content
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantMessage.id ? { ...msg, content: parsed.content } : msg
                  ))
                }
              } catch (e) {
                console.error('解析数据失败:', e)
              }
            }
          }
        }
      }

    } catch (error) {
      console.error('聊天请求失败:', error)
      const errorMessage = {
        id: Date.now() + 2,
        type: 'assistant',
        content: '抱歉，回答生成失败，请稍后重试。',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleFileUpload = async (file, type) => {
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('document_type', type)

      const response = await documentAPI.uploadDocument(formData)
      alert('文档上传成功！')
      if (showDocuments) {
        fetchDocuments()
      }
    } catch (error) {
      console.error('文件上传失败:', error)
      alert('文件上传失败，请重试。')
    }
  }

  const handleDeleteDocument = async (docId) => {
    if (window.confirm('确定要删除这个文档吗？')) {
      try {
        await documentAPI.deleteDocument(docId)
        alert('文档删除成功！')
        fetchDocuments()
      } catch (error) {
        console.error('删除文档失败:', error)
        alert('删除文档失败，请重试。')
      }
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <MessageSquare className="h-8 w-8 text-blue-600 mr-3" />
              <h1 className="text-xl font-bold text-gray-900">MiniRAG 智能问答系统</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowDocuments(!showDocuments)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  showDocuments 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <FileText className="h-4 w-4 inline mr-2" />
                文档管理
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* 主要内容 */}
      <div className="max-w-7xl mx-auto">
        <div className="flex border-b">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'chat'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            智能问答
          </button>
          <button
            onClick={() => setActiveTab('documents')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'documents'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            文档管理
          </button>
        </div>

        {activeTab === 'chat' && (
          <div className="chat-container">
            {/* 消息列表 */}
            <div className="chat-messages">
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-gray-500">
                  <MessageSquare className="h-16 w-16 mb-4" />
                  <h3 className="text-xl font-medium mb-2">欢迎使用 MiniRAG</h3>
                  <p className="text-center max-w-md">
                    上传文档后，您可以在此处提出相关问题，系统将基于文档内容为您生成智能回答。
                  </p>
                </div>
              )}
              
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              
              {isLoading && (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-6 w-6 text-gray-400 animate-spin" />
                  <span className="ml-2 text-gray-500">正在生成回答...</span>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>

            {/* 输入区域 */}
            <div className="chat-input-container">
              <div className="flex items-end space-x-3">
                <div className="flex-1">
                  <textarea
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="请输入您的问题..."
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={1}
                    disabled={isLoading}
                  />
                </div>
                <button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isLoading}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'documents' && (
          <div className="p-6">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">文档管理</h2>
              <DocumentUpload onUpload={handleFileUpload} />
            </div>
            
            <div className="mb-4">
              <h3 className="text-lg font-medium text-gray-900 mb-3">已上传文档</h3>
            </div>
            
            <DocumentList 
              documents={documents} 
              onDelete={handleDeleteDocument}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default App