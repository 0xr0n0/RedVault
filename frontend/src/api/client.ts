/**
 * Axios instance configured with JWT interceptors.
 */
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/redvault/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// Request interceptor: attach access token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Token refresh lock to prevent race conditions
let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

function addRefreshSubscriber(callback: (token: string) => void) {
  refreshSubscribers.push(callback)
}

// Response interceptor: refresh token on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      localStorage.getItem('refresh_token')
    ) {
      originalRequest._retry = true

      if (isRefreshing) {
        // Wait for the ongoing refresh to complete
        return new Promise((resolve) => {
          addRefreshSubscriber((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(api(originalRequest))
          })
        })
      }

      isRefreshing = true
      try {
        const { data } = await axios.post(
          `${api.defaults.baseURL}/auth/refresh/`,
          { refresh: localStorage.getItem('refresh_token') }
        )
        localStorage.setItem('access_token', data.access)
        if (data.refresh) {
          localStorage.setItem('refresh_token', data.refresh)
        }
        isRefreshing = false
        onRefreshed(data.access)
        originalRequest.headers.Authorization = `Bearer ${data.access}`
        return api(originalRequest)
      } catch {
        isRefreshing = false
        refreshSubscribers = []
        // Refresh failed — force logout
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/redvault/login'
      }
    }

    return Promise.reject(error)
  }
)

export default api

/** Base URL of the backend (without /api/v1) for building media URLs. */
const rawBase = import.meta.env.VITE_API_URL || '/redvault/api/v1'
export const backendBase = rawBase.startsWith('http')
  ? rawBase.replace(/\/api\/v1\/?$/, '')
  : rawBase.replace(/\/api\/v1\/?$/, '')  // e.g. '/redvault'

/**
 * Build a full media URL from a path that may be relative (/media/...) or absolute.
 */
export function mediaUrl(path: string): string {
  if (path.startsWith('http')) return path
  return `${backendBase}${path}`
}

/**
 * Download a file from an authenticated media endpoint via Axios
 * and trigger a browser download dialog.
 */
export async function downloadMedia(path: string, filename?: string): Promise<void> {
  const url = mediaUrl(path)
  const response = await api.get(url, { responseType: 'blob', baseURL: '' })
  const blob = new Blob([response.data])
  const blobUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = filename || path.split('/').pop() || 'download'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(blobUrl)
}

/**
 * Fetch a media file and return an object URL (blob:...) for use in <img> tags.
 * Caller is responsible for revoking the URL when done.
 */
export async function fetchMediaBlob(path: string): Promise<string> {
  const url = mediaUrl(path)
  const response = await api.get(url, { responseType: 'blob', baseURL: '' })
  return window.URL.createObjectURL(new Blob([response.data]))
}
