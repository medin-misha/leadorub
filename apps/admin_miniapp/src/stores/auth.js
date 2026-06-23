import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'
import { extractError, TOKEN_KEY } from '@/api/http'

// Сессия админа: JWT в localStorage переживает перезагрузку страницы.
export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    admin: null, // данные текущего админа (после /auth/me)
    loading: false,
    error: null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
  },

  actions: {
    async login(username, password) {
      this.loading = true
      this.error = null
      try {
        const { access_token } = await authApi.login(username, password)
        this.token = access_token
        localStorage.setItem(TOKEN_KEY, access_token)
        await this.fetchMe()
        return true
      } catch (err) {
        this.error = extractError(err)
        return false
      } finally {
        this.loading = false
      }
    },

    async fetchMe() {
      this.admin = await authApi.me()
      return this.admin
    },

    logout() {
      this.token = ''
      this.admin = null
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})
