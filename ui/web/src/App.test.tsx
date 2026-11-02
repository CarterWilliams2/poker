import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import App from './App.tsx'

const FIRST = { hand: ['AS', 'KD'], board: ['2C', '3C', '4C', '5H', '10S'] }
const SECOND = { hand: ['QH', 'JH'], board: ['9D', '9S', '8C', '7D', '6H'] }

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

test('shows the hand and the board as cards', async () => {
  serverDeals(FIRST)
  render(<App />)
  const hand = await screen.findByRole('region', { name: 'Your hand' })
  const names = within(hand).getAllByRole('img').map((card) => card.getAttribute('aria-label'))
  expect(names).toEqual(['Ace of spades', 'King of diamonds'])
  const board = screen.getByRole('region', { name: 'Board' })
  expect(within(board).getAllByRole('img')).toHaveLength(5)
})

test('deals again when asked', async () => {
  const fetch = serverDeals(FIRST, SECOND)
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: 'Deal again' }))
  await screen.findByRole('img', { name: 'Queen of hearts' })
  expect(screen.queryByRole('img', { name: 'Ace of spades' })).toBeNull()
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
