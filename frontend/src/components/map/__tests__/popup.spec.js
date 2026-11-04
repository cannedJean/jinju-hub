import { describe, expect, test, vi } from 'vitest'
import { buildPopup } from '../popup'

const M = { id: 'jh-1', title: '<img src=x onerror=alert(1)>촉석루', category: 'sight', lat: 35.19, lng: 128.08 }

describe('buildPopup', () => {
  test('renders place text with textContent only', () => {
    const el = buildPopup(M, { distanceText: '650m', saved: false })
    expect(el.querySelector('img')).toBeNull()
    expect(el.querySelector('.map-popup__title').textContent).toBe(M.title)
    expect(el.textContent).toContain('명소')
    expect(el.textContent).toContain('650m')
    expect(el.querySelector('a').getAttribute('href')).toBe('/places/jh-1')
  })

  test('save button toggles label and calls back', () => {
    const onToggleSave = vi.fn()
    const el = buildPopup(M, { saved: false, onToggleSave })
    const btn = el.querySelector('button')
    expect(btn.getAttribute('aria-pressed')).toBe('false')
    btn.click()
    expect(onToggleSave).toHaveBeenCalledWith('jh-1')
    expect(btn.getAttribute('aria-pressed')).toBe('true')
    expect(btn.textContent).toContain('담음')
  })

  test('detail link calls onOpen instead of navigating', () => {
    const onOpen = vi.fn()
    const el = buildPopup(M, { onOpen })
    const ev = new MouseEvent('click', { bubbles: true, cancelable: true })
    el.querySelector('a').dispatchEvent(ev)
    expect(onOpen).toHaveBeenCalledWith('jh-1')
    expect(ev.defaultPrevented).toBe(true)
  })
})
