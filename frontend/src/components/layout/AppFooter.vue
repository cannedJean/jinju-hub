<script setup>
import { openDemoSettings } from '../../composables/useDemoSettings'
</script>

<template>
  <footer class="bg-night-900 text-white/70 text-[13px] px-4 md:px-8 py-6 text-center md:text-left">
    <p>한국관광공사 TourAPI · 진주시 공공데이터</p>
    <p class="mt-1">지도 © OpenStreetMap contributors</p>
    <router-link to="/about/data" class="inline-block mt-2 underline underline-offset-2">데이터 출처 보기</router-link>
    <button type="button" class="inline-block mt-2 ml-4 underline underline-offset-2" @click="openDemoSettings">시연 설정</button>
  </footer>
</template>
