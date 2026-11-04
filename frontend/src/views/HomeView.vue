<script setup>
import { computed, onMounted, watch } from 'vue'
import WeatherWidget from '../components/WeatherWidget.vue'
import { useCollectionStore } from '../stores/collection'
import { useFestivalsStore } from '../stores/festivals'
import { useLanternsStore } from '../stores/lanterns'
import { formatDateRange } from '../utils/format'

const collection = useCollectionStore()
const festivals = useFestivalsStore()
const lanterns = useLanternsStore()

const jinju8 = computed(() => collection.data?.jinju8 || [])
const total = computed(() => collection.collectionIds.length || 30)
const progress = computed(() => collection.progress)

const banner = computed(() => {
  const f = festivals.ongoing[0]
  if (f) return `지금 진행 중: ${f.title} (${formatDateRange(f.start_date, f.end_date)})`
  const u = festivals.upcoming[0]
  if (u) return `다음 축제: ${u.title} (${formatDateRange(u.start_date, u.end_date)}) · ${u.status_label}`
  const label = festivals.items[0]?.status_label
  return `유등축제는 매년 10월${label ? ` · ${label}` : ''}`
})

onMounted(() => {
  festivals.load()
  collection.load().catch(() => {})
})
watch(() => [lanterns.demo.enabled, lanterns.demo.today], festivals.load)
</script>

<template>
  <div>
    <section class="bg-night-900 text-white px-4 md:px-8 py-14 md:py-20 text-center">
      <h1 class="text-[28px] md:text-[44px] font-extrabold text-lantern-500">진주, 남강에 유등을 띄우다</h1>
      <p class="mt-3 text-[15px] md:text-[18px] text-white/80">내일 갈 곳을 담고, 도착하면 유등을 밝혀요</p>
      <router-link
        to="/explore"
        class="inline-block mt-6 px-6 py-3 rounded-full bg-lantern-500 text-night-900 font-bold text-[16px]"
      >
        지도에서 탐색
      </router-link>
    </section>

    <div class="max-w-[1200px] mx-auto px-4 md:px-8 py-8 space-y-8">
      <router-link
        to="/festivals"
        data-test="festival-banner"
        class="block rounded-xl bg-primary-tint border border-selected-border px-4 py-3 text-[15px] font-bold text-primary-strong"
      >
        🎆 {{ banner }}
      </router-link>

      <div class="grid gap-4 md:grid-cols-2">
        <section class="bg-card border border-border rounded-xl p-4">
          <h2 class="text-[15px] font-extrabold text-strong mb-3">오늘 진주 날씨</h2>
          <WeatherWidget />
        </section>
        <router-link to="/lanterns" class="bg-card border border-border rounded-xl p-4 block" data-test="progress-card">
          <h2 class="text-[15px] font-extrabold text-strong">유등 30선 진행도</h2>
          <p class="mt-2 text-[24px] font-extrabold text-lantern-500">◆ {{ progress }}/{{ total }}</p>
          <div class="mt-2 h-2 rounded-full bg-subtle overflow-hidden">
            <div class="h-full bg-lantern-500" :style="{ width: (progress / total) * 100 + '%' }"></div>
          </div>
        </router-link>
      </div>

      <section v-if="jinju8.length">
        <h2 class="text-[18px] font-extrabold text-strong mb-3">진주8경</h2>
        <ul class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <li v-for="p in jinju8" :key="p.id">
            <router-link
              :to="`/places/${p.id}`"
              data-test="jinju8-card"
              class="block bg-card border border-border rounded-xl p-4 h-full hover:border-lantern-500"
            >
              <span class="text-[12px] font-bold text-lantern-500">{{ p.rank }}경</span>
              <span class="block mt-1 text-[15px] font-bold text-strong">{{ p.title }}</span>
            </router-link>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
