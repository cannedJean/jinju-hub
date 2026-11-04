<script setup>
import { computed, ref, watch } from 'vue'
import ImagePlaceholder from '../ImagePlaceholder.vue'

const props = defineProps({
  images: { type: Array, default: () => [] },
  emoji: { type: String, default: '📍' },
})

const LICENSE_LABELS = {
  Type1: '공공누리 제1유형',
  Type3: '공공누리 제3유형(변경 금지)',
  jinju_city_unverified: '진주시 제공',
}

const index = ref(0)
const failed = ref(new Set())

watch(
  () => props.images,
  () => {
    index.value = 0
    failed.value = new Set()
  },
)

const usable = computed(() => props.images.filter((im) => im && im.url && !failed.value.has(im.url)))
const current = computed(() => usable.value[Math.min(index.value, usable.value.length - 1)] || null)

function caption(im) {
  const license = LICENSE_LABELS[im.license] ?? im.license ?? ''
  return ['출처: ' + (im.source || '알 수 없음'), license].filter(Boolean).join(' · ')
}

function onError(url) {
  failed.value = new Set([...failed.value, url])
}
</script>

<template>
  <figure v-if="current" class="gallery">
    <div class="gallery__frame">
      <img
        :src="current.url"
        alt="장소 사진"
        style="object-fit: contain; width: 100%; height: 100%"
        @error="onError(current.url)"
      />
    </div>
    <figcaption class="gallery__caption">{{ caption(current) }}</figcaption>
    <div v-if="usable.length > 1" class="gallery__thumbs" role="list">
      <button
        v-for="(im, i) in usable"
        :key="im.url"
        type="button"
        role="listitem"
        class="gallery__thumb"
        :class="{ 'is-current': im.url === current.url }"
        :aria-label="`사진 ${i + 1} 보기`"
        :aria-current="im.url === current.url ? 'true' : undefined"
        @click="index = i"
      >
        <img :src="im.url" alt="" loading="lazy" style="object-fit: contain; width: 100%; height: 100%" />
      </button>
    </div>
  </figure>
  <div v-else class="gallery__empty"><ImagePlaceholder :emoji="emoji" /></div>
</template>

<style scoped>
.gallery__frame,
.gallery__empty {
  aspect-ratio: 16 / 10;
  border-radius: 14px;
  overflow: hidden;
  background: var(--bg-subtle);
}
.gallery__caption {
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-muted);
}
.gallery__thumbs {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  overflow-x: auto;
}
.gallery__thumb {
  flex: none;
  width: 64px;
  height: 48px;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid transparent;
  background: var(--bg-subtle);
}
.gallery__thumb.is-current {
  border-color: var(--color-lantern-500);
}
</style>
