<script setup>
defineProps({ title: { type: String, required: true } })
</script>

<template>
  <div class="placeholder">
    <h2>{{ title }}</h2>
    <p>Раздел в разработке.</p>
  </div>
</template>

<style scoped>
.placeholder {
  padding: var(--space-5);
  text-align: center;
  color: var(--color-text-muted);
}
</style>
