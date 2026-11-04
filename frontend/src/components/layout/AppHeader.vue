<script setup>
// Temporary stub; replaced in C2.
import WeatherWidget from '../WeatherWidget.vue'
</script>

<template>
  <header class="sticky top-0 z-[60] h-[72px] bg-night-900 flex items-center justify-between px-6 md:px-8">
    <router-link to="/" class="text-[22px] font-extrabold text-lantern-500 tracking-tight">
      JinjuHub
    </router-link>
    <nav class="flex items-center gap-6 text-white text-[15px]">
      <router-link to="/boards">게시판</router-link>
      <WeatherWidget />
    </nav>
  </header>
</template>
