<script setup>
import AppHeader from './components/layout/AppHeader.vue'
import AppFooter from './components/layout/AppFooter.vue'
import ChatWidget from './components/ChatWidget.vue'
</script>

<template>
  <div class="min-h-screen flex flex-col relative bg-page">
    <AppHeader />
    <main class="flex-1 w-full relative">
      <router-view />
    </main>
    <AppFooter />
    <ChatWidget />
  </div>
</template>
