// Chat sources follow the API contract { type: 'place'|'post', id, label }.
// Convert them to router links; unknown types are ignored.
export function toSourceLinks(sources) {
  if (!Array.isArray(sources)) return []
  const links = []
  for (const s of sources) {
    if (!s || s.id === undefined || s.id === null || s.id === '') continue
    const id = String(s.id)
    const label = String(s.label || id)
    if (s.type === 'place') {
      links.push({ to: { name: 'place', params: { id } }, label, kind: 'place', placeId: id })
    } else if (s.type === 'post') {
      links.push({ to: { name: 'post', params: { id } }, label, kind: 'post' })
    }
  }
  return links
}
