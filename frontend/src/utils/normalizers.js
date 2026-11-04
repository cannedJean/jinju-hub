// Accepts several pagination envelope shapes and returns a consistent structure.
export function normalizePage(payload = {}, mapper = (value) => value) {
  const envelope = payload?.data ?? payload
  const sourceItems = Array.isArray(envelope)
    ? envelope
    : (envelope?.items ?? envelope?.results ?? [])

  const items = sourceItems.map(mapper)

  return {
    items,
    total: Number(envelope?.total ?? envelope?.pagination?.total_items ?? items.length),
    page: Number(envelope?.page ?? envelope?.pagination?.page ?? 1),
    size: Number(envelope?.size ?? items.length),
    totalPages: Number(
      envelope?.totalPages ?? envelope?.total_pages ?? envelope?.pagination?.total_pages ?? 1,
    ),
  }
}
