import { useEffect, useRef, useState } from 'react'
import { pauseAfter } from './events.ts'
import type { TableMessage } from './protocol.ts'

// How fast it can play, as a multiple of the normal pace.
export const SPEEDS = [
  { speed: 0.5, name: '½×' },
  { speed: 1, name: '1×' },
  { speed: 2, name: '2×' },
  { speed: 4, name: '4×' },
]

export type Playback = ReturnType<typeof usePlayback>

// Plays messages back at a readable pace, however fast they arrive. `messages` only ever grows.
// `shown` is the index of the one on screen, and -1 until the first arrives, which shows straight
// away. Each one after that waits until the one before has been on screen long enough.
export function usePlayback(messages: TableMessage[]) {
  const [shown, setShown] = useState(-1)
  const [paused, setPaused] = useState(false)
  const [speed, setSpeed] = useState(1)
  const shownAt = useRef(0)

  const show = (index: number) => {
    shownAt.current = Date.now()
    setShown(index)
  }

  const next = shown + 1
  const waiting = next < messages.length

  useEffect(() => {
    if (paused || !waiting) return
    // Time already spent on screen counts, so a message that arrives late, or a change of speed,
    // doesn't start the wait over.
    const wait =
      shown < 0 ? 0 : pauseAfter(messages[shown]) / speed - (Date.now() - shownAt.current)
    if (wait <= 0) {
      show(next)
      return
    }
    const timer = setTimeout(() => show(next), wait)
    return () => clearTimeout(timer)
  }, [messages, messages.length, paused, shown, speed])

  return {
    shown,
    paused,
    speed,
    // Whether there's a message that hasn't been shown yet.
    waiting,
    setSpeed,
    togglePause: () => setPaused(!paused),
    // Pauses, and shows the next message.
    step: () => {
      setPaused(true)
      if (waiting) show(next)
    },
  }
}

// Buttons to pause, step through one message at a time and change the speed.
export function PlaybackControls({ playback }: { playback: Playback }) {
  const { paused, speed, waiting, setSpeed, togglePause, step } = playback
  return (
    <div className="playback" role="group" aria-label="Playback">
      <button onClick={togglePause}>{paused ? 'Play' : 'Pause'}</button>
      <button onClick={step} disabled={!waiting}>
        Step
      </button>
      <div className="speeds" role="group" aria-label="Speed">
        {SPEEDS.map((choice) => (
          <button
            key={choice.speed}
            aria-pressed={choice.speed === speed}
            onClick={() => setSpeed(choice.speed)}
          >
            {choice.name}
          </button>
        ))}
      </div>
    </div>
  )
}
