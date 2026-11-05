<script setup>
import { computed, ref, watch } from 'vue'
import { useCollectionStore } from '../../stores/collection'
import { useLanternsStore } from '../../stores/lanterns'
import { useRoute, useRouter } from 'vue-router'
import WeatherWidget from '../WeatherWidget.vue'
import { useBreakpoint } from '../../composables/useBreakpoint'
import { DEFAULT_STATE, parseQuery, searchState, toQuery } from '../../composables/useExploreQuery'

const collection = useCollectionStore()
// The 32px demo banner is sticky at top-0; stack the header below it.
const demoOn = computed(() => useLanternsStore().demo.enabled)
const progress = computed(() => collection.progress)
const total = computed(() => collection.collectionIds.length || 30)

const router = useRouter()
const route = useRoute()
const { isMobile } = useBreakpoint()
const query = ref('')

// Keep the box in sync with the explore URL (back/forward, clearing the search in the panel).
watch(
  () => [route.name, route.query.q],
  ([name, q]) => {
    if (name === 'explore') query.value = typeof q === 'string' ? q : ''
  },
  { immediate: true },
)

const NAV = [
  { to: '/explore', label: '탐색' },
  { to: '/lanterns', label: '내 유등' },
  { to: '/festivals', label: '축제' },
  { to: '/boards', label: '게시판' },
  { to: '/about/data', label: '데이터 출처' },
]

// On the explore page a new search keeps the lodging radius (near/radius/sort); elsewhere it starts fresh.
function submit() {
  const current = route.name === 'explore' ? parseQuery(route.query) : DEFAULT_STATE
  router.push({ name: 'explore', query: toQuery(searchState(current, query.value)) })
}
</script>

<template>
  <header
    class="sticky z-[60] bg-night-900 flex items-center gap-2 sm:gap-4 px-3 sm:px-4 md:px-8"
    :class="[isMobile ? 'h-14 justify-between' : 'h-[72px]', demoOn ? 'top-8' : 'top-0']"
  >
    <router-link
      to="/"
      class="text-lantern-500 font-extrabold tracking-tight whitespace-nowrap shrink-0"
      :class="isMobile ? 'text-[18px]' : 'text-[22px]'"
    >
      JinjuHub<span v-if="!isMobile" class="ml-1.5 text-white/80 font-bold text-[16px]">진주</span>
    </router-link>

    <form class="flex-1 max-w-[360px] min-w-0" role="search" @submit.prevent="submit">
      <label for="header-search" class="sr-only">장소 검색</label>
      <input
        id="header-search"
        name="search"
        v-model="query"
        type="search"
        placeholder="장소, 음식, 축제 검색"
        aria-label="장소 검색"
        class="w-full rounded-full bg-white/10 text-white placeholder-white/75 px-3 sm:px-4 py-1.5 sm:py-2 text-[13px] sm:text-[14px] outline-none focus:bg-white/20"
      />
    </form>

    <nav v-if="!isMobile" class="flex items-center gap-5 text-white text-[15px] ml-auto" aria-label="주 메뉴">
      <router-link
        v-for="item in NAV"
        :key="item.to"
        :to="item.to"
        class="hover:text-lantern-400 whitespace-nowrap"
        active-class="text-lantern-500 font-bold"
      >
        {{ item.label }}
      </router-link>
    </nav>

    <div class="flex items-center gap-2 sm:gap-3 shrink-0" :class="{ 'ml-auto': !isMobile }">
      <WeatherWidget compact />
      <slot name="lantern-progress">
        <router-link
          to="/lanterns"
          class="text-lantern-500 font-bold text-[14px] whitespace-nowrap"
          data-test="lantern-progress"
          :aria-label="collection.error && !collection.loaded ? '유등 30선 진행도를 불러오지 못했어요, 내 유등 보기' : `유등 30선 진행도 ${progress}/${total}, 내 유등 보기`"
        >
          <span aria-hidden="true">◆ {{ collection.loaded ? progress : '–' }}/{{ total }}</span>
        </router-link>
      </slot>
    </div>
  </header>
</template>
