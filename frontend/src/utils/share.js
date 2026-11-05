const MAX_IDS = 100
const MAX_INPUT = 4096
const ID_RE = /^jh-[A-Za-z0-9_-]{1,64}$/

export const SHARE_MAX_IDS = MAX_IDS

function toToken(ids) {
  const bytes = new TextEncoder().encode(ids.join(','))
  let bin = ''
  for (const b of bytes) bin += String.fromCharCode(b)
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

// The ids a link can really carry: the newest MAX_IDS that also fit the decoder's input limit.
export function capShareIds(ids) {
  const out = (ids || []).slice(0, MAX_IDS)
  while (out.length > 1 && toToken(out).length > MAX_INPUT) out.pop()
  return out
}

export function encodeShare(ids) {
  return toToken(capShareIds(ids))
}

export function decodeShare(s) {
  if (typeof s !== 'string' || !s || s.length > MAX_INPUT) return []
  try {
    const b64 = s.replace(/-/g, '+').replace(/_/g, '/')
    const bin = atob(b64 + '='.repeat((4 - (b64.length % 4)) % 4))
    const text = new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)))
    const ids = text.split(',').filter((id) => ID_RE.test(id))
    return [...new Set(ids)].slice(0, MAX_IDS)
  } catch {
    return []
  }
}
