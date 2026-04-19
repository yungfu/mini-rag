import React, { useState, useRef } from 'react'
import { Upload, FileText, X, AlertCircle } from 'lucide-react'
import { toast } from 'react-hot-toast'

const DocumentUpload = ({ onUpload }) => {
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const fileInputRef = useRef(null)

  const supportedFormats = ['md', 'txt', 'html']
  const formatNames = {
    md: 'Markdown',
    txt: '纯文本',
    html: 'HTML'
  }

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleChange = (e) => {
    e.preventDefault()
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleFile = (file) => {
    // 检查文件类型
    const fileExtension = file.name.split('.').pop().toLowerCase()
    if (!supportedFormats.includes(fileExtension)) {
      toast.error(`不支持的文件格式: ${fileExtension}`)
      return
    }

    // 检查文件大小 (10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('文件大小不能超过 10MB')
      return
    }

    setSelectedFile(file)
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    setUploading(true)
    try {
      const fileExtension = selectedFile.name.split('.').pop().toLowerCase()
      await onUpload(selectedFile, fileExtension)
      setSelectedFile(null)
      toast.success('文档上传成功！')
    } catch (error) {
      toast.error(error.message || '上传失败')
    } finally {
      setUploading(false)
    }
  }

  const handleCancel = () => {
    setSelectedFile(null)
  }

  const openFileDialog = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="space-y-4">
      {/* 拖拽上传区域 */}
      {!selectedFile && (
        <div
          className={`upload-area ${dragActive ? 'drag-over' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={openFileDialog}
        >
          <Upload className="h-12 w-12 text-gray-400 mx-auto mb-3" />
          <p className="text-lg font-medium text-gray-700 mb-2">
            拖拽文件到此处或点击上传
          </p>
          <p className="text-sm text-gray-500">
            支持 {supportedFormats.map(format => formatNames[format]).join('、')} 格式，
            最大 10MB
          </p>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleChange}
            accept={supportedFormats.map(format => `.${format}`).join(',')}
          />
        </div>
      )}

      {/* 已选择文件，显示预览 */}
      {selectedFile && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-3">
              <FileText className="h-8 w-8 text-blue-600" />
              <div>
                <h4 className="text-sm font-medium text-gray-900">
                  {selectedFile.name}
                </h4>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <button
              onClick={handleCancel}
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex-1">
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <AlertCircle className="h-4 w-4" />
                  <span>正在准备上传...</span>
                </div>
              </div>
            </div>
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {uploading ? '上传中...' : '上传文件'}
            </button>
          </div>
        </div>
      )}

      {/* 上传提示 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">上传说明</p>
            <ul className="space-y-1 text-blue-700">
              <li>• 支持的文件格式：Markdown (.md)、纯文本 (.txt)、HTML (.html)</li>
              <li>• 文件大小限制：最大 10MB</li>
              <li>• 上传后系统会自动解析文档并创建切片</li>
              <li>• 处理完成后即可开始提问</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DocumentUpload