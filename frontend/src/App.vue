<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './components/layout/AppHeader.vue'
import AppFooter from './components/layout/AppFooter.vue'
import AppTabBar from './components/layout/AppTabBar.vue'
import DemoBanner from './components/layout/DemoBanner.vue'
import ChatWidget from './components/ChatWidget.vue'
import CelebrationToast from './components/lanterns/CelebrationToast.vue'
import { useBreakpoint } from './composables/useBreakpoint'
import { useCollectionStore } from './stores/collection'

const collection = useCollectionStore()
// Header progress and badge toasts need the collection definition; a failure just leaves 0/30.
onMounted(async () => {
  try {
    await collection.load()
    collection.checkBadges()
  } catch {
    // retried on the next load (e.g. visiting 내 유등)
  }
})

const { isMobile } = useBreakpoint()
const route = useRoute()
// Map-first pages fill the viewport exactly (no page scroll, no footer).
const fullscreen = computed(() => !!route.meta.fullscreen)
// Placeholder flag; C3/C7 wire the real demo-mode store.
const demo = ref({ active: false, date: '' })
</script>

<template>
  <div
    class="flex flex-col relative bg-page"
    :class="[fullscreen ? 'h-[100dvh] overflow-hidden' : 'min-h-screen', { 'pb-14': isMobile }]"
  >
    <DemoBanner :active="demo.active" :date="demo.date" />
    <AppHeader />
    <main class="flex-1 w-full relative" :class="{ 'min-h-0': fullscreen }">
      <router-view />
    </main>
    <AppFooter v-if="!fullscreen" />
    <AppTabBar v-if="isMobile" />
    <ChatWidget />
    <CelebrationToast />
  </div>
</template>
