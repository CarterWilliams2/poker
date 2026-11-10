import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import HandLog from './HandLog.tsx'
import { handLog } from './log.ts'
import type { TableMessage } from './protocol.ts'

const SPLIT_POT = import.meta.glob<TableMessage[]>('../../fixtures/split-pot.json', {
  eager: true,
  import: 'default',
})['../../fixtures/split-pot.json']

afterEach(cleanup)

const panel = () => screen.getByRole('complementary', { name: 'Hand log' })
const streetNamed = (name: string) => within(panel()).getByRole('region', { name })
const linesIn = (section: HTMLElement) =>
  within(section)
    .getAllByRole('listitem')
    .map((line) => line.textContent)

test('says the first hand is coming before there is one', () => {
  render(<HandLog log={null} />)
  expect(within(panel()).getByRole('heading', { name: 'Hand log' })).toBeTruthy()
  expect(panel().textContent).toContain('The first hand is about to be dealt.')
  expect(within(panel()).queryAllByRole('listitem')).toHaveLength(0)
})

test('lists each street under its own heading, with the pot after each line', () => {
  render(<HandLog log={handLog(SPLIT_POT, 9)} />)
  expect(within(panel()).getByRole('heading', { name: 'Hand 1' })).toBeTruthy()
  expect(
    within(panel())
      .getAllByRole('region')
      .map((section) => section.getAttribute('aria-label')),
  ).toEqual(['Preflop', 'Flop', 'Turn', 'River', 'Showdown'])
  expect(linesIn(streetNamed('Preflop'))).toEqual([
    'Random 2 posts a small blind of 11',
    'Calling 3 posts a big blind of 23',
    'Random 1 raises to 1013',
    'Random 2 folds13',
    'Calling 3 calls 821',
  ])
  const pots = within(streetNamed('Preflop'))
    .getAllByRole('listitem')
    .map((line) => line.lastElementChild!.textContent)
  expect(pots).toEqual(['1', '3', '13', '13', '21'])
})

test('draws the cards each street dealt, by the names a screen reader gives them', () => {
  render(<HandLog log={handLog(SPLIT_POT, 9)} />)
  const cards = (name: string) =>
    within(within(streetNamed(name)).getByRole('heading'))
      .getAllByRole('img')
      .map((card) => card.getAttribute('aria-label'))
  expect(cards('Flop')).toEqual(['King of spades', 'King of diamonds', 'King of clubs'])
  expect(cards('River')).toEqual(['10 of diamonds'])
  expect(within(streetNamed('Flop')).getByRole('heading').textContent).toBe('FlopK♠︎K♦︎K♣︎')
})

test("shows each player's cards and hand at the showdown, then who won", () => {
  render(<HandLog log={handLog(SPLIT_POT, 9)} />)
  const showdown = streetNamed('Showdown')
  expect(linesIn(showdown)).toEqual([
    'Random 1 shows7♥︎5♠︎, Three Of A Kind21',
    'Calling 3 shows6♠︎5♦︎, Three Of A Kind21',
    'Calling 3 and Random 1 split 210',
  ])
  const shown = within(within(showdown).getAllByRole('listitem')[0]).getAllByRole('img')
  expect(shown.map((card) => card.getAttribute('aria-label'))).toEqual([
    '7 of hearts',
    '5 of spades',
  ])
  expect(shown[0].className).toBe('log-card red')
  expect(shown[1].className).toBe('log-card')
})

test('marks what has just happened', () => {
  const { rerender } = render(<HandLog log={handLog(SPLIT_POT, 4)} />)
  const marked = () => [...panel().querySelectorAll('.latest')].map((line) => line.textContent)
  expect(marked()).toEqual(['Calling 3 calls 821'])
  rerender(<HandLog log={handLog(SPLIT_POT, 5)} />)
  expect(marked()).toEqual(['FlopK♠︎K♦︎K♣︎'])
})

// jsdom doesn't lay anything out, so this stands in for the browser's scrolling.
function watchScrolling() {
  const lines = panel().querySelector('.hand-log-lines')!
  const scrolledTo = vi.fn()
  Object.defineProperty(lines, 'scrollHeight', { get: () => 500 })
  Object.defineProperty(lines, 'scrollTop', { set: scrolledTo, get: () => 0 })
  return scrolledTo
}

test('keeps the newest line in view', () => {
  const { rerender } = render(<HandLog log={handLog(SPLIT_POT, 3)} />)
  const scrolledTo = watchScrolling()
  rerender(<HandLog log={handLog(SPLIT_POT, 4)} />)
  expect(scrolledTo).toHaveBeenCalledExactlyOnceWith(500)
  // A new street with no lines yet counts too.
  rerender(<HandLog log={handLog(SPLIT_POT, 5)} />)
  expect(scrolledTo).toHaveBeenCalledTimes(2)
})

test('leaves the scrolling alone when nothing new has been logged', () => {
  const { rerender } = render(<HandLog log={handLog(SPLIT_POT, 4)} />)
  const scrolledTo = watchScrolling()
  // The table changes with each message, and the page redraws with it.
  rerender(<HandLog log={handLog(SPLIT_POT, 4)} />)
  expect(scrolledTo).not.toHaveBeenCalled()
})

test('a new hand with as many lines as the last still scrolls', () => {
  const { rerender } = render(<HandLog log={handLog(SPLIT_POT, 1)} />)
  const scrolledTo = watchScrolling()
  rerender(<HandLog log={{ ...handLog(SPLIT_POT, 1)!, hand: 2 }} />)
  expect(scrolledTo).toHaveBeenCalledOnce()
})
