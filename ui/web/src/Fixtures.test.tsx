import { cleanup, render, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, test } from 'vitest'
import { cardName } from './cards.ts'
import Fixtures from './Fixtures.tsx'
import type { Message } from './protocol.ts'

const SAMPLES = import.meta.glob<Message[]>('../../fixtures/*.json', {
  eager: true,
  import: 'default',
})

// Asking for elements by role is slow on a page this big, so these tests go straight to them.
let page: HTMLElement

beforeEach(() => {
  page = render(<Fixtures />).container
})

afterEach(cleanup)

// Looks through more than 100 tables, which can take a while on a busy computer.
test('draws every message in every sample, in order', { timeout: 60_000 }, () => {
  expect(Object.keys(SAMPLES)).toContain('../../fixtures/heads-up.json')
  for (const [path, messages] of Object.entries(SAMPLES)) {
    const name = path.split('/').pop()!.replace('.json', '')
    const figures = page.querySelectorAll(`[id="${name}"] figure`)
    expect(figures).toHaveLength(messages.length)
    messages.forEach(({ type, table }, index) => {
      const figure = figures[index] as HTMLElement
      expect(figure.querySelector('figcaption')!.textContent).toContain(`"type":"${type}"`)
      const board = within(within(figure).getByLabelText('Board')).queryAllByRole('img')
      expect(board.map((card) => card.getAttribute('aria-label'))).toEqual(
        table.board.map(cardName),
      )
      for (const seat of table.seats) {
        const stack = within(within(figure).getByLabelText(seat.name)).getByTitle('Stack')
        expect(stack.textContent).toBe(String(seat.chips))
      }
    })
  }
})

test('says what happened in each state, without repeating the table', () => {
  const captions = [...page.querySelectorAll(`[id="heads-up"] figcaption`)].map(
    (caption) => caption.textContent,
  )
  expect(captions[0]).toBe('1. {"type":"match_start","seed":576}')
  expect(captions[2]).toBe('3. {"type":"action","name":"Random 1","action":"fold","amount":0}')
  for (const caption of captions) {
    expect(caption).not.toContain('"table"')
  }
})

test('goes through every table size, smallest first', () => {
  const headings = [...page.querySelectorAll('h2')].map((heading) => heading.textContent)
  expect(headings.map((heading) => Number(heading!.match(/(\d+) seats/)![1]))).toEqual([
    2, 3, 4, 5, 6, 7, 8,
  ])
  expect(headings[0]).toBe('heads-up: 2 seats, 16 states')
})

test('links to each sample', () => {
  const links = [...page.querySelectorAll('nav a')]
  expect(links).toHaveLength(Object.keys(SAMPLES).length)
  for (const link of links) {
    expect(page.querySelector(link.getAttribute('href')!)).toBeTruthy()
  }
})
