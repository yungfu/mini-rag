import React from 'react'
import { FileText, Clock, CheckCircle, XCircle, Trash2 } from 'lucide-react'

const DocumentList = ({ documents, onDelete }) => {
  const getStatusColor = (status) => {
    switch (status) {
      case 'ready':
        return 'text-green-600 bg-green-100'
      case 'processing':
        return 'text-blue-600 bg-blue-100'
      case 'failed':
        return 'text-red-600 bg-red-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'ready':
        return <CheckCircle className="h-4 w-4" />
      case 'processing':
        return <Clock className="h-4 w-4" />
      case 'failed':
        return <XCircle className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDate = (dateString) => {
    if (!dateString) return '未知时间'
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (documents.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-8 text-center">
        <FileText className="h-12 w-12 text-gray-400 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">暂无文档</h3>
        <p className="text-gray-500">请先上传文档以开始使用智能问答功能</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {documents.map((document) => (
        <div key={document.doc_id} className="document-item">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3 flex-1">
              {/* 文档图标 */}
              <div className="flex-shrink-0">
                <FileText className="h-8 w-8 text-blue-600" />
              </div>
              
              {/* 文档信息 */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-1">
                  <h4 className="text-sm font-medium text-gray-900 truncate">
                    {document.filename}
                  </h4>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(document.status)}`}>
                    {getStatusIcon(document.status)}
                    <span className="ml-1">
                      {document.status === 'ready' ? '就绪' : 
                       document.status === 'processing' ? '处理中' : 
                       document.status === 'failed' ? '失败' : 
                       document.status === 'deleted' ? '已删除' : document.status}
                    </span>
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
                  <div className="flex items-center space-x-1">
                    <span>类型:</span>
                    <span className="font-medium">{document.file_type.toUpperCase()}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <span>大小:</span>
                    <span className="font-medium">{formatFileSize(document.file_size)}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <span>创建:</span>
                    <span className="font-medium">{formatDate(document.created_at)}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <span>更新:</span>
                    <span className="font-medium">{formatDate(document.updated_at)}</span>
                  </div>
                </div>
                
                {/* 处理中的文档显示额外信息 */}
                {document.status === 'processing' && (
                  <div className="mt-2 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                    <div className="flex items-center space-x-1">
                      <Clock className="h-3 w-3" />
                      <span>文档正在处理中，请稍候...</span>
                    </div>
                  </div>
                )}
                
                {/* 失败的文档显示错误信息 */}
                {document.status === 'failed' && (
                  <div className="mt-2 text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                    <div className="flex items-center space-x-1">
                      <XCircle className="h-3 w-3" />
                      <span>文档处理失败，请检查文件格式后重新上传</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            {/* 删除按钮 */}
            <div className="flex-shrink-0 ml-4">
              {document.status !== 'deleted' && (
                <button
                  onClick={() => onDelete(document.doc_id)}
                  className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="删除文档"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default DocumentList