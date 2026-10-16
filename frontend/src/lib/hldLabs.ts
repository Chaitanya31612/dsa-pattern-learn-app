// Small deterministic teaching models. These do not contact infrastructure or move money.
export function queueProjection(initial: number, arrivals: number, capacity: number, seconds: number) {
  const backlog = Math.max(0, initial + (arrivals - capacity) * seconds)
  return { backlog, growth: arrivals - capacity, drainSeconds: capacity > arrivals ? Math.ceil(backlog / (capacity - arrivals)) : null }
}
export function reservationTrace(guarded: boolean, step: number) {
  const events = ['Buyer A sees one available seat.', 'Buyer B also sees one available seat.',
    guarded ? 'A atomically checks and reserves the seat. One booking commits.' : 'A uses the old read, writes available=0, and confirms.',
    guarded ? 'B atomically checks current state. It is already reserved, so B is rejected.' : 'B uses the same old read, writes available=0, and also confirms.']
  return { events: events.slice(0, step), bookings: step < 3 ? 0 : guarded || step < 4 ? 1 : 2, available: step < 3 ? 1 : 0 }
}
export function retryTrace(stable: boolean, step: number) {
  const events = ['Client sends intent ORDER-7 with key K1.', 'Provider stores a successful effect under K1.',
    'The reply is lost. The client knows only that the outcome is unknown.',
    stable ? 'Retry reuses K1 and the same parameters. Provider returns the existing outcome.' : 'Retry uses new key K2. Provider sees a new operation and creates a second effect.']
  return { events: events.slice(0, step), effects: step < 2 ? 0 : stable || step < 4 ? 1 : 2 }
}
export const GEO_PLACES = [{ id: 'A', x: 105, y: 90 }, { id: 'B', x: 65, y: 80 }, { id: 'C', x: 175, y: 175 }, { id: 'D', x: 75, y: 130 }]
export function geoSearch(x: number, y: number, radius: number, neighbors: boolean) {
  const cells = Array.from({ length: 4 }, (_, i) => ({ x: (i % 2) * 100, y: Math.floor(i / 2) * 100 }))
  const selected = cells.filter(c => neighbors
    ? Math.hypot(Math.max(c.x - x, 0, x - (c.x + 100)), Math.max(c.y - y, 0, y - (c.y + 100))) <= radius
    : Math.floor(x / 100) === c.x / 100 && Math.floor(y / 100) === c.y / 100)
  const candidates = GEO_PLACES.filter(p => selected.some(c => p.x >= c.x && p.x < c.x + 100 && p.y >= c.y && p.y < c.y + 100))
  const matches = candidates.filter(p => Math.hypot(p.x - x, p.y - y) <= radius)
  const actual = GEO_PLACES.filter(p => Math.hypot(p.x - x, p.y - y) <= radius)
  return { selected, candidates, matches, missed: actual.filter(p => !matches.includes(p)) }
}
