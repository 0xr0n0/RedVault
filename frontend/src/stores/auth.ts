/**
 * Auth store — manages JWT tokens and current user profile.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client'
import type { User, LoginRequest, TokenPair } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))

  const isAuthenticated = computed(() => !!accessToken.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isAnalyst = computed(() => user.value?.role === 'analyst' || user.value?.role === 'admin')

  async function login(credentials: LoginRequest) {
    const { data } = await api.post<TokenPair>('/auth/login/', credentials)
    accessToken.value = data.access
    refreshToken.value = data.refresh
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    await fetchProfile()
  }

  async function fetchProfile() {
    try {
      const { data } = await api.get<User>('/auth/profile/')
      user.value = data
    } catch {
      logout()
    }
  }

  function logout() {
    user.value = null
    accessToken.value = null
    refreshToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  // On store init, if we have a token, fetch the profile
  async function init() {
    if (accessToken.value) {
      await fetchProfile()
    }
  }

  return {
    user,
    accessToken,
    refreshToken,
    isAuthenticated,
    isAdmin,
    isAnalyst,
    login,
    fetchProfile,
    logout,
    init,
  }
})
