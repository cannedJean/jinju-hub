<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import StateView from '../components/StateView.vue'
import FestivalCard from '../components/festival/FestivalCard.vue'
import FestivalTimeline from '../components/festival/FestivalTimeline.vue'
import { useFestivalsStore } from '../stores/festivals'
import { useLanternsStore } from '../stores/lanterns'

const festivals = useFestivalsStore()
const lanterns = useLanternsStore()
const TABS = [
  { key: 'ongoing', label: '진행 중' },
  { key: 'upcoming', label: '예정' },
  { key: 'past', label: '지난 축제' },
]
const tab = ref('ongoing')
const list = computed(() => festivals[tab.value])
const today = computed(() => festivals.today || lanterns.effectiveToday)

onMounted(festivals.load)
watch([() => lanterns.effectiveToday, () => lanterns.demo.enabled], () => festivals.load())
</script>

<template>
  <section class="max-w-[1200px] mx-auto px-4 md:px-8 py-8">
    <h1 class="text-2xl font-extrabold text-strong">축제·행사</h1>
    <StateView
      :loading="festivals.loading && !festivals.loaded"
      :error="festivals.error && !festivals.loaded"
      @retry="festivals.load"
    >
      <div class="mt-4">
        <FestivalTimeline :festivals="festivals.items" :today="today" />
      </div>
      <div class="mt-6 flex gap-2" role="tablist" aria-label="축제 구분">
        <button
          v-for="t in TABS"
          :key="t.key"
          type="button"
          role="tab"
          :aria-selected="tab === t.key"
          class="px-4 py-2 rounded-full text-[14px] font-bold"
          :class="tab === t.key ? 'bg-night-900 text-white' : 'bg-subtle text-strong'"
          @click="tab = t.key"
        >
          {{ t.label }} {{ festivals[t.key].length }}
        </button>
      </div>
      <StateView :empty="!list.length" empty-message="해당하는 축제가 없어요.">
        <div class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <FestivalCard v-for="f in list" :key="f.id" :festival="f" />
        </div>
      </StateView>
    </StateView>
  </section>
</template>
