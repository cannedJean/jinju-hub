import { categoryLabel } from '../../utils/format'
import { safeCategory } from './markerIcons'

// Marker popup built from DOM nodes with textContent only, so place data can never inject HTML.
// { distanceText, saved, lit, href, onToggleSave(id), getSaved(id), onOpen(id) }.
// After a toggle the button re-reads the real state via getSaved (onToggleSave may return a promise),
// so it never shows a save that did not happen. A lit place cannot be un-saved here (that would erase
// its check-in), so its button is a static badge.
export function buildPopup(
  marker,
  { distanceText = '', saved = false, lit = false, href, onToggleSave, getSaved, onOpen } = {},
) {
  const el = (tag, className, text) => {
    const node = document.createElement(tag)
    if (className) node.className = className
    if (text !== undefined) node.textContent = text
    return node
  }

  const wrap = el('div', 'map-popup')

  const meta = el('div', 'map-popup__meta')
  const cat = el('span', `map-popup__cat marker--${safeCategory(marker.category)}`, categoryLabel(marker.category))
  meta.appendChild(cat)
  if (distanceText) meta.appendChild(el('span', 'map-popup__dist', `기준점에서 ${distanceText}`))
  wrap.appendChild(meta)

  wrap.appendChild(el('div', 'map-popup__title', marker.title))

  const actions = el('div', 'map-popup__actions')
  const link = el('a', 'map-popup__link', '상세 보기')
  link.href = href || `/places/${encodeURIComponent(marker.id)}`
  link.addEventListener('click', (event) => {
    if (!onOpen || event.ctrlKey || event.metaKey || event.shiftKey) return
    event.preventDefault()
    onOpen(marker.id)
  })
  actions.appendChild(link)

  const btn = el('button', 'map-popup__save')
  btn.type = 'button'
  let isSaved = !!saved
  if (lit) {
    btn.textContent = '◆ 밝힌 곳'
    btn.disabled = true
    btn.classList.add('is-lit')
    actions.appendChild(btn)
    wrap.appendChild(actions)
    return wrap
  }
  const render = () => {
    btn.textContent = isSaved ? '◇ 담음' : '＋ 담기'
    btn.setAttribute('aria-pressed', String(isSaved))
    btn.setAttribute('aria-label', isSaved ? `${marker.title} 담기 취소` : `${marker.title} 담기`)
    btn.classList.toggle('is-saved', isSaved)
  }
  render()
  btn.addEventListener('click', async () => {
    btn.disabled = true
    try {
      await onToggleSave?.(marker.id)
    } finally {
      isSaved = getSaved ? !!getSaved(marker.id) : !isSaved
      btn.disabled = false
      render()
    }
  })
  actions.appendChild(btn)
  wrap.appendChild(actions)

  return wrap
}
