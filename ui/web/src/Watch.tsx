import { useEffect, useState, type ReactNode } from 'react'
import { watchMatch } from './api.ts'
import type { TableState } from './protocol.ts'
import Table from './Table.tsx'

const NO_SERVER = (
  <>
    Couldn't reach the poker server. Is <code>python ui/play.py</code> running? Reload this page to
    try again.
  </>
)

// Watches a match between bots, redrawing the table with each message from the server. Loading the
// page starts a new match.
export default function Watch() {
  const [table, setTable] = useState<TableState | null>(null)
  const [handsPlayed, setHandsPlayed] = useState<number | null>(null)
  const [problem, setProblem] = useState<ReactNode>(null)

  useEffect(() => {
    // The server closes the connection once it has said all it has to say.
    let finished = false
    return watchMatch(
      (message) => {
        if (message.type === 'error') {
          finished = true
          setProblem(message.message)
          return
        }
        setTable(message.table)
        if (message.type === 'match_over') {
          finished = true
          setHandsPlayed(message.hands_played)
        }
      },
      () => {
        if (!finished) setProblem(NO_SERVER)
      },
    )
  }, [])

  return (
    <main className="watch">
      <header>
        <h1>Watch</h1>
        {problem ? (
          <p className="error" role="alert">
            {problem}
          </p>
        ) : (
          <p>{progress(table, handsPlayed)}</p>
        )}
      </header>
      {table && <Table table={table} />}
    </main>
  )
}

function progress(table: TableState | null, handsPlayed: number | null) {
  if (handsPlayed !== null) {
    return `Match over after ${handsPlayed} ${handsPlayed === 1 ? 'hand' : 'hands'}`
  }
  return table && table.hand > 0 ? `Hand ${table.hand}` : 'Starting the match…'
}
