<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from './components/layout/AppHeader.vue'
import AppFooter from './components/layout/AppFooter.vue'
import AppTabBar from './components/layout/AppTabBar.vue'
import DemoBanner from './components/layout/DemoBanner.vue'
import ChatWidget from './components/ChatWidget.vue'
import CelebrationToast from './components/lanterns/CelebrationToast.vue'
import { useBreakpoint } from './composables/useBreakpoint'
import DemoSettings from './components/demo/DemoSettings.vue'
import { useCollectionStore } from './stores/collection'
import { useLanternsStore } from './stores/lanterns'

const collection = useCollectionStore()
const lanterns = useLanternsStore()
const route = useRoute()
const router = useRouter()
// ?demo=1 on first load turns demo mode on (keeping any saved reference date).
// Wait for the router: the initial route's query is empty until navigation resolves.
router.isReady().then(() => {
  if (route.query.demo === '1') {
    lanterns.setDemo({ enabled: true, today: lanterns.demo.today, pos: lanterns.demo.pos })
  }
})
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
// Map-first pages fill the viewport exactly (no page scroll, no footer).
const fullscreen = computed(() => !!route.meta.fullscreen)
</script>

<template>
  <div
    class="flex flex-col relative bg-page"
    :class="[fullscreen ? 'h-[100dvh] overflow-hidden' : 'min-h-screen', { 'pb-14': isMobile }]"
  >
    <DemoBanner :active="lanterns.demo.enabled" :date="lanterns.demo.today || ''" />
    <AppHeader />
    <main class="flex-1 w-full relative" :class="{ 'min-h-0': fullscreen }">
      <router-view />
    </main>
    <AppFooter v-if="!fullscreen" />
    <AppTabBar v-if="isMobile" />
    <ChatWidget />
    <CelebrationToast />
    <DemoSettings />
  </div>
</template>
