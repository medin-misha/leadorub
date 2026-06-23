import { defineStore } from 'pinia'
import { usersApi } from '@/api/users'
import { profilesApi } from '@/api/profiles'
import { statsApi } from '@/api/stats'
import { extractError } from '@/api/http'

export const useUsersStore = defineStore('users', {
  state: () => ({
    items: [],
    page: 1,
    limit: 10,
    search: '',
    field: '', // '' = полнотекстовый поиск по всем строковым полям
    loading: false,
    error: null,
    hasNext: false,
  }),

  actions: {
    async fetchUsers() {
      this.loading = true
      this.error = null
      try {
        const items = await usersApi.list({
          page: this.page,
          limit: this.limit,
          search: this.search || null,
          field: this.field || null,
        })
        this.items = items
        // total бэкенд не отдаёт → "есть следующая страница" = пришла полная страница.
        this.hasNext = items.length === this.limit
      } catch (err) {
        this.error = extractError(err)
        this.items = []
        this.hasNext = false
      } finally {
        this.loading = false
      }
    },

    async setSearch({ search, field }) {
      this.search = search ?? ''
      this.field = field ?? ''
      this.page = 1 // новый запрос — всегда с первой страницы
      await this.fetchUsers()
    },

    async setPage(page) {
      this.page = Math.max(1, page)
      await this.fetchUsers()
    },

    async setLimit(limit) {
      this.limit = Math.max(1, limit)
      this.page = 1
      await this.fetchUsers()
    },

    async createUser(payload) {
      await usersApi.create(payload)
      await this.fetchUsers()
    },

    async updateUser(id, patch) {
      await usersApi.update(id, patch)
    },

    async deleteUser(id) {
      await usersApi.remove(id)
      await this.fetchUsers()
    },

    createProfile(data) {
      return profilesApi.create(data)
    },
    updateProfile(id, data) {
      return profilesApi.patch(id, data)
    },
    createStats(data) {
      return statsApi.create(data)
    },
    updateStats(id, data) {
      return statsApi.patch(id, data)
    },
  },
})
