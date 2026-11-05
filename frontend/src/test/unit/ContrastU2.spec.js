import { describe, expect, test } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function getRelativeLuminance(hex) {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255

  const adjust = (c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4))
  const R = adjust(r)
  const G = adjust(g)
  const B = adjust(b)

  return 0.2126 * R + 0.7152 * G + 0.0722 * B
}

function getContrastRatio(hex1, hex2) {
  const l1 = getRelativeLuminance(hex1)
  const l2 = getRelativeLuminance(hex2)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

describe('U2 - Design System Contrast Ratio Fix', () => {
  const tokensPath = resolve(__dirname, '../../styles/tokens.css')
  const content = readFileSync(tokensPath, 'utf-8')

  test('tokens.css defines --text-faint as #64748b', () => {
    const match = /--text-faint:\s*([^;]+);/.exec(content)
    expect(match).not.toBeNull()
    const color = match[1].trim()
    expect(color).toBe('#64748b')
  })

  test('--text-faint achieves >= 4.5:1 contrast against white (#ffffff) for WCAG AA compliance', () => {
    const match = /--text-faint:\s*([^;]+);/.exec(content)
    const color = match[1].trim()
    const ratio = getContrastRatio(color, '#ffffff')
    expect(ratio).toBeGreaterThanOrEqual(4.5)
  })
})
