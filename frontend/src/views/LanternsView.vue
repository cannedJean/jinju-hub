<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchPlace } from '../api/places'
import { useLanternsStore } from '../stores/lanterns'
import { useCollectionStore } from '../stores/collection'
import { useMarkersStore } from '../stores/markers'
import { decodeShare } from '../utils/share'
import SavedList from '../components/lanterns/SavedList.vue'
import BadgeShelf from '../components/lanterns/BadgeShelf.vue'
import ShareDialog from '../components/lanterns/ShareDialog.vue'

const LanternMap = defineAsyncComponent(() => import('../components/lanterns/LanternMap.vue'))

const route = useRoute()
const router = useRouter()
const lanterns = useLanternsStore()
const collection = useCollectionStore()
const markers = useMarkersStore()

const CHECK_CONCURRENCY = 4
const UNDO_MS = 5000

const tab = ref('list')
const shareOpen = ref(false)
const missing = ref(new Set())
const checked = new Set()

const sharedIds = computed(() => (typeof route.query.share === 'string' ? decodeShare(route.query.share) : []))
const isShared = computed(() => typeof route.query.share === 'string')
const sharedItems = ref([])
const sharedFailed = ref(0)
const sharedLoading = ref(false)
const sharedError = computed(() => !sharedLoading.value && sharedIds.value.length > 0 && sharedFailed.value === sharedIds.value.length)

const items = computed(() => (isShared.value ? sharedItems.value : lanterns.savedList))
const activeMissing = computed(() => (isShared.value ? new Set() : missing.value))

const collectionError = ref(false)
async function loadCollection() {
  collectionError.value = false
  try {
    await collection.load()
    collection.checkBadges()
  } catch {
    collectionError.value = true
  }
}
loadCollection()

// Tombstone check: ids present in the (cached) marker list are alive; the rest are looked up
// one by one with a small concurrency cap. 404 -> tombstone; merged id -> migrate the snapshot;
// any other failure is forgotten so a later visit retries.
async function verify(list) {
  const todo = list.filter((it) => !checked.has(it.id))
  todo.forEach((it) => checked.add(it.id))
  if (!todo.length) return
  let alive = new Map()
  try {
    await markers.load()
    alive = markers.byId
  } catch {
    // fall back to per-place lookups
  }
  const rest = todo.filter((it) => !alive.has(it.id))
  let next = 0
  async function worker() {
    while (next < rest.length) {
      const it = rest[next++]
      try {
        const p = await fetchPlace(it.id)
        const canonical = p?.canonical_id || p?.id
        if (canonical && canonical !== it.id) lanterns.migrateId(it.id, canonical)
      } catch (e) {
        if (e?.response?.status === 404) missing.value = new Set([...missing.value, it.id])
        else checked.delete(it.id)
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(CHECK_CONCURRENCY, rest.length) }, worker))
}

watch(
  () => (isShared.value ? '' : lanterns.savedList.map((it) => it.id).join(',')),
  () => {
    if (!isShared.value) verify(lanterns.savedList)
  },
  { immediate: true },
)

let sharedToken = 0
async function loadShared() {
  const token = ++sharedToken
  sharedLoading.value = true
  const ids = sharedIds.value
  const results = await Promise.allSettled(ids.map((id) => fetchPlace(id)))
  if (token !== sharedToken) return
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

// Undo for removals: keep the full snapshot (incl. lit fields) for a few seconds.
const undo = ref(null)
let undoTimer = null
function removeItem(id) {
  const snap = lanterns.items[id] ? { ...lanterns.items[id] } : null
  lanterns.unsave(id)
  if (!snap) return
  clearTimeout(undoTimer)
  undo.value = snap
  undoTimer = setTimeout(() => (undo.value = null), UNDO_MS)
}
function undoRemove() {
  if (!undo.value) return
  lanterns.restore(undo.value)
  clearTimeout(undoTimer)
  undo.value = null
}
onBeforeUnmount(() => clearTimeout(undoTimer))

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
      <p v-else-if="isShared && sharedError" class="py-10 text-center text-muted" role="alert">
        공유받은 목록을 불러오지 못했어요.
        <button type="button" class="btn ml-2" @click="loadShared">다시 시도</button>
      </p>
      <p v-else-if="!items.length" class="py-10 text-center text-muted">
        {{ isShared ? '표시할 장소가 없어요.' : '아직 담은 장소가 없어요. 탐색에서 마음에 드는 곳을 담아 보세요.' }}
      </p>
      <SavedList
        v-else-if="tab === 'list'"
        :items="items"
        :missing="activeMissing"
        :readonly="isShared"
        @remove="removeItem"
      />
      <LanternMap v-else :items="items" :missing="activeMissing" />
    </div>

    <template v-if="!isShared">
      <h2 class="mt-10 mb-3 text-lg font-extrabold text-strong">배지 진열장</h2>
      <div v-if="collectionError" class="notice" role="alert">
        배지 정보를 불러오지 못했어요
        <button type="button" class="btn ml-2" @click="loadCollection">다시 시도</button>
      </div>
      <BadgeShelf v-else :badges="badges" />
    </template>

    <div v-if="undo" class="undo" role="status">
      <span>{{ undo.title }} 빼기 완료</span>
      <button type="button" class="undo__btn" @click="undoRemove">실행 취소</button>
    </div>

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
.undo {
  position: fixed;
  left: 50%;
  bottom: 88px;
  transform: translateX(-50%);
  z-index: 250;
  width: max-content;
  max-width: calc(100vw - 32px);
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 16px;
  border-radius: 999px;
  background: var(--color-night-900);
  color: #fff;
  font-weight: 700;
  font-size: 14px;
}
.undo__btn {
  color: var(--color-lantern-500);
  font-weight: 800;
}
/* Mobile: clear the tab bar and the chat bubble above it (ChatWidget bottom 72px + 64px). */
@media (max-width: 767px) {
  .undo {
    bottom: 148px;
  }
}
</style>
