// The server sends cards as rank then suit, like "10H" or "AS".

export type Suit = 'H' | 'D' | 'C' | 'S'

const RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
const RANK_NAMES: Record<string, string> = { J: 'Jack', Q: 'Queen', K: 'King', A: 'Ace' }

// Asks for the plain text form of a suit symbol, so phones don't swap in a coloured emoji.
const TEXT = '︎'

export const SUITS: Record<Suit, { symbol: string; name: string; red: boolean }> = {
  H: { symbol: '♥' + TEXT, name: 'hearts', red: true },
  D: { symbol: '♦' + TEXT, name: 'diamonds', red: true },
  C: { symbol: '♣' + TEXT, name: 'clubs', red: false },
  S: { symbol: '♠' + TEXT, name: 'spades', red: false },
}

export function parseCard(card: string) {
  const rank = card.slice(0, -1)
  const suit = card.slice(-1)
  if (!RANKS.includes(rank) || !Object.hasOwn(SUITS, suit)) {
    throw new Error(`Not a card: ${card}`)
  }
  return { rank, suit: suit as Suit }
}

// What a screen reader says for a card, like "Ace of spades".
export function cardName(card: string) {
  const { rank, suit } = parseCard(card)
  return `${RANK_NAMES[rank] ?? rank} of ${SUITS[suit].name}`
}
