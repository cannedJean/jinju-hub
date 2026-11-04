<script setup>
import { computed, ref } from 'vue'
import { canLight, getPosition } from '../../utils/checkin'
import { formatDistance } from '../../utils/format'
import { useLanternsStore } from '../../stores/lanterns'
import { useCollectionStore } from '../../stores/collection'

const props = defineProps({ place: { type: Object, required: true } })
const emit = defineEmits(['lit'])

const lanterns = useLanternsStore()
const collection = useCollectionStore()

const busy = ref(false)
const message = ref('')

const demo = computed(() => lanterns.demo.enabled)
const lit = computed(() => lanterns.isLit(props.place.id))

async function afterLight() {
  // Badges need the collection definition; a failed load must not undo the lighting.
  try {
    await collection.load()
    collection.checkBadges()
  } catch {
    // badges are re-checked the next time the collection loads
  }
  emit('lit', props.place.id)
}

function rejectMessage(result) {
  if (result.reason === 'too_far') return `아직 ${formatDistance(result.distance)} 떨어져 있어요`
  if (result.reason === 'low_accuracy') return '위치 정확도가 낮아요. 잠시 후 다시 시도해 주세요'
  return '이 장소의 위치 정보가 없어 점등할 수 없어요'
}

function positionErrorMessage(e) {
  if (e?.message === 'permission_denied') return '위치 권한이 필요해요. 브라우저 설정에서 허용해 주세요'
  if (e?.message === 'unsupported') return '이 브라우저에서는 위치 확인을 지원하지 않아요'
  return '현재 위치를 확인하지 못했어요. 잠시 후 다시 시도해 주세요'
}

async function checkIn() {
  if (busy.value || lit.value) return
  busy.value = true
  message.value = ''
  try {
    const id = props.place.id
    if (demo.value) {
      const pos = lanterns.demo.pos
      if (pos) {
        const result = canLight(props.place, { lat: pos.lat, lng: pos.lng, accuracy: 0 })
        if (!result.ok) {
          message.value = rejectMessage(result)
          return
        }
      }
      lanterns.light(id, 'demo', props.place)
      await afterLight()
      return
    }
    let pos
    try {
      pos = await getPosition()
    } catch (e) {
      message.value = positionErrorMessage(e)
      return
    }
    const result = canLight(props.place, pos)
    if (!result.ok) {
      message.value = rejectMessage(result)
      return
    }
    lanterns.light(id, 'gps', props.place)
    await afterLight()
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="checkin">
    <p v-if="lit" class="checkin__done">◆ 이곳의 유등을 밝혔어요</p>
    <template v-else>
      <button type="button" class="checkin__btn" :disabled="busy" @click="checkIn">
        {{ demo ? '도착 시뮬레이션' : '도착했어요' }}
      </button>
      <span v-if="demo" class="checkin__badge">시연 모드</span>
    </template>
    <p v-if="message" class="checkin__msg" role="alert">{{ message }}</p>
  </div>
</template>

<style scoped>
.checkin {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.checkin__btn {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 12px;
  background: var(--color-night-900);
  color: #fff;
  font-weight: 800;
  font-size: 14px;
}
.checkin__btn:disabled {
  opacity: 0.6;
}
.checkin__badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--color-lantern-500);
  color: var(--color-night-900);
  font-size: 12px;
  font-weight: 800;
}
.checkin__done {
  font-weight: 800;
  color: #b45309;
}
.checkin__msg {
  flex-basis: 100%;
  font-size: 13px;
  color: #b91c1c;
}
</style>
