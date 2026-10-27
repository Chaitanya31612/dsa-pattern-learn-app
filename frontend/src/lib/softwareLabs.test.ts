import { describe, expect, it } from 'vitest'
import { eventFlowModel } from './softwareLabs'
describe('event-boundary teaching model', () => {
  it('replays after effect-before-offset crash and deduplicates the DB effect', () => {
    const m=eventFlowModel();m.publish();m.read();m.apply();m.crash()
    expect(m.committed).toBe(0);m.read();m.apply();m.commit()
    expect(m.effects).toBe(1);expect(m.committed).toBe(1)
  })
  it('exposes a duplicate effect without an inbox', () => {
    const m=eventFlowModel();m.deduplicate=false;m.publish();m.read();m.apply();m.crash();m.read();m.apply()
    expect(m.effects).toBe(2)
  })
  it('exposes the lost-effect gap when progress is committed first', () => {
    const m=eventFlowModel();m.publish();m.read();m.commit();m.crash();m.read();m.apply()
    expect(m.effects).toBe(0);expect(m.inflight).toBeNull()
  })
  it('keeps one event identity across an acknowledgment/mark crash gap', () => {
    const m=eventFlowModel();m.publish(false);m.publish();expect(m.records).toHaveLength(2)
    m.read();m.apply();m.commit();m.read();m.apply();m.commit()
    expect(m.effects).toBe(1);expect(m.committed).toBe(2)
  })
})
