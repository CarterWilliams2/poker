import { useEffect, useState } from 'react'
import { fetchDeal, type Deal } from './api.ts'
import Card from './Card.tsx'

export default function App() {
  const [deal, setDeal] = useState<Deal | null>(null)
  const [failed, setFailed] = useState(false)
  const [dealing, setDealing] = useState(true)
  // Every new value asks the server for another deal.
  const [round, setRound] = useState(0)

  useEffect(() => {
    // Drops the answer if another deal was asked for while this one was on its way.
    let current = true
    fetchDeal()
      .then((next) => {
        if (current) {
          setDeal(next)
          setFailed(false)
        }
      })
      .catch(() => {
        if (current) setFailed(true)
      })
      .finally(() => {
        if (current) setDealing(false)
      })
    return () => {
      current = false
    }
  }, [round])

  function dealAgain() {
    setDealing(true)
    setRound((count) => count + 1)
  }

  return (
    <main className="table">
      <h1>Poker</h1>
      {failed && (
        <p className="error" role="alert">
          Couldn't reach the poker server. Is <code>python ui/play.py</code> running?
        </p>
      )}
      {deal && (
        <>
          <Hand title="Your hand" cards={deal.hand} />
          <Hand title="Board" cards={deal.board} />
        </>
      )}
      <button onClick={dealAgain} disabled={dealing}>
        {dealing ? 'Dealing…' : 'Deal again'}
      </button>
    </main>
  )
}

function Hand({ title, cards }: { title: string; cards: string[] }) {
  return (
    <section className="hand" aria-label={title}>
      <h2>{title}</h2>
      <div className="cards">
        {cards.map((card) => (
          <Card key={card} card={card} />
        ))}
      </div>
    </section>
  )
}
