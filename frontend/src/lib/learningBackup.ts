import { validateSoftwareProgress } from './softwareLearning'
import type { SoftwareProgress } from '../types/software'
export type LearningArea = 'software' | 'ai'
export function encodeLearningBackup(progress: SoftwareProgress, area: LearningArea) {
  return JSON.stringify({ learningArea: area, progress }, null, 2)
}
export function decodeLearningBackup(value: unknown, area: LearningArea): SoftwareProgress {
  if (value && typeof value==='object' && 'learningArea' in value) {
    const envelope=value as { learningArea: unknown; progress: unknown }
    if(envelope.learningArea!==area) throw new Error('This backup belongs to the other learning space. Open its Backup tab.')
    return validateSoftwareProgress(envelope.progress)
  }
  if(area==='ai') throw new Error('Use an AI Learnings backup with its learning-area label. Older Software backups belong in Software Learnings.')
  return validateSoftwareProgress(value) // Original Software backups remain valid.
}
