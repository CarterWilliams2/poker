import { useEffect, useRef } from 'react'
import { cardName, parseCard, SUITS } from './cards.ts'
import type { HandLog as Log } from './log.ts'

// A side panel listing what has happened this hand, by street, with the pot after each thing. It
// keeps the newest at the bottom in view.
export default function HandLog({ log }: { log: Log | null }) {
  const scroller = useRef<HTMLDivElement>(null)
  const count = log?.streets.reduce((total, street) => total + 1 + street.lines.length, 0)

  useEffect(() => {
    const lines = scroller.current!
    lines.scrollTop = lines.scrollHeight
  }, [log?.hand, count])

  return (
    <aside className="hand-log" aria-label="Hand log">
      <header>
        <h2>{log ? `Hand ${log.hand}` : 'Hand log'}</h2>
        <span>Pot</span>
      </header>
      <div className="hand-log-lines" ref={scroller}>
        {log ? (
          log.streets.map(({ street, cards, lines, latest }) => (
            <section key={street} aria-label={capitalized(street)}>
              <h3 className={latest ? 'latest' : undefined}>
                {capitalized(street)}
                {cards.map((card) => (
                  <LogCard key={card} card={card} />
                ))}
              </h3>
              <ol>
                {lines.map(({ name, text, cards, hand, pot, latest }, index) => (
                  <li key={index} className={latest ? 'latest' : undefined}>
                    <span>
                      <b>{name}</b> {text}
                      {cards.map((card) => (
                        <LogCard key={card} card={card} />
                      ))}
                      {hand && <>, {hand}</>}
                    </span>
                    <span className="log-pot">{pot}</span>
                  </li>
                ))}
              </ol>
            </section>
          ))
        ) : (
          <p>The first hand is about to be dealt.</p>
        )}
      </div>
    </aside>
  )
}

// A card written small, like "K♥", in its suit's colour.
function LogCard({ card }: { card: string }) {
  const { rank, suit } = parseCard(card)
  const { symbol, red } = SUITS[suit]
  return (
    <span className={red ? 'log-card red' : 'log-card'} role="img" aria-label={cardName(card)}>
      {rank}
      {symbol}
    </span>
  )
}

const capitalized = (text: string) => text[0].toUpperCase() + text.slice(1)
