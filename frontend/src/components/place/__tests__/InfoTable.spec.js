import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import InfoTable from '../InfoTable.vue'

const hrefs = (w) => w.findAll('a').map((a) => a.attributes('href'))

describe('InfoTable', () => {
  test('javascript: homepage is shown as text, not a link', () => {
    const w = mount(InfoTable, { props: { place: { homepage: 'javascript:alert(1)', hours: '09:00' } } })
    expect(hrefs(w)).toEqual([])
    expect(w.text()).toContain('운영시간')
  })

  test('https homepage opens in new window', () => {
    const w = mount(InfoTable, { props: { place: { homepage: 'https://a.kr' } } })
    expect(w.find('a').attributes('target')).toBe('_blank')
  })

  test('tel takes the first number and sanitizes', () => {
    const w = mount(InfoTable, { props: { place: { phone: '055-749-5171, 055-749-5172' } } })
    expect(hrefs(w)).toEqual(['tel:055-749-5171'.replace(/-/g, '')])
  })

  test('phone without digits is not a link', () => {
    const w = mount(InfoTable, { props: { place: { phone: '문의 요망' } } })
    expect(hrefs(w)).toEqual([])
  })
})
