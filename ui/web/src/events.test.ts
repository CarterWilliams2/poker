import { expect, test } from 'vitest'
import { bubblesAt, describeAction, pauseAfter, sweptBets } from './events.ts'
import type { ActionMessage, TableMessage } from './protocol.ts'

// Every recorded match, as the server sent it.
const SAMPLES = import.meta.glob<TableMessage[]>('../../fixtures/*.json', {
  eager: true,
  import: 'default',
})
const SPLIT_POT = SAMPLES['../../fixtures/split-pot.json']
const HEADS_UP = SAMPLES['../../fixtures/heads-up.json']

// What describeAction says for messages[index] in a sample, which has to be an action.
function said(messages: TableMessage[], index: number) {
  expect(messages[index].type).toBe('action')
  return describeAction(messages[index] as ActionMessage, messages[index - 1].table)
}

const textOf = (bubbles: ReturnType<typeof bubblesAt>) =>
  Object.fromEntries(Object.entries(bubbles).map(([name, { text }]) => [name, text]))

const latestOf = (bubbles: ReturnType<typeof bubblesAt>) =>
  Object.keys(bubbles).filter((name) => bubbles[name].latest)

test('says what each type of action did', () => {
  expect(said(HEADS_UP, 2)).toBe('Folds')
  expect(said(SPLIT_POT, 15)).toBe('Checks')
})

test('raising the blinds is a raise to the new total', () => {
  // Random 1 pushes all 10 chips in over the big blind of 2.
  expect(said(SPLIT_POT, 2)).toBe('Raises to 10')
})

test('the first bet in a betting round is a bet, not a raise', () => {
  // On the river, after Calling 3 checks.
  expect(said(SPLIT_POT, 22)).toBe('Bets 1')
})

test('a call says how much more the player put in, not their whole bet', () => {
  // The big blind already had 2 in, so calling 10 costs 8.
  expect(said(SPLIT_POT, 4)).toBe('Calls 8')
  // With nothing in yet, the two are the same.
  expect(said(SPLIT_POT, 23)).toBe('Calls 1')
})

test('describes every action in every sample', () => {
  const seen = new Set<string>()
  for (const messages of Object.values(SAMPLES)) {
    messages.forEach((message, index) => {
      if (message.type !== 'action') return
      const text = said(messages, index)
      expect(text).toMatch(/^(Folds|Checks|Calls [1-9]\d*|Bets [1-9]\d*|Raises to [1-9]\d*)$/)
      seen.add(text.split(' ')[0])
    })
  }
  expect([...seen].sort()).toEqual(['Bets', 'Calls', 'Checks', 'Folds', 'Raises'])
})

test("shows each player's last action this betting round, marking the newest", () => {
  let bubbles = bubblesAt(SPLIT_POT, 3)
  expect(textOf(bubbles)).toEqual({ 'Random 1': 'Raises to 10', 'Random 2': 'Folds' })
  expect(latestOf(bubbles)).toEqual(['Random 2'])

  bubbles = bubblesAt(SPLIT_POT, 4)
  expect(textOf(bubbles)).toEqual({
    'Random 1': 'Raises to 10',
    'Random 2': 'Folds',
    'Calling 3': 'Calls 8',
  })
  expect(latestOf(bubbles)).toEqual(['Calling 3'])
})

test('a player who acts again replaces their bubble', () => {
  expect(textOf(bubblesAt(SPLIT_POT, 21))).toEqual({ 'Calling 3': 'Checks' })
  expect(textOf(bubblesAt(SPLIT_POT, 22))).toEqual({ 'Calling 3': 'Checks', 'Random 1': 'Bets 1' })
  expect(textOf(bubblesAt(SPLIT_POT, 23))).toEqual({ 'Calling 3': 'Calls 1', 'Random 1': 'Bets 1' })
})

test('a new street starts with no bubbles', () => {
  expect(SPLIT_POT[14].type).toBe('street')
  expect(bubblesAt(SPLIT_POT, 14)).toEqual({})
  expect(textOf(bubblesAt(SPLIT_POT, 15))).toEqual({ 'Calling 3': 'Checks' })
})

test('so do the showdown and a new hand', () => {
  expect(SPLIT_POT[24].type).toBe('showdown')
  expect(bubblesAt(SPLIT_POT, 24)).toEqual({})
  expect(SPLIT_POT[10].type).toBe('hand_start')
  expect(bubblesAt(SPLIT_POT, 10)).toEqual({})
  expect(bubblesAt(SPLIT_POT, 0)).toEqual({})
})

test('bubbles from a hand that ended before the flop stay out of the next one', () => {
  // Hand 1 ended with a fold before the flop, so both hands' tables say preflop.
  expect(HEADS_UP[4].type).toBe('hand_start')
  expect([HEADS_UP[3].table.street, HEADS_UP[4].table.street]).toEqual(['preflop', 'preflop'])
  expect(bubblesAt(HEADS_UP, 4)).toEqual({})
  expect(textOf(bubblesAt(HEADS_UP, 5))).toEqual({ 'Calling 2': 'Calls 1' })
})

test('after a fold ends the hand, the bubbles stay while the pot is paid, none of them new', () => {
  expect(HEADS_UP[3].type).toBe('pot')
  const bubbles = bubblesAt(HEADS_UP, 3)
  expect(textOf(bubbles)).toEqual({ 'Random 1': 'Folds' })
  expect(latestOf(bubbles)).toEqual([])
})

test('bets go into the middle when a betting round ends', () => {
  expect(sweptBets(SPLIT_POT[13].table, SPLIT_POT[14].table)).toEqual({
    'Random 1': 9,
    'Random 2': 9,
    'Calling 3': 9,
  })
  // At the showdown too, and only from the players who had a bet.
  expect(sweptBets(SPLIT_POT[23].table, SPLIT_POT[24].table)).toEqual({
    'Random 1': 1,
    'Calling 3': 1,
  })
})

test('and when everyone else folds, including the folded blind', () => {
  expect(sweptBets(HEADS_UP[2].table, HEADS_UP[3].table)).toEqual({ 'Random 1': 1, 'Calling 2': 2 })
})

test('nothing is swept while betting goes on, or into a new hand', () => {
  expect(sweptBets(SPLIT_POT[3].table, SPLIT_POT[4].table)).toEqual({})
  expect(sweptBets(SPLIT_POT[14].table, SPLIT_POT[15].table)).toEqual({})
  // The blinds go in at the start of a hand, and nothing leaves the table.
  expect(sweptBets(SPLIT_POT[9].table, SPLIT_POT[10].table)).toEqual({})
  expect(sweptBets(undefined, SPLIT_POT[0].table)).toEqual({})
})

test('bets from one hand are never swept into the next', () => {
  // The same two tables as above, but as if the second were a new hand.
  const before = SPLIT_POT[13].table
  expect(sweptBets(before, { ...SPLIT_POT[14].table, hand: 3 })).toEqual({})
})

test('every message stays on screen a while, apart from the last', () => {
  for (const messages of Object.values(SAMPLES)) {
    for (const message of messages.slice(0, -1)) {
      expect(pauseAfter(message)).toBeGreaterThanOrEqual(500)
    }
  }
  expect(pauseAfter(HEADS_UP[HEADS_UP.length - 1])).toBe(0)
})

test('there is more to take in at a showdown than after an action', () => {
  expect(pauseAfter(SPLIT_POT[24])).toBeGreaterThan(pauseAfter(SPLIT_POT[23]))
})
