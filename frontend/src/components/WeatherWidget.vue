<script setup>
import { computed, onMounted, ref } from 'vue'
import { fetchWeather } from '../api/weather'

// compact: header chip (temperature + icon only on small screens, no recommendation text).
const props = defineProps({ compact: { type: Boolean, default: false } })

const weather = ref(null)
const loading = ref(true)
const failed = ref(false)

const temperature = computed(() => {
  const value = Number(weather.value?.temperature)
  return Number.isFinite(value) ? `${Math.round(value)}°C` : ''
})

const RECOMMENDATION_LABELS = {
  outdoor: '야외활동 추천',
  indoor: '실내활동 추천',
  mixed: '실내외 모두 좋음',
}

const recommendationLabel = computed(() => {
  const value = weather.value?.recommendation
  return value ? RECOMMENDATION_LABELS[value] || '' : ''
})

const WEATHER_ICONS = {
  clear: '☀️',
  'partly-cloudy': '🌤️',
  cloudy: '☁️',
  rain: '🌧️',
  'rain-snow': '🌨️',
  snow: '❄️',
  unknown: '🌥️',
}

const weatherIcon = computed(() => {
  const code = String(weather.value?.icon_code || '').trim()
  return WEATHER_ICONS[code] || WEATHER_ICONS.unknown
})

async function loadWeather() {
  loading.value = true
  failed.value = false
  try {
    weather.value = await fetchWeather()
  } catch {
    weather.value = null
    failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadWeather)
</script>

<template>
  <div class="weather-widget flex items-center" aria-live="polite">
    <div
      v-if="loading"
      class="flex items-center gap-2 bg-primary-tint rounded-[24px] px-3 md:px-4 py-1.5 border border-selected-border opacity-60"
    >
      <span class="text-[14px] text-primary-strong md:hidden">날씨…</span>
      <span class="hidden md:inline text-[14px] text-primary-strong">진주 날씨 확인 중…</span>
    </div>

    <div
      v-else-if="failed"
      class="flex items-center gap-2 bg-danger-bg rounded-[24px] px-3 md:px-4 py-1.5 border border-danger-border"
    >
      <span class="text-[13px] text-danger font-medium md:hidden">날씨 오류</span>
      <span class="hidden md:inline text-[14px] text-danger font-medium">
        날씨 정보를 불러올 수 없습니다.
      </span>
      <button
        type="button"
        class="text-[12px] font-bold text-danger underline underline-offset-2 disabled:opacity-50"
        :disabled="loading"
        aria-label="날씨 정보 다시 불러오기"
        @click="loadWeather"
      >
        재시도
      </button>
    </div>

    <div
      v-else-if="weather"
      class="flex items-center gap-1.5 md:gap-2 bg-primary-tint rounded-[24px] px-3 md:px-4 py-1.5 border border-selected-border text-primary-strong text-[14px] font-bold whitespace-nowrap"
      :title="`${weather.condition || ''} · ${weather.source || ''}`"
    >
      <span aria-hidden="true" data-test="weather-icon">{{ weatherIcon }}</span>
      <span class="md:hidden">{{ temperature || '진주' }}</span>
      <span class="hidden md:inline">진주 {{ temperature }}</span>
      <span v-if="recommendationLabel" :class="props.compact ? 'hidden lg:inline' : 'hidden md:inline'">
        · {{ recommendationLabel }}
      </span>
    </div>
    <router-link
      v-if="weather?.recommendation === 'indoor'"
      :to="{ name: 'explore', query: { tags: 'indoor' } }"
      data-test="indoor-link"
      class="ml-2 text-[13px] font-bold text-primary underline underline-offset-2 whitespace-nowrap"
      :class="props.compact ? 'hidden lg:inline' : ''"
    >
      실내 명소 보기
    </router-link>
  </div>
</template>
