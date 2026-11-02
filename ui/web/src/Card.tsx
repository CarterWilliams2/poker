import { cardName, parseCard, SUITS } from './cards.ts'

// One playing card, drawn from a string like "10H".
export default function Card({ card }: { card: string }) {
  const { rank, suit } = parseCard(card)
  const { symbol, red } = SUITS[suit]
  return (
    <div className={red ? 'card red' : 'card'} role="img" aria-label={cardName(card)}>
      <span className="corner">
        {rank}
        <br />
        {symbol}
      </span>
      <span className="pip">{symbol}</span>
    </div>
  )
}
