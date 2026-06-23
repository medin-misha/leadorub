<script setup>
import { ref } from 'vue'
import { useNewsletterStore } from '@/stores/newsletter'
import AudiencePanel from '@/components/newsletter/AudiencePanel.vue'
import MessageComposer from '@/components/newsletter/MessageComposer.vue'
import NewsletterConfirmDialog from '@/components/newsletter/NewsletterConfirmDialog.vue'

const store = useNewsletterStore()

const confirming = ref(false)
const sentNotice = ref(false)

function onSubmit() {
  store.error = null
  confirming.value = true
}

function onSent() {
  confirming.value = false
  sentNotice.value = true
  // авто-скрытие уведомления об успехе
  setTimeout(() => (sentNotice.value = false), 4000)
}
</script>

<template>
  <div class="newsletter">
    <p v-if="sentNotice" class="newsletter__notice">Рассылка поставлена в очередь ✓</p>
    <p v-if="store.error && !confirming" class="newsletter__error">{{ store.error }}</p>

    <div class="newsletter__cols">
      <AudiencePanel class="newsletter__left" />
      <MessageComposer class="newsletter__right" @submit="onSubmit" />
    </div>

    <NewsletterConfirmDialog
      v-if="confirming"
      @close="confirming = false"
      @sent="onSent"
    />
  </div>
</template>

<style scoped>
.newsletter {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.newsletter__cols {
  display: flex;
  gap: var(--space-4);
  align-items: flex-start;
  flex-wrap: wrap;
}
.newsletter__left {
  flex: 0 0 320px;
}
.newsletter__right {
  flex: 1 1 420px;
}
.newsletter__notice {
  margin: 0;
  padding: var(--space-3);
  border-radius: var(--radius);
  background: var(--color-success-bg);
  color: var(--color-success);
}
.newsletter__error {
  margin: 0;
  color: var(--color-danger);
}
</style>
