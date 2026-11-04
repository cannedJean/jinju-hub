<script setup>
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchPlace } from '../api/places'
import { useLanternsStore } from '../stores/lanterns'
import { useCollectionStore } from '../stores/collection'
import { decodeShare } from '../utils/share'
import SavedList from '../components/lanterns/SavedList.vue'
import BadgeShelf from '../components/lanterns/BadgeShelf.vue'
import ShareDialog from '../components/lanterns/ShareDialog.vue'

const LanternMap = defineAsyncComponent(() => import('../components/lanterns/LanternMap.vue'))

const route = useRoute()
const router = useRouter()
const lanterns = useLanternsStore()
const collection = useCollectionStore()

const tab = ref('list')
const shareOpen = ref(false)
const missing = ref(new Set())
const checked = new Set()

const sharedIds = computed(() => (typeof route.query.share === 'string' ? decodeShare(route.query.share) : []))
const isShared = computed(() => typeof route.query.share === 'string')
const sharedItems = ref([])
const sharedFailed = ref(0)
const sharedLoading = ref(false)

const items = computed(() => (isShared.value ? sharedItems.value : lanterns.savedList))
const activeMissing = computed(() => (isShared.value ? new Set() : missing.value))

collection.load().catch(() => {})

// Check each saved place once: 404 -> tombstone; merged/renamed id -> migrate the snapshot.
async function verify(list) {
  await Promise.all(
    list.map(async (it) => {
      if (checked.has(it.id)) return
      checked.add(it.id)
      try {
        const p = await fetchPlace(it.id)
        const canonical = p?.canonical_id || p?.id
        if (canonical && canonical !== it.id) lanterns.migrateId(it.id, canonical)
      } catch (e) {
        if (e?.response?.status === 404) missing.value = new Set([...missing.value, it.id])
      }
    }),
  )
}

watch(
  () => (isShared.value ? '' : lanterns.savedList.map((it) => it.id).join(',')),
  () => {
    if (!isShared.value) verify(lanterns.savedList)
  },
  { immediate: true },
)

async function loadShared() {
  sharedLoading.value = true
  const ids = sharedIds.value
  const results = await Promise.allSettled(ids.map((id) => fetchPlace(id)))
  sharedItems.value = results
    .map((r, i) => (r.status === 'fulfilled' && r.value ? { ...r.value, id: r.value.id || ids[i] } : null))
    .filter(Boolean)
    .map((p) => ({ id: p.id, title: p.title, category: p.category, tags: p.tags, lat: p.lat, lng: p.lng }))
  sharedFailed.value = ids.length - sharedItems.value.length
  sharedLoading.value = false
}

watch(
  () => route.query.share,
  () => {
    if (isShared.value) loadShared()
  },
  { immediate: true },
)

function importAll() {
  const byId = Object.fromEntries(sharedItems.value.map((s) => [s.id, s]))
  lanterns.importShared(Object.keys(byId), byId)
  router.push({ name: 'lanterns' })
}

const total = computed(() => collection.collectionIds.length || 30)
const savedCount = computed(() => lanterns.savedList.length)
const badges = computed(() => collection.evaluated)
const TABS = [
  { id: 'list', label: '목록' },
  { id: 'map', label: '지도' },
]
</script>

<template>
  <section class="max-w-[1200px] mx-auto px-4 md:px-8 py-8">
    <div v-if="!lanterns.storageAvailable" class="notice" role="alert">
      이 브라우저에서는 담은 목록이 저장되지 않아요(사생활 보호 모드)
    </div>

    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-extrabold text-strong">내 유등</h1>
      <button v-if="!isShared && savedCount" type="button" class="btn" @click="shareOpen = true">공유</button>
    </div>

    <div v-if="isShared" class="notice notice--info" role="status">
      <p class="font-extrabold">공유받은 목록</p>
      <p class="text-[13px]">읽기 전용이에요. 마음에 들면 내 목록에 가져올 수 있어요.</p>
      <p v-if="sharedFailed" class="text-[13px]">{{ sharedFailed }}곳은 불러오지 못해 건너뛰었어요.</p>
      <button type="button" class="btn btn--primary mt-2" :disabled="!sharedItems.length" @click="importAll">
        내 목록에 가져오기
      </button>
    </div>
    <p v-else class="mt-2 text-[15px] text-body">
      담음 {{ savedCount }} · 밝힘 {{ lanterns.litCount }} · 유등 30선 ◆ {{ collection.progress }}/{{ total }}
    </p>

    <div class="mt-5 flex gap-2" role="tablist" aria-label="보기 방식">
      <button
        v-for="t in TABS"
        :key="t.id"
        type="button"
        role="tab"
        :aria-selected="String(tab === t.id)"
        class="tab"
        :class="{ 'tab--on': tab === t.id }"
        @click="tab = t.id"
      >
        {{ t.label }}
      </button>
    </div>

    <div class="mt-4">
      <p v-if="isShared && sharedLoading" class="text-muted" aria-live="polite">불러오는 중...</p>
      <p v-else-if="!items.length" class="py-10 text-center text-muted">
        {{ isShared ? '표시할 장소가 없어요.' : '아직 담은 장소가 없어요. 탐색에서 마음에 드는 곳을 담아 보세요.' }}
      </p>
      <SavedList
        v-else-if="tab === 'list'"
        :items="items"
        :missing="activeMissing"
        :readonly="isShared"
        @remove="lanterns.unsave"
      />
      <LanternMap v-else :items="items" :missing="activeMissing" />
    </div>

    <template v-if="!isShared">
      <h2 class="mt-10 mb-3 text-lg font-extrabold text-strong">배지 진열장</h2>
      <BadgeShelf :badges="badges" />
    </template>

    <ShareDialog v-if="shareOpen" :ids="lanterns.savedList.map((it) => it.id)" @close="shareOpen = false" />
  </section>
</template>

<style scoped>
.notice {
  margin-bottom: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #fef2f2;
  color: #991b1b;
  font-size: 14px;
  font-weight: 700;
}
.notice--info {
  margin-top: 12px;
  background: #fffbeb;
  color: var(--color-night-900);
  border: 1px solid var(--color-lantern-500);
}
.btn {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  font-weight: 700;
}
.btn--primary {
  background: var(--color-night-900);
  border-color: var(--color-night-900);
  color: #fff;
}
.btn:disabled {
  opacity: 0.5;
}
.tab {
  min-height: 40px;
  padding: 0 18px;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  font-weight: 700;
}
.tab--on {
  background: var(--color-night-900);
  border-color: var(--color-night-900);
  color: #fff;
}
</style>
