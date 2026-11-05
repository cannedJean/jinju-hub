<script setup>
import { computed, onMounted } from 'vue'
import { openDemoSettings } from '../../composables/useDemoSettings'
import { useMetaStore } from '../../stores/meta'

const meta = useMetaStore()
const dataVersion = computed(() => meta.data?.data_version || '')
onMounted(() => meta.load())
</script>

<template>
  <footer class="bg-night-900 text-white/70 text-[13px] px-4 md:px-8 py-6 text-center md:text-left">
    <p>한국관광공사 TourAPI · 진주시 공공데이터</p>
    <p class="mt-1">지도 © OpenStreetMap contributors</p>
    <p v-if="dataVersion" class="mt-1" data-test="data-version">데이터 버전 {{ dataVersion }}</p>
    <router-link to="/about/data" class="inline-block mt-2 underline underline-offset-2">데이터 출처</router-link>
    <button type="button" class="inline-block mt-2 ml-4 underline underline-offset-2" @click="openDemoSettings">시연 설정</button>
  </footer>
</template>
