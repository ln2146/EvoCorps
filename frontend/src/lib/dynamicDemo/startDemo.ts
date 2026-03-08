import { setAttackFlag, setAttackMode, setAftercareFlag, setModerationFlag } from '../../services/api'
import type { AttackMode } from '../attackModeToggle'

interface StartDynamicDemoOptions {
  enableAttack: boolean
  attackMode: AttackMode | null
  enableAftercare: boolean
  enableModeration: boolean
  enableEvoCorps: boolean
  snapshotId?: string
  startTick?: number
  fetchImpl?: typeof fetch
  scheduleSync?: (callback: () => void, delayMs: number) => void
}

interface StartDynamicDemoResult {
  success: boolean
  data?: any
  message?: string
}

export async function startDynamicDemoWithPreset({
  enableAttack,
  attackMode,
  enableAftercare,
  enableModeration,
  enableEvoCorps,
  snapshotId,
  startTick,
  fetchImpl = fetch,
  scheduleSync = (callback, delayMs) => {
    globalThis.setTimeout(callback, delayMs)
  },
}: StartDynamicDemoOptions): Promise<StartDynamicDemoResult> {
  await fetchImpl('/api/config/moderation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content_moderation: enableModeration }),
  }).catch(() => {})

  const response = await fetchImpl('/api/dynamic/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      enable_attack: enableAttack,
      enable_aftercare: enableAftercare,
      snapshot_id: snapshotId,
      start_tick: startTick,
    }),
  })

  const data = await response.json()
  if (!data.success) {
    return {
      success: false,
      data,
      message: data.message || '未知错误',
    }
  }

  const preAttack = enableAttack
  const preAttackMode = attackMode
  const preAftercare = enableAftercare
  const preModeration = enableModeration
  const preEvoCorps = enableEvoCorps

  scheduleSync(() => {
    void (async () => {
      const syncs: Array<Promise<unknown>> = []
      if (preAttack) {
        if (preAttackMode) {
          syncs.push(setAttackMode(preAttackMode).catch(() => {}))
        }
        syncs.push(setAttackFlag(true).catch(() => {}))
      }
      if (!preAftercare) {
        syncs.push(setAftercareFlag(false).catch(() => {}))
      }
      if (preModeration) {
        syncs.push(setModerationFlag(true).catch(() => {}))
      }
      await Promise.allSettled(syncs)
      if (preEvoCorps) {
        await fetchImpl('/api/dynamic/opinion-balance/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        }).catch(() => {})
      }
    })()
  }, 3000)

  return { success: true, data }
}
