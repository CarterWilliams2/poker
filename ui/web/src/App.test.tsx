import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import App from './App.tsx'

// Deals the way /api/deal sends them: your hand first, then your opponent's.
const FIRST = {
  hands: [
    { cards: ['AS', 'KD'], name: 'Pair', wins: true },
    { cards: ['QH', 'JH'], name: 'High Card', wins: false },
  ],
  board: ['2C', '3C', 'KC', '5H', '9S'],
}
const SECOND = {
  hands: [
    { cards: ['10D', '10H'], name: 'Pair', wins: false },
    { cards: ['8C', '8D'], name: 'Three Of A Kind', wins: true },
  ],
  board: ['8H', '4S', '6D', 'JC', '2D'],
}
// The board is a royal flush, so it plays for both hands.
const TIE = {
  hands: [
    { cards: ['2H', '3D'], name: 'Straight Flush', wins: true },
    { cards: ['4C', '5H'], name: 'Straight Flush', wins: true },
  ],
  board: ['10S', 'JS', 'QS', 'KS', 'AS'],
}

// Makes fetch answer with each deal in turn, the way the server's /api/deal does.
function serverDeals(...deals: object[]) {
  const fetch = vi.fn()
  for (const deal of deals) {
    fetch.mockResolvedValueOnce({ ok: true, status: 200, json: async () => deal })
  }
  vi.stubGlobal('fetch', fetch)
  return fetch
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// The cards in a section of the page, by the names a screen reader gives them.
function cardsIn(section: HTMLElement) {
  return within(section).getAllByRole('img').map((card) => card.getAttribute('aria-label'))
}

test('shows both hands and the board as cards', async () => {
  serverDeals(FIRST)
  render(<App />)
  const yours = await screen.findByRole('region', { name: 'Your hand' })
  expect(cardsIn(yours)).toEqual(['Ace of spades', 'King of diamonds'])
  const theirs = screen.getByRole('region', { name: "Opponent's hand" })
  expect(cardsIn(theirs)).toEqual(['Queen of hearts', 'Jack of hearts'])
  expect(cardsIn(screen.getByRole('region', { name: 'Board' }))).toHaveLength(5)
})

test('names each hand and marks the winner', async () => {
  serverDeals(FIRST)
  render(<App />)
  const yours = await screen.findByRole('region', { name: 'Your hand' })
  expect(within(yours).getByText('Pair')).toBeTruthy()
  expect(within(yours).getByText('Wins')).toBeTruthy()
  const theirs = screen.getByRole('region', { name: "Opponent's hand" })
  expect(within(theirs).getByText('High Card')).toBeTruthy()
  expect(within(theirs).queryByText('Wins')).toBeNull()
})

test('marks both hands when they tie', async () => {
  serverDeals(TIE)
  render(<App />)
  for (const name of ['Your hand', "Opponent's hand"]) {
    const hand = await screen.findByRole('region', { name })
    expect(within(hand).getByText('Straight Flush')).toBeTruthy()
    expect(within(hand).getByText('Tie')).toBeTruthy()
    expect(within(hand).queryByText('Wins')).toBeNull()
  }
})

test('deals again when asked', async () => {
  const fetch = serverDeals(FIRST, SECOND)
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: 'Deal again' }))
  await screen.findByRole('img', { name: '10 of diamonds' })
  expect(screen.queryByRole('img', { name: 'Ace of spades' })).toBeNull()
  const theirs = screen.getByRole('region', { name: "Opponent's hand" })
  expect(within(theirs).getByText('Three Of A Kind')).toBeTruthy()
  expect(within(theirs).getByText('Wins')).toBeTruthy()
  expect(fetch).toHaveBeenCalledTimes(2)
  expect(fetch).toHaveBeenCalledWith('/api/deal')
})

test('says so when the server cannot be reached, and lets you try again', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
  render(<App />)
  expect((await screen.findByRole('alert')).textContent).toContain('python ui/play.py')
  expect(screen.getByRole('button', { name: 'Deal again' })).toHaveProperty('disabled', false)
})

test('treats an error answer from the server the same way', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
  render(<App />)
  await screen.findByRole('alert')
  expect(screen.queryByRole('img')).toBeNull()
})
