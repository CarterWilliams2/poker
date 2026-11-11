import { describeAction } from './events.ts'
import type { TableMessage } from './protocol.ts'

// One thing that happened, like "Tuned 1 raises to 40", and the pot straight afterwards, counting
// the bets still in front of the players. A player showing down has their `cards` and the `hand`
// they make. `latest` marks what's just happened.
export type LogLine = {
  name: string
  text: string
  cards: string[]
  hand: string | null
  pot: number
  latest: boolean
}

// A betting round, or the showdown, with the cards it dealt to the board.
export type LogStreet = { street: string; cards: string[]; lines: LogLine[]; latest: boolean }

export type HandLog = { hand: number; streets: LogStreet[] }

// Everything that has happened in the hand that messages[index] belongs to, up to and including
// it, by street. Null before the first hand is dealt.
export function handLog(messages: TableMessage[], index: number): HandLog | null {
  let start = index
  while (start >= 0 && messages[start].type !== 'hand_start') start--
  if (start < 0) return null

  const streets: LogStreet[] = []
  for (let at = start; at <= index; at++) {
    const message = messages[at]
    const { table } = message
    const latest = at === index
    const newStreet = (street: string, cards: string[] = []) =>
      streets.push({ street, cards, lines: [], latest })
    const line = (name: string, text: string, details: Partial<LogLine> = {}) =>
      streets[streets.length - 1].lines.push({
        name,
        text,
        cards: [],
        hand: null,
        pot: table.pot,
        latest,
        ...details,
      })

    switch (message.type) {
      case 'hand_start': {
        const bet = (name: string) => table.seats.find((seat) => seat.name === name)!.bet
        const small = bet(table.small_blind!)
        newStreet('preflop')
        line(table.small_blind!, `posts a small blind of ${small}`, { pot: small })
        line(table.big_blind!, `posts a big blind of ${bet(table.big_blind!)}`)
        break
      }
      case 'action': {
        const text = describeAction(message, messages[at - 1].table)
        line(message.name, text[0].toLowerCase() + text.slice(1))
        break
      }
      case 'street':
        newStreet(message.street, message.cards)
        break
      case 'showdown':
        newStreet('showdown')
        for (const { name, cards, hand } of message.hands) {
          line(name, 'shows', { cards, hand })
        }
        break
      case 'pot':
        line(
          listOf(message.winners),
          `${message.winners.length > 1 ? 'split' : 'wins'} ${message.amount}`,
        )
        break
      case 'busted':
        line(message.name, `is out, in ${ordinal(message.place)} place`)
        break
    }
  }
  return { hand: messages[index].table.hand, streets }
}

// "Tuned 1", "Tuned 1 and Random 2", or "Tuned 1, Random 2 and Tight 3".
function listOf(names: string[]) {
  return names.length > 1 ? `${names.slice(0, -1).join(', ')} and ${names.at(-1)}` : names[0]
}

const SUFFIXES: Record<number, string> = { 1: 'st', 2: 'nd', 3: 'rd' }

// 2nd, 3rd, 4th and so on, for places at a table of up to 8.
function ordinal(place: number) {
  return `${place}${SUFFIXES[place] ?? 'th'}`
}
