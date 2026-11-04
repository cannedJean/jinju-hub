<script setup>
// 404 fallback route.
</script>

<template>
  <div class="flex flex-col items-center justify-center py-32 px-6 text-center min-h-[calc(100vh-260px)]">
    <h1 class="text-6xl font-extrabold text-primary mb-4">404</h1>
    <h2 class="text-2xl font-bold text-heading mb-6">존재하지 않는 페이지입니다</h2>
    <p class="text-[15px] text-muted mb-8 max-w-md">
      요청하신 페이지를 찾을 수 없습니다. 주소를 다시 확인하시거나 홈으로 돌아가 주세요.
    </p>
    <div class="flex gap-4">
      <router-link
        to="/"
        class="px-6 py-3 bg-primary text-white font-bold rounded-lg hover:bg-primary-strong transition-colors"
      >
        홈으로 가기
      </router-link>
      <router-link
        to="/places"
        class="px-6 py-3 bg-white border border-border text-strong font-bold rounded-lg hover:bg-page transition-colors"
      >
        지역정보 보기
      </router-link>
    </div>
  </div>
</template>
