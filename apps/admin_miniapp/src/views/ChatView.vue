<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useChatStore } from '@/stores/chat'
import BaseInput from '@/components/ui/BaseInput.vue'
import ConversationList from '@/components/chat/ConversationList.vue'
import ChatThread from '@/components/chat/ChatThread.vue'
import ChatComposer from '@/components/chat/ChatComposer.vue'

const store = useChatStore()
const { conversations, activeUid, messages, loadingThread, sending, error } =
  storeToRefs(store)

const route = useRoute()

// Поиск по диалогам с debounce, чтобы не дёргать backend на каждый символ.
const search = ref('')
let searchTimer = null
watch(search, (value) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => store.setSearch(value.trim()), 300)
})

// Composer отдаёт { text, file } — разворачиваем в сигнатуру стора.
function onSend({ text, file }) {
  store.sendReply(text, file)
}

// Заголовок активного диалога для шапки правой панели.
function activeTitle() {
  const c = store.activeConversation
  if (!c) return ''
  const name = [c.first_name, c.last_name].filter(Boolean).join(' ')
  if (name) return name
  if (c.username) return '@' + c.username
  return 'ID ' + c.telegram_id
}

onMounted(async () => {
  await store.fetchConversations()
  store.startListPolling()

  const userId = parseInt(route.query.userId, 10)
  if (!isNaN(userId)) {
    await store.initializeAndOpenConversation(userId)
  }
})

watch(
  () => route.query.userId,
  async (newVal) => {
    if (newVal) {
      const userId = parseInt(newVal, 10)
      if (!isNaN(userId)) {
        await store.initializeAndOpenConversation(userId)
      }
    }
  }
)

// Критично: гасим все интервалы при уходе с вкладки, иначе они утекут.
onUnmounted(() => {
  clearTimeout(searchTimer)
  store.stopAllPolling()
  store.closeConversation()
})
</script>

<template>
  <div class="chat">
    <p v-if="error" class="chat__error">{{ error }}</p>

    <div class="chat__cols">
      <aside class="chat__list">
        <div class="chat__search">
          <BaseInput v-model="search" placeholder="Поиск диалогов…" />
        </div>
        <ConversationList
          :conversations="conversations"
          :active-uid="activeUid"
          @select="store.openConversation"
        />
      </aside>

      <section class="chat__thread">
        <template v-if="activeUid != null">
          <header class="chat__header">{{ activeTitle() }}</header>
          <ChatThread :messages="messages" :loading="loadingThread" />
          <ChatComposer :sending="sending" @send="onSend" />
        </template>
        <div v-else class="chat__placeholder">Выберите диалог слева</div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.chat__error {
  margin: 0;
  color: var(--color-danger);
}
.chat__cols {
  display: flex;
  gap: var(--space-4);
  height: 70vh;
}
.chat__list {
  flex: 0 0 300px;
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
}
.chat__search {
  padding: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}
.chat__thread {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
}
.chat__header {
  padding: var(--space-3);
  font-weight: 600;
  border-bottom: 1px solid var(--color-border);
}
.chat__placeholder {
  margin: auto;
  color: var(--color-text-muted);
}
</style>
