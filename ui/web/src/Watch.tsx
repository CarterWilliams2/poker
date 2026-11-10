import { useEffect, useRef, useState } from 'react'
import { watchMatch } from './api.ts'
import { bubblesAt, sweptBets } from './events.ts'
import { PlaybackControls, usePlayback } from './Playback.tsx'
import type { TableMessage } from './protocol.ts'
import Table from './Table.tsx'

const NO_SERVER = (
  <>
    Couldn't reach the poker server. Is <code>python ui/play.py</code> running? Reload this page to
    try again.
  </>
)

// Watches a match between bots. The server sends the whole match at once, and the page plays it
// back at a pace you can follow, redrawing the table with each message. Loading the page starts a
// new match.
export default function Watch() {
  // Every message so far. A long match has thousands, so they're added to one list rather than
  // copied into a new one each time, and setReceived tells React when there's another.
  const messages = useRef<TableMessage[]>([]).current
  const [, setReceived] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [lost, setLost] = useState(false)
  const playback = usePlayback(messages)

  useEffect(() => {
    // The server closes the connection once it has said all it has to say.
    let finished = false
    return watchMatch(
      (message) => {
        if (message.type === 'error') {
          finished = true
          setError(message.message)
          return
        }
        messages.push(message)
        setReceived(messages.length)
        if (message.type === 'match_over') finished = true
      },
      () => {
        if (!finished) setLost(true)
      },
    )
  }, [messages])

  const { shown } = playback
  const message = messages[shown]
  // A lost connection only matters once everything that did arrive has been played.
  const problem = error ?? (lost && !playback.waiting ? NO_SERVER : null)

  return (
    <main className="watch">
      <header>
        <h1>Watch</h1>
        {problem ? (
          <p className="error" role="alert">
            {problem}
          </p>
        ) : (
          <p>{progress(message)}</p>
        )}
        {message && <PlaybackControls playback={playback} />}
      </header>
      {message && (
        <Table
          table={message.table}
          bubbles={bubblesAt(messages, shown)}
          swept={sweptBets(messages[shown - 1]?.table, message.table)}
          speed={playback.speed}
        />
      )}
    </main>
  )
}

function progress(message: TableMessage | undefined) {
  if (message?.type === 'match_over') {
    const { hands_played: hands } = message
    return `Match over after ${hands} ${hands === 1 ? 'hand' : 'hands'}`
  }
  return message && message.table.hand > 0 ? `Hand ${message.table.hand}` : 'Starting the match…'
}
