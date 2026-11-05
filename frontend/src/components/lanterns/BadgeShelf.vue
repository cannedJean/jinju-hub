<script setup>
// Badge shelf: one card per evaluated badge ({id,label,description,required,progress,earned}).
defineProps({ badges: { type: Array, default: () => [] } })
const req = (b) => Math.max(1, Number(b.required) || 1)
const cur = (b) => Math.min(Math.max(0, b.progress || 0), req(b))

const BADGE_ICONS = {
  first_light: '🏮',
  jinju8: '🏰',
  food_explorer: '🥢',
  history_walk: '📜',
  night_namgang: '🌙',
  festival_guest: '🎆',
}
const badgeIcon = (b) => BADGE_ICONS[b.id] || (b.earned ? '🏆' : '✨')
</script>

<template>
  <ul class="badge-shelf" aria-label="배지 진열장">
    <li
      v-for="b in badges"
      :key="b.id"
      class="badge"
      :class="{ 'badge--earned': b.earned }"
      :data-earned="String(b.earned)"
    >
      <span class="badge__icon" aria-hidden="true">{{ badgeIcon(b) }}</span>
      <div class="min-w-0 flex-1">
        <p class="badge__label">
          {{ b.label }}
          <span v-if="b.earned" class="badge__tag">획득</span>
        </p>
        <p v-if="b.description" class="badge__desc">{{ b.description }}</p>
        <div
          class="badge__bar"
          role="progressbar"
          :aria-label="`${b.label} 진행도`"
          aria-valuemin="0"
          :aria-valuemax="req(b)"
          :aria-valuenow="cur(b)"
        >
          <span class="badge__fill" :style="{ width: `${(cur(b) / req(b)) * 100}%` }"></span>
        </div>
        <p class="badge__count">{{ cur(b) }}/{{ req(b) }}</p>
      </div>
    </li>
  </ul>
</template>

<style scoped>
.badge-shelf {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
}
.badge {
  display: flex;
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
}
.badge__icon {
  flex: none;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: var(--bg-subtle);
  color: var(--color-muted);
  filter: grayscale(0.8);
  opacity: 0.6;
}
.badge--earned {
  border-color: var(--color-lantern-500);
}
.badge--earned .badge__icon {
  background: var(--color-lantern-500);
  color: var(--color-night-900);
  box-shadow: 0 0 12px var(--color-lantern-glow);
  filter: none;
  opacity: 1;
}
.badge__label {
  font-weight: 800;
  font-size: 15px;
}
.badge__tag {
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--color-night-900);
  color: var(--color-lantern-500);
  font-size: 11px;
}
.badge__desc {
  font-size: 13px;
  color: var(--color-muted);
}
.badge__bar {
  margin-top: 8px;
  height: 6px;
  border-radius: 999px;
  background: var(--bg-subtle);
  overflow: hidden;
}
.badge__fill {
  display: block;
  height: 100%;
  background: var(--color-lantern-500);
}
.badge__count {
  margin-top: 4px;
  font-size: 12px;
  font-weight: 700;
  color: var(--color-muted);
}
</style>
