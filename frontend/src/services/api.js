import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    console.error(`API Error: ${error.response?.status} ${error.config?.url}`, error)
    return Promise.reject(error)
  }
)

// 聊天API
export const chatAPI = {
  chatStream: async (query, top_k = 5) => {
    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        top_k,
      }),
    })
    
    if (!response.ok) {
      throw new Error('聊天请求失败')
    }
    
    return response
  },
  
  chat: async (query, top_k = 5) => {
    const response = await api.post('/chat', {
      query,
      top_k,
    })
    return response.data
  },
}

// 文档API
export const documentAPI = {
  uploadDocument: async (formData) => {
    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      body: formData,
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || '文档上传失败')
    }
    
    return response.json()
  },
  
  getDocuments: async () => {
    const response = await api.get('/documents')
    return response.data
  },
  
  deleteDocument: async (docId) => {
    const response = await api.delete(`/documents/${docId}`)
    return response.data
  },
}

// 健康检查API
export const healthAPI = {
  check: async () => {
    const response = await api.get('/health')
    return response.data
  },
}

export default api