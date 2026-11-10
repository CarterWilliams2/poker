import { expect, test } from 'vitest'
import { handLog, type HandLog } from './log.ts'
import type { TableMessage } from './protocol.ts'

// Every recorded match, as the server sent it.
const SAMPLES = import.meta.glob<TableMessage[]>('../../fixtures/*.json', {
  eager: true,
  import: 'default',
})
const SPLIT_POT = SAMPLES['../../fixtures/split-pot.json']
const HEADS_UP = SAMPLES['../../fixtures/heads-up.json']
const SIX_SEATS = SAMPLES['../../fixtures/six-seats.json']

// Each street as its name and lines, with each line as "name text cards, hand: pot".
function written(log: HandLog | null) {
  return log!.streets.map(({ street, cards, lines }) => [
    [street, ...cards].join(' '),
    ...lines.map(
      ({ name, text, cards, hand, pot }) =>
        `${[name, text, ...cards].join(' ')}${hand ? `, ${hand}` : ''}: ${pot}`,
    ),
  ])
}

const latestOf = (log: HandLog | null) => [
  ...log!.streets.filter(({ latest }) => latest).map(({ street }) => street),
  ...log!.streets.flatMap(({ lines }) =>
    lines.filter(({ latest }) => latest).map(({ text }) => text),
  ),
]

test('there is nothing to log before the first hand', () => {
  expect(SPLIT_POT[0].type).toBe('match_start')
  expect(handLog(SPLIT_POT, 0)).toBeNull()
})

test('a hand starts with the blinds, and the pot after each', () => {
  const log = handLog(HEADS_UP, 1)
  expect(log!.hand).toBe(1)
  expect(written(log)).toEqual([
    ['preflop', 'Random 1 posts a small blind of 1: 1', 'Calling 2 posts a big blind of 2: 3'],
  ])
  expect(latestOf(log)).toEqual(['preflop', 'posts a small blind of 1', 'posts a big blind of 2'])
})

test('lists each action with the pot after it, marking the newest', () => {
  const log = handLog(SPLIT_POT, 4)
  expect(written(log)).toEqual([
    [
      'preflop',
      'Random 2 posts a small blind of 1: 1',
      'Calling 3 posts a big blind of 2: 3',
      'Random 1 raises to 10: 13',
      'Random 2 folds: 13',
      'Calling 3 calls 8: 21',
    ],
  ])
  expect(latestOf(log)).toEqual(['calls 8'])
})

test('each street gets its own heading with the cards it dealt, through to the showdown', () => {
  const log = handLog(SPLIT_POT, 9)
  expect(written(log)).toEqual([
    [
      'preflop',
      'Random 2 posts a small blind of 1: 1',
      'Calling 3 posts a big blind of 2: 3',
      'Random 1 raises to 10: 13',
      'Random 2 folds: 13',
      'Calling 3 calls 8: 21',
    ],
    ['flop KS KD KC'],
    ['turn 8C'],
    ['river 10D'],
    [
      'showdown',
      'Random 1 shows 7H 5S, Three Of A Kind: 21',
      'Calling 3 shows 6S 5D, Three Of A Kind: 21',
      'Calling 3 and Random 1 split 21: 0',
    ],
  ])
  expect(latestOf(log)).toEqual(['split 21'])
})

test('a new street is the newest thing until someone acts', () => {
  expect(latestOf(handLog(SPLIT_POT, 5))).toEqual(['flop'])
})

test('a pot with one winner is won, and the players who run out are listed', () => {
  const log = handLog(SPLIT_POT, 28)
  expect(written(log).at(-1)!.slice(-4)).toEqual([
    'Calling 3 wins 27: 2',
    'Calling 3 wins 2: 0',
    'Random 2 is out, in 3rd place: 0',
    'Random 1 is out, in 2nd place: 0',
  ])
})

test('names every winner of a pot split many ways', () => {
  const index = SIX_SEATS.findIndex((message) => message.type === 'pot')
  const lines = handLog(SIX_SEATS, index)!.streets.at(-1)!.lines
  expect(`${lines.at(-1)!.name} ${lines.at(-1)!.text}`).toMatch(
    /^Random 2, Random 3, Random 4, Random 5, Calling 6 and Aggressive 1 split \d+$/,
  )
})

test('places from 4th down end in th', () => {
  const full = SAMPLES['../../fixtures/full-table.json']
  const outs = full.flatMap((message, index) =>
    message.type === 'busted' ? [handLog(full, index)!.streets.at(-1)!.lines.at(-1)!.text] : [],
  )
  expect(outs).toContain('is out, in 8th place')
  expect(outs).toContain('is out, in 4th place')
  expect(outs.at(-1)).toBe('is out, in 2nd place')
})

test('a hand that ends with a fold has no showdown', () => {
  expect(HEADS_UP[3].type).toBe('pot')
  expect(written(handLog(HEADS_UP, 3))).toEqual([
    [
      'preflop',
      'Random 1 posts a small blind of 1: 1',
      'Calling 2 posts a big blind of 2: 3',
      'Random 1 folds: 3',
      'Calling 2 wins 3: 0',
    ],
  ])
})

test('the next hand starts a new log', () => {
  expect(HEADS_UP[4].type).toBe('hand_start')
  const log = handLog(HEADS_UP, 4)
  expect(log!.hand).toBe(2)
  expect(written(log)).toEqual([
    ['preflop', 'Calling 2 posts a small blind of 1: 1', 'Random 1 posts a big blind of 2: 3'],
  ])
})

test('the end of the match adds nothing, and keeps the last hand', () => {
  const last = HEADS_UP.length - 1
  expect(HEADS_UP[last].type).toBe('match_over')
  expect(written(handLog(HEADS_UP, last))).toEqual(written(handLog(HEADS_UP, last - 1)))
  expect(latestOf(handLog(HEADS_UP, last))).toEqual([])
})

test('logs everything that happens in every sample, once, with the pot as the table has it', () => {
  for (const messages of Object.values(SAMPLES)) {
    messages.forEach((message, index) => {
      const log = handLog(messages, index)
      if (message.table.hand === 0) return expect(log).toBeNull()
      const lines = log!.streets.flatMap(({ lines }) => lines)
      // From this hand's start, counting the two blinds for its first message.
      let start = index
      while (messages[start].type !== 'hand_start') start--
      const expected = messages.slice(start, index + 1).reduce((total, { type, ...rest }) => {
        if (type === 'hand_start') return total + 2
        if (type === 'showdown') return total + (rest as { hands: unknown[] }).hands.length
        return total + (['action', 'pot', 'busted'].includes(type) ? 1 : 0)
      }, 0)
      expect(lines).toHaveLength(expected)
      // The newest line's pot is the table's. A new street only moves bets into the middle, and the
      // pot counts them either way.
      expect(lines.at(-1)!.pot).toBe(message.table.pot)
      expect(log!.hand).toBe(message.table.hand)
    })
  }
})
