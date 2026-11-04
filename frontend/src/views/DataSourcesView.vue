<script setup>
import { computed, onMounted, ref } from 'vue'
import StateView from '../components/StateView.vue'
import { fetchReport } from '../api/places'
import { useMetaStore } from '../stores/meta'
import { categoryLabel } from '../utils/format'

const meta = useMetaStore()
const report = ref(null)
const loading = ref(true)
const error = ref(false)

async function load() {
  loading.value = true
  error.value = false
  try {
    const [r] = await Promise.all([fetchReport(), meta.load()])
    report.value = r
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)

// User-facing source summary (static copy; counts come from the report only).
const SOURCES = [
  { key: 'jinju_city.tourinfo', name: '진주시 OpenAPI · 관광지', provider: '진주시', use: '명소·관광지 기본 정보' },
  { key: 'jinju_city.restaurant', name: '진주시 OpenAPI · 음식점', provider: '진주시', use: '맛집 정보' },
  { key: 'jinju_city.festival', name: '진주시 OpenAPI · 축제', provider: '진주시', use: '축제·행사 일정' },
  { key: 'jinju_city.heritage', name: '진주시 OpenAPI · 문화재', provider: '진주시', use: '문화·역사 장소' },
  { key: 'jinju_city.lodging', name: '진주시 OpenAPI · 숙박', provider: '진주시', use: '숙박 시설' },
  { key: 'tourapi.area', name: '한국관광공사 TourAPI · 지역 관광정보', provider: '한국관광공사', use: '장소 상세·이미지·좌표 보강' },
  { key: 'tourapi.festival', name: '한국관광공사 TourAPI · 행사정보', provider: '한국관광공사', use: '축제·행사 보강' },
]
const STATUS_LABEL = { ok: '정상', error: '오류', skipped: '건너뜀', partial: '일부 실패' }

const sourceRows = computed(() => {
  const byKey = Object.fromEntries((report.value?.sources || []).map((s) => [s.source, s]))
  const rows = SOURCES.map((s) => ({ ...s, r: byKey[s.key] || null }))
  const known = new Set(SOURCES.map((s) => s.key))
  for (const s of report.value?.sources || []) {
    if (!known.has(s.source)) rows.push({ key: s.source, name: s.source, provider: '', use: '', r: s })
  }
  return rows
})

const droppedTotal = computed(() =>
  Object.values(report.value?.dropped || {}).reduce((a, b) => a + Number(b || 0), 0),
)
const cards = computed(() => {
  const r = report.value
  if (!r) return []
  return [
    { label: '정제 후', value: r.cleaned_count },
    { label: '제외', value: droppedTotal.value },
    { label: '병합된 쌍', value: r.merge?.pairs ?? 0 },
    { label: '최종 장소', value: r.final_count },
  ]
})
const categoryRows = computed(() =>
  Object.entries(report.value?.category_counts || {}).sort((a, b) => b[1] - a[1]),
)
const COMPLETENESS_LABEL = {
  hero_image: '대표 이미지',
  overview: '소개글',
  phone: '전화번호',
  hours: '운영시간',
  coords: '좌표',
}
const completenessRows = computed(() =>
  Object.entries(report.value?.completeness || {}).map(([k, v]) => ({
    key: k,
    label: COMPLETENESS_LABEL[k] || k,
    pct: Math.round(Number(v) * 100),
  })),
)
const MERGE_REASON = {
  same_name: '이름 동일',
  fuzzy_name: '이름 유사',
  same_phone: '전화번호 동일',
  same_name_addr: '이름·주소 동일',
  force_merge: '수동 지정',
}
const mergeReasons = computed(() =>
  Object.entries(report.value?.merge?.by_reason || {}).map(([k, v]) => ({ label: MERGE_REASON[k] || k, v })),
)
const DROP_REASON = { out_of_region: '진주 밖 좌표·주소' }
const dropRows = computed(() =>
  Object.entries(report.value?.dropped || {}).map(([k, v]) => ({ label: DROP_REASON[k] || k, v })),
)

const STEPS = [
  { t: '수집', s: '(병렬)' },
  { t: '원본 보존', s: '' },
  { t: '정제', s: '' },
  { t: '병합', s: '' },
  { t: '적재', s: '' },
  { t: '리포트', s: '' },
]

function fmtTime(iso) {
  const d = new Date(iso)
  if (!iso || Number.isNaN(d.getTime())) return ''
  return new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', dateStyle: 'medium', timeStyle: 'short' }).format(d)
}
</script>

<template>
  <section class="max-w-[1000px] mx-auto px-4 md:px-8 py-8 flex flex-col gap-8">
    <header>
      <h1 class="text-2xl font-extrabold text-strong">데이터 출처</h1>
      <p class="mt-2 text-[14px] text-body">
        진주허브의 장소 정보는 아래 공공 데이터를 정기적으로 수집·정제·병합해 만듭니다. 서비스는 실행 중에 외부
        API를 직접 호출하지 않고, 미리 만들어 둔 데이터만 사용합니다.
      </p>
      <p v-if="meta.data" class="mt-2 text-[13px] text-muted" data-test="meta-line">
        데이터 버전 <strong>{{ meta.data.data_version }}</strong>
        <span v-if="fmtTime(meta.data.generated_at)"> · 생성 {{ fmtTime(meta.data.generated_at) }}</span>
      </p>
    </header>

    <StateView :loading="loading" :error="error" error-message="리포트를 불러오지 못했습니다." @retry="load">
      <template v-if="report">
        <div>
          <h2 class="text-lg font-extrabold text-strong mb-3">수집 소스</h2>
          <div class="overflow-x-auto bg-card border border-border rounded-xl">
            <table class="w-full text-[13px] text-left">
              <thead class="bg-subtle text-muted">
                <tr>
                  <th class="px-3 py-2">소스</th>
                  <th class="px-3 py-2">제공</th>
                  <th class="px-3 py-2">용도</th>
                  <th class="px-3 py-2 text-right">수집 건수</th>
                  <th class="px-3 py-2">상태</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in sourceRows" :key="row.key" class="border-t border-border" data-test="source-row">
                  <td class="px-3 py-2 font-semibold text-strong">{{ row.name }}</td>
                  <td class="px-3 py-2">{{ row.provider }}</td>
                  <td class="px-3 py-2">{{ row.use }}</td>
                  <td class="px-3 py-2 text-right">{{ row.r ? Number(row.r.records).toLocaleString('ko-KR') : '-' }}</td>
                  <td class="px-3 py-2">
                    <span v-if="row.r" :class="row.r.status === 'ok' ? 'text-strong' : 'text-danger font-bold'">
                      {{ STATUS_LABEL[row.r.status] || row.r.status }}
                    </span>
                    <span v-else class="text-muted">기록 없음</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <h2 class="text-lg font-extrabold text-strong mb-3">처리 결과</h2>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div v-for="c in cards" :key="c.label" class="bg-card border border-border rounded-xl p-4" data-test="report-card">
              <div class="text-[12px] text-muted">{{ c.label }}</div>
              <div class="text-2xl font-extrabold text-strong">{{ Number(c.value).toLocaleString('ko-KR') }}</div>
            </div>
          </div>
          <div class="mt-3 grid md:grid-cols-2 gap-3 text-[13px] text-body">
            <div v-if="dropRows.length" class="bg-card border border-border rounded-xl p-4">
              <div class="font-bold text-strong mb-1">제외 사유</div>
              <ul>
                <li v-for="d in dropRows" :key="d.label">{{ d.label }}: {{ d.v }}건</li>
              </ul>
            </div>
            <div v-if="mergeReasons.length" class="bg-card border border-border rounded-xl p-4">
              <div class="font-bold text-strong mb-1">병합 사유</div>
              <ul>
                <li v-for="m in mergeReasons" :key="m.label">{{ m.label }}: {{ m.v }}쌍</li>
              </ul>
            </div>
          </div>
        </div>

        <div class="grid md:grid-cols-2 gap-6">
          <div>
            <h2 class="text-lg font-extrabold text-strong mb-3">카테고리별 장소</h2>
            <ul class="bg-card border border-border rounded-xl divide-y divide-border text-[14px]">
              <li v-for="[code, n] in categoryRows" :key="code" class="flex justify-between px-4 py-2" data-test="category-row">
                <span>{{ categoryLabel(code) }}</span>
                <span class="font-bold text-strong">{{ Number(n).toLocaleString('ko-KR') }}</span>
              </li>
            </ul>
          </div>
          <div>
            <h2 class="text-lg font-extrabold text-strong mb-3">정보 보유율</h2>
            <ul class="bg-card border border-border rounded-xl p-4 flex flex-col gap-3 text-[13px]">
              <li v-for="c in completenessRows" :key="c.key" data-test="completeness-row">
                <div class="flex justify-between mb-1">
                  <span>{{ c.label }}</span><span class="font-bold text-strong">{{ c.pct }}%</span>
                </div>
                <div
                  class="h-2 rounded-full bg-subtle overflow-hidden"
                  role="progressbar"
                  :aria-valuenow="c.pct"
                  aria-valuemin="0"
                  aria-valuemax="100"
                  :aria-label="`${c.label} 보유율`"
                >
                  <div class="h-full bg-primary" :style="{ width: `${c.pct}%` }"></div>
                </div>
              </li>
            </ul>
            <p class="mt-2 text-[12px] text-muted">장소 중 해당 정보를 가진 비율입니다. 원본에 없는 정보는 비워 둡니다.</p>
          </div>
        </div>

        <p v-if="fmtTime(report.generated_at)" class="text-[12px] text-muted">
          리포트 생성 {{ fmtTime(report.generated_at) }}
        </p>
      </template>
    </StateView>

    <div>
      <h2 class="text-lg font-extrabold text-strong mb-3">파이프라인 동작 방식</h2>
      <div class="bg-card border border-border rounded-xl p-3 overflow-x-auto">
        <svg
          viewBox="0 0 900 120"
          class="w-full min-w-[640px] h-auto"
          role="img"
          aria-labelledby="pipe-title"
          data-test="pipeline-svg"
        >
          <title id="pipe-title">수집(병렬), 원본 보존, 정제, 병합, 적재, 리포트 순서의 데이터 파이프라인</title>
          <defs>
            <marker id="pipe-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0 0 L10 5 L0 10 z" fill="#1d4ed8" />
            </marker>
          </defs>
          <g v-for="(st, i) in STEPS" :key="st.t">
            <rect :x="10 + i * 148" y="30" width="118" height="60" rx="10" fill="#eff6ff" stroke="#1d4ed8" stroke-width="1.5" />
            <text :x="69 + i * 148" :y="st.s ? 56 : 66" text-anchor="middle" font-size="16" font-weight="700" fill="#111827">{{ st.t }}</text>
            <text v-if="st.s" :x="69 + i * 148" y="76" text-anchor="middle" font-size="13" fill="#374151">{{ st.s }}</text>
            <line
              v-if="i < STEPS.length - 1"
              :x1="128 + i * 148"
              y1="60"
              :x2="156 + i * 148"
              y2="60"
              stroke="#1d4ed8"
              stroke-width="2"
              marker-end="url(#pipe-arrow)"
            />
          </g>
        </svg>
      </div>
      <ol class="mt-3 text-[13px] text-body list-decimal pl-5 flex flex-col gap-1">
        <li><strong>수집(병렬)</strong>: 진주시·한국관광공사 API에서 여러 소스를 동시에 가져옵니다.</li>
        <li><strong>원본 보존</strong>: 받은 응답을 가공하지 않고 그대로 저장해 언제든 다시 처리할 수 있게 합니다.</li>
        <li><strong>정제</strong>: 형식을 통일하고 진주 밖 데이터와 잘못된 좌표를 걸러냅니다.</li>
        <li><strong>병합</strong>: 이름·전화번호·주소가 같은 장소를 하나로 합쳐 중복을 줄입니다.</li>
        <li><strong>적재</strong>: 검색에 쓰는 장소 데이터베이스로 만듭니다.</li>
        <li><strong>리포트</strong>: 위의 건수와 보유율을 기록해 이 페이지에 보여줍니다.</li>
      </ol>
    </div>

    <div class="bg-subtle border border-border rounded-xl p-4 text-[13px] text-body flex flex-col gap-1">
      <h2 class="text-base font-extrabold text-strong">라이선스 및 이용 안내</h2>
      <p>장소 정보 출처: {{ meta.data?.attribution || '한국관광공사 TourAPI · 진주시 공공데이터' }}</p>
      <p>이미지는 원본 제공처의 라이선스에 따르며, 각 이미지에 출처를 표기합니다.</p>
      <p>지도 © OpenStreetMap contributors © CARTO</p>
      <p>날씨 정보: 기상청 단기예보. 챗봇 답변은 위 데이터를 바탕으로 하며 실제와 다를 수 있으니 방문 전 운영 여부를 확인해 주세요.</p>
    </div>
  </section>
</template>
