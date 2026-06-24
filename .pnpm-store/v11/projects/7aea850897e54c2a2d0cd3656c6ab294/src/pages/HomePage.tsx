import { useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Users, Wallet, Trophy, Target, ChevronDown } from 'lucide-react'
import { Footer } from '../components/Footer'

const steps = [
  {
    icon: Users,
    title: 'Create or join a competition',
    description:
      "Set up your own sweepstake and invite friends or colleagues with a single link — or jump straight into one they've already started. No complicated setup, no excuses.",
  },
  {
    icon: Wallet,
    title: 'Sort the stake',
    description:
      "If your group is playing for something, transfer your entry fee directly to whoever is holding the pot. Skin in the game makes every prediction matter just a little more.",
  },
  {
    icon: Trophy,
    title: 'Predict before the whistle',
    description:
      "Call the tournament winner, group standings, and knockout-stage outcomes before the relevant matches kick off. Once it starts, the books are closed.",
  },
  {
    icon: Target,
    title: 'Call every score, earn every point',
    description:
      "For each match, predict the exact scoreline before kick-off. Every correct call earns you points — and at the end, bragging rights are on the line.",
  },
]

// ─── Constants ────────────────────────────────────────────────────────────────
const SECTION_COUNT = 6   // hero + 4 steps + footer CTA
const ANIM_MS       = 750 // ms per snap
const WHEEL_THRESH  = 60  // px of accumulated delta before snapping

// ─── Helpers ──────────────────────────────────────────────────────────────────
function easeInOutCubic(t: number) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

type Refs = React.RefObject<HTMLDivElement | null>[]

/** Directly mutate DOM — zero React re-renders during animation */
function paint(refs: Refs, p: number) {
  refs.forEach((ref, i) => {
    if (!ref.current) return
    const d = p - i
    let opacity: number
    let ty: number

    if (d <= -1)      { opacity = 0;       ty = 50        }
    else if (d <= 0)  { opacity = d + 1;   ty = (-d) * 50 }
    else if (d <= 1)  { opacity = 1 - d;   ty = -d * 30   }
    else              { opacity = 0;        ty = -30       }

    ref.current.style.opacity       = String(Math.max(0, Math.min(1, opacity)))
    ref.current.style.transform     = `translateY(${ty}px)`
    ref.current.style.pointerEvents = opacity > 0.25 ? 'auto' : 'none'
  })
}

// ─── Buttons ──────────────────────────────────────────────────────────────────
const base       = 'inline-block rounded px-6 py-3 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-transparent'
const primaryBtn = `${base} bg-teal-600 text-white hover:bg-teal-500 focus:ring-teal-500`
const outlineBtn = `${base} border border-white/60 text-white hover:bg-white/10 focus:ring-white`

