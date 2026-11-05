<script setup>
import { sourceLabel } from '../utils/constants'
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchPlace } from '../api/places'
import { useLanternsStore } from '../stores/lanterns'
import { categoryLabel, safeUrl } from '../utils/format'
import StateView from '../components/StateView.vue'
import ImageGallery from '../components/place/ImageGallery.vue'
import InfoTable from '../components/place/InfoTable.vue'
import NearbyList from '../components/place/NearbyList.vue'
import LanternButton from '../components/place/LanternButton.vue'
import CheckInButton from '../components/place/CheckInButton.vue'

// Leaflet stays out of the main bundle.
const MiniMap = defineAsyncComponent(() => import('../components/place/MiniMap.vue'))

const route = useRoute()
const router = useRouter()
const lanterns = useLanternsStore()

const place = ref(null)
const loading = ref(true)
const error = ref(false)
const notFound = ref(false)
let seq = 0

const id = computed(() => String(route.params.id ?? ''))
const savedSnapshot = computed(() => lanterns.items[id.value] || null)
const hasCoords = computed(() => place.value && Number.isFinite(place.value.lat) && Number.isFinite(place.value.lng))
const badge = computed(() => {
  const p = place.value
  if (!p) return ''
  if (p.jinju8_rank) return `진주8경 ${p.jinju8_rank}`
  if (p.is_collection) return '유등 30선'
  return ''
})
const sources = computed(() => (place.value?.sources || []).map((s) => ({ ...s, href: safeUrl(s.source_url) })).filter((s) => s.href))

async function load() {
  const mine = ++seq
  if (route.name !== 'place' || !id.value) {
    loading.value = false
    return
  }
  // Already showing this place (e.g. after the alias replace below): nothing to fetch.
  if (place.value && place.value.id === id.value) {
    loading.value = false
    return
  }
  loading.value = true
  error.value = false
  notFound.value = false
  place.value = null
  const requested = id.value
  try {
    const data = await fetchPlace(requested)
    if (mine !== seq) return
    if (data.canonical_id && data.canonical_id !== requested) {
      lanterns.migrateId(requested, data.canonical_id)
      place.value = data
      loading.value = false
      await router.replace({ name: 'place', params: { id: data.canonical_id } })
      return
    }
    place.value = data
  } catch (e) {
    if (mine !== seq) return
    if (e?.response?.status === 404) notFound.value = true
    else error.value = true
  } finally {
    if (mine === seq) loading.value = false
  }
}

watch([id, () => route.name], load, { immediate: true })

function removeTombstone() {
  lanterns.unsave(id.value)
}
</script>

<template>
  <section class="max-w-[1200px] mx-auto px-4 md:px-8 py-6 md:py-10">
    <div v-if="notFound" class="py-16 text-center">
      <span class="text-4xl opacity-60" aria-hidden="true">🏮</span>
      <h1 class="mt-3 text-xl font-extrabold text-strong">더 이상 제공되지 않는 장소예요</h1>
      <p class="mt-2 text-muted text-[14px]">데이터가 갱신되면서 이 장소가 목록에서 사라졌을 수 있어요.</p>
      <div v-if="savedSnapshot" class="mt-5 inline-flex flex-col items-center gap-3 rounded-xl border border-border p-4">
        <p class="text-[15px]">
          담아 두었던 장소: <strong>{{ savedSnapshot.title }}</strong>
        </p>
        <button type="button" class="px-4 py-2 rounded-lg bg-subtle font-bold" @click="removeTombstone">
          목록에서 빼기
        </button>
      </div>
      <p class="mt-6">
        <router-link :to="{ name: 'explore' }" class="underline font-bold">지도에서 다른 장소 찾기</router-link>
      </p>
    </div>

    <StateView
      v-else
      :loading="loading"
      :error="error"
      error-message="장소 정보를 불러오지 못했어요."
      @retry="load"
    >
      <article v-if="place" class="grid gap-8 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div class="min-w-0">
          <ImageGallery :images="place.images || []" />
        </div>

        <div class="min-w-0 flex flex-col gap-5">
          <header>
            <div class="flex items-center gap-2 text-[13px] font-bold">
              <span class="px-2.5 py-0.5 rounded-full bg-subtle">{{ categoryLabel(place.category) }}</span>
              <span v-if="badge" class="px-2.5 py-0.5 rounded-full bg-night-900 text-lantern-500">◆ {{ badge }}</span>
            </div>
            <h1 class="mt-2 text-2xl font-extrabold text-strong">{{ place.title }}</h1>
            <p v-if="place.addr" class="mt-1 text-[14px] text-muted">{{ place.addr }}</p>
            <p v-if="place.summary" class="mt-3 text-[15px]">{{ place.summary }}</p>
          </header>

          <div class="flex flex-col gap-3">
            <div class="flex flex-wrap gap-2">
              <LanternButton :place="place" />
            </div>
            <CheckInButton :place="place" />
          </div>

          <InfoTable :place="place" />
        </div>

        <div class="lg:col-span-2 min-w-0 flex flex-col gap-8">
          <p v-if="place.overview" class="text-[15px] leading-relaxed whitespace-pre-line">{{ place.overview }}</p>

          <div v-if="hasCoords">
            <h2 class="mb-2 text-lg font-extrabold text-strong">위치</h2>
            <MiniMap :lat="place.lat" :lng="place.lng" :title="place.title" />
          </div>

          <div v-if="place.nearby && place.nearby.length">
            <h2 class="mb-2 text-lg font-extrabold text-strong">근처 가볼 만한 곳</h2>
            <NearbyList :items="place.nearby" />
          </div>

          <footer class="text-[12px] text-muted">
            <p>출처: 한국관광공사 TourAPI · 진주시 공공데이터</p>
            <ul v-if="sources.length" class="mt-1 flex flex-wrap gap-x-3">
              <li v-for="s in sources" :key="s.source + s.source_url">
                <a :href="s.href" target="_blank" rel="noopener noreferrer" class="underline">{{ sourceLabel(s.source) }} 원문</a>
              </li>
            </ul>
          </footer>
        </div>
      </article>
    </StateView>
  </section>
</template>
