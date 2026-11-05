import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

vi.mock('../../api/places', () => ({ fetchReport: vi.fn(), fetchMeta: vi.fn() }))
import DataSourcesView from '../../views/DataSourcesView.vue'
import { fetchReport, fetchMeta } from '../../api/places'

const report = {
  sources: [
    { source: 'jinju_city.tourinfo', status: 'ok', records: 12, calls: 2, error: null },
    { source: 'tourapi.area', status: 'skipped', records: 0, calls: 0, error: null },
    { source: 'jinju_city.restaurant', status: 'failed', records: 0, calls: 1, error: 'network error' },
  ],
  cleaned_count: 40,
  dropped: { out_of_region: 2 },
  merge: { pairs: 3, by_reason: { same_name: 3 } },
  final_count: 35,
  category_counts: { food: 20, sight: 15 },
  completeness: { hero_image: 0.5, overview: 0.25, phone: 1, hours: 0, coords: 0.8 },
  generated_at: '2026-11-04T12:59:47+09:00',
}

describe('U12 - DataSourcesView skipped status localized mapping', () => {
  beforeEach(() => vi.clearAllMocks())

  test('maps skipped backend source status to localized label "건너뜀" and applies non-danger styling', async () => {
    fetchReport.mockResolvedValue(report)
    fetchMeta.mockResolvedValue({ data_version: 'v', generated_at: report.generated_at })
    const w = mount(DataSourcesView)
    await flushPromises()

    const text = w.text()
    expect(text).toContain('건너뜀')
    expect(text).not.toContain('skipped')

    // Find the row for tourapi.area (which has status 'skipped')
    const rows = w.findAll('[data-test="source-row"]')
    const skippedRow = rows.find((r) => r.text().includes('한국관광공사 지역 관광정보') || r.text().includes('건너뜀'))
    expect(skippedRow).toBeDefined()

    const statusBadge = skippedRow?.find('td:last-child span')
    expect(statusBadge?.text()).toBe('건너뜀')
    // skipped should not be styled as red danger error
    expect(statusBadge?.classes()).not.toContain('text-danger')
    expect(statusBadge?.classes()).toContain('text-muted')

    w.unmount()
  })
})
