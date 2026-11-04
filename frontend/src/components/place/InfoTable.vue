<script setup>
import { computed } from 'vue'
import { formatDateRange, safeUrl, telHref } from '../../utils/format'

const props = defineProps({ place: { type: Object, required: true } })

const rows = computed(() => {
  const p = props.place
  const period = p.date_undecided ? '일정 미정' : formatDateRange(p.start_date, p.end_date)
  const list = [
    { key: 'hours', label: '운영시간', value: p.hours },
    { key: 'closed', label: '휴무', value: p.closed_days },
    { key: 'fee', label: '요금', value: p.fee },
    { key: 'parking', label: '주차', value: p.parking },
    { key: 'phone', label: '전화', value: p.phone, href: telHref(p.phone) },
    { key: 'home', label: '홈페이지', value: p.homepage, href: safeUrl(p.homepage), external: true },
    { key: 'menu', label: '메뉴', value: p.menu },
    { key: 'period', label: '기간', value: period },
  ]
  return list.filter((r) => r.value && String(r.value).trim())
})
</script>

<template>
  <div v-if="rows.length">
    <dl>
      <div v-for="r in rows" :key="r.key" class="info__row">
        <dt>{{ r.label }}</dt>
        <dd>
          <a
            v-if="r.href"
            :href="r.href"
            :target="r.external ? '_blank' : undefined"
            :rel="r.external ? 'noopener noreferrer' : undefined"
            >{{ r.value }}</a
          >
          <span v-else class="whitespace-pre-line">{{ r.value }}</span>
        </dd>
      </div>
    </dl>
    <p class="mt-2 text-[12px] text-muted">방문 전 운영 정보를 확인하세요.</p>
  </div>
</template>

<style scoped>
.info__row {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border);
  font-size: 14px;
}
dt {
  flex: none;
  width: 72px;
  font-weight: 700;
  color: var(--color-muted);
}
dd {
  min-width: 0;
  overflow-wrap: anywhere;
}
a {
  color: var(--color-night-700);
  text-decoration: underline;
}
</style>
