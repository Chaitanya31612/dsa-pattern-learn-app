/** Remove unchanged prompts/starter lines before counting learner-authored work. */
export function withoutScaffold(value: string, scaffold: string): string {
  const supplied = new Set(scaffold.split('\n').map(line => line.trim()).filter(Boolean))
  return value.split('\n').map(line => line.trim()).filter(line => line && !supplied.has(line)).join('\n')
}
