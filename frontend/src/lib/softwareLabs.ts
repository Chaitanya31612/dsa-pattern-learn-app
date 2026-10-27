/** Deterministic teaching model. No broker, database, or external requests. */
export function eventFlowModel() {
  return {
    records: [] as string[], pending: true, published: false,
    position: 0, committed: 0, inflight: null as { index: number; id: string } | null,
    inbox: [] as string[], effects: 0, deduplicate: true,
    publish(mark = true) {
      if (!this.pending) return
      this.records.push('ticket-completed-e1')
      if (mark) { this.pending = false; this.published = true }
    },
    read() {
      if (this.inflight || this.position >= this.records.length) return
      this.inflight = { index: this.position, id: this.records[this.position]! }
      this.position++
    },
    apply() {
      if (!this.inflight) return
      if (!this.deduplicate || !this.inbox.includes(this.inflight.id)) this.effects++
      if (!this.inbox.includes(this.inflight.id)) this.inbox.push(this.inflight.id)
    },
    commit() {
      if (!this.inflight) return
      this.committed = this.inflight.index + 1
      this.inflight = null
    },
    crash() { this.position = this.committed; this.inflight = null },
  }
}