// ─── Component ────────────────────────────────────────────────────────────────
export function HomePage() {
  const { search } = useLocation()
  const containerRef = useRef<HTMLDivElement>(null)
  const heroRef      = useRef<HTMLDivElement>(null)
  const step1Ref     = useRef<HTMLDivElement>(null)
  const step2Ref     = useRef<HTMLDivElement>(null)
  const step3Ref     = useRef<HTMLDivElement>(null)
  const step4Ref     = useRef<HTMLDivElement>(null)
  const ctaRef       = useRef<HTMLDivElement>(null)
  const nextCueRef     = useRef<HTMLDivElement>(null)
  const takepartCueRef = useRef<HTMLDivElement>(null)

  // All animation state lives in a single mutable ref — no re-renders
  const anim = useRef({ progress: 0, target: 0, animating: false, startProg: 0, startTime: 0 })
  const raf  = useRef(0)
  const wheelAccum = useRef(0)

  useEffect(() => {
    const refs: Refs = [heroRef, step1Ref, step2Ref, step3Ref, step4Ref, ctaRef]

    // Next Step cue: steps 1–3. Take part cue: step 4.
    function updateCue(p: number) {
      if (nextCueRef.current) {
        let op = 0
        if      (p > 0 && p <= 1) op = p          // fading in with step 1
        else if (p > 1 && p <= 3) op = 1          // fully visible through steps 2 & 3
        else if (p > 3 && p <  4) op = 4 - p      // fading out as step 3 → step 4
        nextCueRef.current.style.opacity       = String(op)
        nextCueRef.current.style.pointerEvents = op > 0.5 ? 'auto' : 'none'
      }
      if (takepartCueRef.current) {
        let op = 0
        if      (p > 3 && p <= 4) op = p - 3      // fading in as step 4 arrives
        else if (p > 4 && p <  5) op = 5 - p      // fading out as step 4 → CTA
        takepartCueRef.current.style.opacity       = String(op)
        takepartCueRef.current.style.pointerEvents = op > 0.5 ? 'auto' : 'none'
      }
    }

    paint(refs, 0) // hero fully visible on mount
    updateCue(0)

    // ── RAF animation loop ────────────────────────────────────────────────────
    function tick(now: number) {
      const s = anim.current
      const t = Math.min(1, (now - s.startTime) / ANIM_MS)
      s.progress = s.startProg + (s.target - s.startProg) * easeInOutCubic(t)
      paint(refs, s.progress)
      updateCue(s.progress)

      if (t < 1) {
        raf.current = requestAnimationFrame(tick)
      } else {
        s.progress  = s.target
        s.animating = false
        paint(refs, s.target)
        updateCue(s.target)
        wheelAccum.current = 0 // ready for next gesture
      }
    }

    function goTo(next: number) {
      const s       = anim.current
      const clamped = Math.max(0, Math.min(SECTION_COUNT - 1, next))
      if (clamped === s.target && (s.animating || s.progress === clamped)) return

      s.target    = clamped
      s.startProg = s.progress
      s.startTime = performance.now()

      if (!s.animating) {
        s.animating = true
        raf.current = requestAnimationFrame(tick)
      }
      // If already animating: updated target/startProg are picked up automatically
    }

    const goNext = () => goTo(anim.current.target + 1)
    const goPrev = () => goTo(anim.current.target - 1)

    // ── Wheel ─────────────────────────────────────────────────────────────────
    function onWheel(e: WheelEvent) {
      e.preventDefault()
      if (anim.current.animating) return // one snap per animation
      wheelAccum.current += e.deltaY
      if (Math.abs(wheelAccum.current) >= WHEEL_THRESH) {
        const dir = wheelAccum.current > 0 ? 1 : -1
        wheelAccum.current = 0
        if (dir > 0) goNext(); else goPrev()
      }
    }

    // ── Touch ─────────────────────────────────────────────────────────────────
    let touchY = 0
    const onTouchStart = (e: TouchEvent) => { touchY = e.touches[0].clientY }
    const onTouchEnd   = (e: TouchEvent) => {
      const dy = touchY - e.changedTouches[0].clientY
      if (Math.abs(dy) > 40) { if (dy > 0) goNext(); else goPrev() }
    }

    // ── Keyboard ──────────────────────────────────────────────────────────────
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' || e.key === 'PageDown') { e.preventDefault(); goNext() }
      if (e.key === 'ArrowUp'   || e.key === 'PageUp')   { e.preventDefault(); goPrev() }
    }

    const el = containerRef.current!
    el.addEventListener('wheel',      onWheel,      { passive: false })
    el.addEventListener('touchstart', onTouchStart, { passive: true  })
    el.addEventListener('touchend',   onTouchEnd,   { passive: true  })
    window.addEventListener('keydown', onKeyDown)

    return () => {
      el.removeEventListener('wheel',      onWheel)
      el.removeEventListener('touchstart', onTouchStart)
      el.removeEventListener('touchend',   onTouchEnd)
      window.removeEventListener('keydown', onKeyDown)
      cancelAnimationFrame(raf.current)
    }
  }, [])

  return (
    <div ref={containerRef} className="relative h-screen overflow-hidden cursor-default">
      {/* ── Background ── */}
      <div className="absolute inset-0 bg-app bg-cover bg-center" aria-hidden="true" />
      <div className="absolute inset-0 bg-black/75" aria-hidden="true" />

      {/* ── Section 0: Hero ── */}
      <div
        ref={heroRef}
        className="absolute inset-0 flex flex-col items-center justify-center px-6 text-center text-white"
        style={{ willChange: 'opacity, transform' }}
      >
        <h1 className="text-5xl font-extrabold tracking-tight sm:text-7xl">
          Sweep<span className="text-teal-400">Stake</span>
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-white/80 sm:text-xl">
          After the success of the World Cup Prediction I thought I would create
          one for the SPFL 2026/27. This really is a marathon.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link to={`/login${search}`} className={primaryBtn}>Sign in</Link>
          <Link to={`/register${search}`} className={outlineBtn}>Create account</Link>
        </div>
        <div className="absolute bottom-10 flex flex-col items-center gap-2 text-white/40">
          <span className="text-xs uppercase tracking-widest">How it works</span>
          <ChevronDown className="animate-bounce" size={24} />
        </div>
      </div>

      {/* ── Sections 1–4: Steps ── */}
      {([step1Ref, step2Ref, step3Ref, step4Ref] as const).map((ref, i) => {
        const { icon: Icon, title, description } = steps[i]
        return (
          <div
            key={title}
            ref={ref}
            className="absolute inset-0 flex items-center justify-center px-6"
            style={{ opacity: 0, pointerEvents: 'none', willChange: 'opacity, transform' }}
          >
            <div className="flex max-w-2xl flex-col items-center text-center text-white">
              <div className="mb-6 inline-flex h-20 w-20 items-center justify-center rounded-2xl bg-teal-500/20 text-teal-400 ring-1 ring-teal-400/30">
                <Icon size={40} />
              </div>
              <span className="mb-3 text-sm font-semibold uppercase tracking-widest text-teal-400">
                Step {i + 1}
              </span>
              <h2 className="mb-5 text-4xl font-extrabold leading-tight sm:text-5xl">{title}</h2>
              <p className="max-w-lg text-lg leading-relaxed text-white/70">{description}</p>
            </div>
          </div>
        )
      })}

      {/* ── Next Step cue — shown for steps 1–3 ── */}
      <div
        ref={nextCueRef}
        className="absolute bottom-10 left-0 right-0 flex flex-col items-center gap-2 text-white/50"
        style={{ opacity: 0, pointerEvents: 'none' }}
      >
        <span className="text-xs uppercase tracking-widest">Next Step</span>
        <ChevronDown className="animate-bounce" size={24} />
      </div>

      {/* ── Take part cue — shown for step 4 ── */}
      <div
        ref={takepartCueRef}
        className="absolute bottom-10 left-0 right-0 flex flex-col items-center gap-2 text-white/50"
        style={{ opacity: 0, pointerEvents: 'none' }}
      >
        <span className="text-xs uppercase tracking-widest">Take part</span>
        <ChevronDown className="animate-bounce" size={24} />
      </div>

      {/* ── Section 5: Footer CTA ── */}
      <div
        ref={ctaRef}
        className="absolute inset-0 flex flex-col items-center justify-center px-6 text-center text-white"
        style={{ opacity: 0, pointerEvents: 'none', willChange: 'opacity, transform' }}
      >
        <h2 className="text-3xl font-bold sm:text-5xl">
          Ready to put your football<br className="hidden sm:block" /> knowledge to the test?
        </h2>
        <p className="mx-auto mt-5 max-w-md text-lg text-white/60">
          All you need is an account and some confidence.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link to={`/login${search}`} className={outlineBtn}>Sign in</Link>
          <Link to={`/register${search}`} className={primaryBtn}>Create account</Link>
        </div>
        <div className="absolute bottom-0 left-0 right-0">
          <Footer />
        </div>
      </div>
    </div>
  )
}
