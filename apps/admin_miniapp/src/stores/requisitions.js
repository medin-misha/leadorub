import { defineStore } from 'pinia'
import { requisitionsApi } from '@/api/requisitions'
import { extractError } from '@/api/http'

export const useRequisitionsStore = defineStore('requisitions', {
  state: () => ({
    items: [],
    page: 1,
    limit: 10,
    search: '',
    status: '', // '' = все
    type: '', // '' = все
    loading: false,
    error: null,
    hasNext: false,
  }),

  actions: {
    async fetchRequisitions() {
      this.loading = true
      this.error = null
      try {
        const items = await requisitionsApi.list({
          page: this.page,
          limit: this.limit,
          search: this.search || null,
          status: this.status || null,
          type: this.type || null,
        })
        this.items = items
        this.hasNext = items.length === this.limit
      } catch (err) {
        this.error = extractError(err)
        this.items = []
        this.hasNext = false
      } finally {
        this.loading = false
      }
    },

    async setSearch(search) {
      this.search = search ?? ''
      this.page = 1
      await this.fetchRequisitions()
    },

    async setStatus(status) {
      this.status = status ?? ''
      this.page = 1
      await this.fetchRequisitions()
    },

    async setType(type) {
      this.type = type ?? ''
      this.page = 1
      await this.fetchRequisitions()
    },

    async setPage(page) {
      this.page = Math.max(1, page)
      await this.fetchRequisitions()
    },

    async setLimit(limit) {
      this.limit = Math.max(1, limit)
      this.page = 1
      await this.fetchRequisitions()
    },

    async updateStatus(id, { status, admin_comment = null }) {
      this.loading = true
      this.error = null
      try {
        const updatedItem = await requisitionsApi.updateStatus(id, { status, admin_comment })
        const idx = this.items.findIndex((item) => item.id === id)
        if (idx !== -1) {
          this.items[idx] = updatedItem
        }
        return updatedItem
      } catch (err) {
        this.error = extractError(err)
        throw err
      } finally {
        this.loading = false
      }
    },
  },
})
