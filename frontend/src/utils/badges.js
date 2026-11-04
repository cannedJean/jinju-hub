const PLACE_BADGES = new Set(['jinju8', 'food_explorer', 'history_walk', 'night_namgang'])

const isLit = (it) => !!(it && it.litAt)

export function evaluateBadges(state, collection) {
  const badges = collection?.badges
  if (!Array.isArray(badges)) return []
  const lit = Object.values(state?.items || {}).filter(isLit)
  const litIds = new Set(lit.map((it) => it.id))
  const litById = Object.fromEntries(lit.map((it) => [it.id, it]))

  return badges.map((b) => {
    let progress = 0
    if (b.id === 'first_light') {
      progress = lit.length
    } else if (PLACE_BADGES.has(b.id)) {
      progress = (b.eligible_place_ids || []).filter((id) => litIds.has(id)).length
    } else if (b.id === 'festival_guest') {
      const hit = (b.festival_windows || []).some((w) =>
        (w.venue_place_ids || []).some((id) => {
          const on = litById[id]?.litOn
          return !!on && on >= w.start && on <= w.end
        }),
      )
      progress = hit ? 1 : 0
    }
    const required = b.required ?? 1
    return {
      id: b.id,
      label: b.label,
      description: b.description,
      required,
      progress,
      earned: progress >= required,
    }
  })
}
