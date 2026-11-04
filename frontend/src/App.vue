<script setup>
import { ref } from 'vue'
import AppHeader from './components/layout/AppHeader.vue'
import AppFooter from './components/layout/AppFooter.vue'
import AppTabBar from './components/layout/AppTabBar.vue'
import DemoBanner from './components/layout/DemoBanner.vue'
import ChatWidget from './components/ChatWidget.vue'
import { useBreakpoint } from './composables/useBreakpoint'

const { isMobile } = useBreakpoint()
// Placeholder flag; C3/C7 wire the real demo-mode store.
const demo = ref({ active: false, date: '' })
</script>

<template>
  <div class="min-h-screen flex flex-col relative bg-page" :class="{ 'pb-14': isMobile }">
    <DemoBanner :active="demo.active" :date="demo.date" />
    <AppHeader />
    <main class="flex-1 w-full relative">
      <router-view />
    </main>
    <AppFooter />
    <AppTabBar v-if="isMobile" />
    <ChatWidget />
  </div>
</template>
