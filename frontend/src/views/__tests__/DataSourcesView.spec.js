import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

vi.mock('../../api/places', () => ({ fetchReport: vi.fn(), fetchMeta: vi.fn() }))
import DataSourcesView from '../DataSourcesView.vue'
import { fetchReport, fetchMeta } from '../../api/places'

const report = {
  sources: [{ source: 'jinju_city.tourinfo', status: 'ok', records: 12, calls: 2, error: null }],
  cleaned_count: 40,
  dropped: { out_of_region: 2 },
  merge: { pairs: 3, by_reason: { same_name: 3 } },
  final_count: 35,
  category_counts: { food: 20, sight: 15 },
  completeness: { hero_image: 0.5, overview: 0.25, phone: 1, hours: 0, coords: 0.8 },
  generated_at: '2026-11-04T12:59:47+09:00',
}

describe('DataSourcesView', () => {
  beforeEach(() => vi.clearAllMocks())

  test('renders report numbers, diagram and meta from API', async () => {
    fetchReport.mockResolvedValue(report)
    fetchMeta.mockResolvedValue({ data_version: 'v-test', generated_at: report.generated_at, attribution: '출처문구' })
    const w = mount(DataSourcesView)
    await flushPromises()
    expect(w.findAll('[data-test="report-card"]')).toHaveLength(4)
    expect(w.text()).toContain('35')
    expect(w.text()).toContain('v-test')
    expect(w.text()).toContain('출처문구')
    expect(w.findAll('[data-test="category-row"]')).toHaveLength(2)
    expect(w.findAll('[data-test="completeness-row"]')).toHaveLength(5)
    expect(w.find('[data-test="pipeline-svg"]').text()).toContain('원본 보존')
  })

  test('shows error state when report fails', async () => {
    fetchReport.mockRejectedValue(new Error('x'))
    fetchMeta.mockResolvedValue({ data_version: 'v', generated_at: '' })
    const w = mount(DataSourcesView)
    await flushPromises()
    expect(w.text()).toContain('리포트를 불러오지 못했습니다')
  })
})
