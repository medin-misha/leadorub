<script setup>
import { tabs } from '@/tabs'
</script>

<template>
  <nav class="tabbar">
    <RouterLink
      v-for="tab in tabs"
      :key="tab.key"
      :to="`/${tab.key}`"
      class="tabbar__item"
      active-class="tabbar__item--active"
    >
      {{ tab.label }}
    </RouterLink>
  </nav>
</template>

<style scoped>
.tabbar {
  display: flex;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}
.tabbar__item {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius);
  text-decoration: none;
  color: var(--color-text-muted);
  font-weight: 500;
}
.tabbar__item--active {
  background: var(--color-primary);
  color: #fff;
}
</style>
