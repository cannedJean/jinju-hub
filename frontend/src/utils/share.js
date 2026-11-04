const MAX_IDS = 100

export function encodeShare(ids) {
  const bytes = new TextEncoder().encode((ids || []).join(','))
  let bin = ''
  for (const b of bytes) bin += String.fromCharCode(b)
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export function decodeShare(s) {
  if (typeof s !== 'string' || !s) return []
  try {
    const b64 = s.replace(/-/g, '+').replace(/_/g, '/')
    const bin = atob(b64 + '='.repeat((4 - (b64.length % 4)) % 4))
    const text = new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)))
    return text
      .split(',')
      .filter((id) => id.startsWith('jh-'))
      .slice(0, MAX_IDS)
  } catch {
    return []
  }
}
