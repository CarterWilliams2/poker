import { useEffect, useState } from 'react'
import { fetchDeal, type Deal, type Hand } from './api.ts'
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
      {deal && <Showdown deal={deal} />}
      <button onClick={dealAgain} disabled={dealing}>
        {dealing ? 'Dealing…' : 'Deal again'}
      </button>
    </main>
  )
}

// Your opponent at the top and you at the bottom, with the board between you, as at a table.
function Showdown({ deal }: { deal: Deal }) {
  const [yours, theirs] = deal.hands
  const tie = deal.hands.filter((hand) => hand.wins).length > 1
  const badge = (hand: Hand) => (hand.wins ? (tie ? 'Tie' : 'Wins') : undefined)
  return (
    <>
      <Cards title="Opponent's hand" cards={theirs.cards} name={theirs.name} badge={badge(theirs)} />
      <Cards title="Board" cards={deal.board} />
      <Cards title="Your hand" cards={yours.cards} name={yours.name} badge={badge(yours)} />
    </>
  )
}

type CardsProps = { title: string; cards: string[]; name?: string; badge?: string }

// A titled row of cards. A player's hand also shows its name, and a badge if it won.
function Cards({ title, cards, name, badge }: CardsProps) {
  return (
    <section className={badge ? 'hand winner' : 'hand'} aria-label={title}>
      <h2>{title}</h2>
      <div className="cards">
        {cards.map((card) => (
          <Card key={card} card={card} />
        ))}
      </div>
      {name && (
        <p className="hand-name">
          {name}
          {badge && <span className="badge">{badge}</span>}
        </p>
      )}
    </section>
  )
}
