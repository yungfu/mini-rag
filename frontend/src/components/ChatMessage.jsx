import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Bot, User, FileText, Copy, Check } from 'lucide-react'
import { toast } from 'react-hot-toast'

const ChatMessage = ({ message }) => {
  const [copied, setCopied] = React.useState(false)

  const handleCopy = async (text) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      toast.success('已复制到剪贴板')
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      toast.error('复制失败')
    }
  }

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (message.type === 'user') {
    return (
      <div className="flex justify-end">
        <div className="message-user">
          <div className="flex items-center space-x-2 mb-1">
            <User className="h-4 w-4" />
            <span className="text-xs opacity-75">用户</span>
            <span className="text-xs opacity-75">{formatTimestamp(message.timestamp)}</span>
          </div>
          <div className="text-sm">
            {message.content}
          </div>
        </div>
      </div>
    )
  }

  if (message.type === 'assistant') {
    return (
      <div className="flex justify-start">
        <div className="message-assistant">
          <div className="flex items-center space-x-2 mb-1">
            <Bot className="h-4 w-4" />
            <span className="text-xs opacity-75">助手</span>
            <span className="text-xs opacity-75">{formatTimestamp(message.timestamp)}</span>
          </div>
          <div className="text-sm">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              className="prose prose-sm max-w-none"
            >
              {message.content}
            </ReactMarkdown>
          </div>
          
          {/* 来源信息 */}
          {message.sources && message.sources.length > 0 && (
            <div className="message-source">
              <div className="flex items-center space-x-2 mb-2">
                <FileText className="h-4 w-4" />
                <span className="text-sm font-medium">参考来源</span>
              </div>
              {message.sources.map((source, index) => (
                <div key={source.id || index} className="source-item">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="text-xs text-gray-500 mb-1">
                        文档ID: {source.doc_id} | 切片: {source.chunk_index}
                      </div>
                      <div className="text-sm text-gray-700">
                        {source.content_large.substring(0, 200)}
                        {source.content_large.length > 200 && '...'}
                      </div>
                    </div>
                    <button
                      onClick={() => handleCopy(source.content_large)}
                      className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      {copied ? (
                        <Check className="h-4 w-4 text-green-500" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  return null
}

export default ChatMessage