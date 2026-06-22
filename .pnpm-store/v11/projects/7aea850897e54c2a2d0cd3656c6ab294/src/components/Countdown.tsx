import { useState, useEffect, useLayoutEffect, useRef } from 'react'

export function Countdown({ targetMs, onZero }: { targetMs: number; onZero?: () => void }) {
  const [, tick] = useState(0)
  const onZeroRef = useRef(onZero)
  useLayoutEffect(() => { onZeroRef.current = onZero })
  useEffect(() => {
    const id = setInterval(() => {
      if (Date.now() >= targetMs) {
        clearInterval(id)
        onZeroRef.current?.()
        return
      }
      tick(n => n + 1)
    }, 1000)
    return () => clearInterval(id)
  }, [targetMs])
  const diff = Math.max(0, targetMs - Date.now())
  const d = Math.floor(diff / 86_400_000)
  const h = Math.floor((diff % 86_400_000) / 3_600_000)
  const m = Math.floor((diff % 3_600_000) / 60_000)
  const s = Math.floor((diff % 60_000) / 1_000)
  if (d > 0) return <>{`${d}d ${String(h).padStart(2, '0')}h ${String(m).padStart(2, '0')}m`}</>
  const parts: string[] = []
  if (h > 0) parts.push(`${h}h`)
  parts.push(`${String(m).padStart(2, '0')}m`)
  parts.push(`${String(s).padStart(2, '0')}s`)
  return <>{parts.join(' ')}</>
}

export function ElapsedTime({ startMs, maxMs, onMax }: { startMs: number; maxMs: number; onMax?: () => void }) {
  const [, tick] = useState(0)
  const onMaxRef = useRef(onMax)
  useLayoutEffect(() => { onMaxRef.current = onMax })
  useEffect(() => {
    const id = setInterval(() => {
      if (Date.now() >= maxMs) {
        clearInterval(id)
        onMaxRef.current?.()
        return
      }
      tick(n => n + 1)
    }, 1000)
    return () => clearInterval(id)
  }, [startMs, maxMs])
  const elapsed = Math.max(0, Date.now() - startMs)
  const m = Math.floor(elapsed / 60_000)
  const s = Math.floor((elapsed % 60_000) / 1_000)
  return <>{`${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`}</>
}
