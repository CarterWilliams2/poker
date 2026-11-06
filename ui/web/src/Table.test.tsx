import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, expect, test } from 'vitest'
import { cardName } from './cards.ts'
import type { SeatState, TableMessage, TableState } from './protocol.ts'
import Table from './Table.tsx'

// Every recorded match, as the server sent it.
const SAMPLES = Object.values(
  import.meta.glob<TableMessage[]>('../../fixtures/*.json', { eager: true, import: 'default' }),
)

afterEach(cleanup)

function seat(name: string, details: Partial<SeatState> = {}): SeatState {
  return { name, chips: 100, bet: 0, cards: [], folded: false, place: null, ...details }
}

function table(details: Partial<TableState> = {}): TableState {
  return {
    hand: 1,
    street: 'preflop',
    button: null,
    small_blind: null,
    big_blind: null,
    board: [],
    pot: 0,
    seats: [seat('Tuned 1'), seat('Random 2')],
    ...details,
  }
}

const seatOf = (name: string) => screen.getByRole('region', { name })

// The seats in the order they're drawn: every section of the page, apart from the table itself.
const seatsDrawn = () => screen.getAllByRole('region').slice(1)

// The cards in a section of the page, by the names a screen reader gives them.
function cardsIn(section: HTMLElement) {
  return within(section)
    .queryAllByRole('img', { name: / of / })
    .map((card) => card.getAttribute('aria-label'))
}

const stackIn = (seat: HTMLElement) => within(seat).getByTitle('Stack').textContent
const betIn = (seat: HTMLElement) => within(seat).queryByTitle('Bet')?.textContent
const potOnTable = () => Number(screen.getByText(/^Pot /).textContent!.replace('Pot ', ''))

test("draws each player's name, stack and cards", () => {
  render(
    <Table
      table={table({
        seats: [
          seat('Tuned 1', { chips: 95, cards: ['AS', '10H'] }),
          seat('Random 2', { chips: 7 }),
        ],
      })}
    />,
  )
  expect(stackIn(seatOf('Tuned 1'))).toBe('95')
  expect(cardsIn(seatOf('Tuned 1'))).toEqual(['Ace of spades', '10 of hearts'])
  expect(stackIn(seatOf('Random 2'))).toBe('7')
  expect(cardsIn(seatOf('Random 2'))).toEqual([])
})

test('shows a bet only for a player who has one', () => {
  render(<Table table={table({ seats: [seat('Tuned 1', { bet: 40 }), seat('Random 2')] })} />)
  expect(betIn(seatOf('Tuned 1'))).toBe('40')
  expect(betIn(seatOf('Random 2'))).toBeUndefined()
  // A bet of 0 draws nothing at all, rather than a stray 0.
  expect(seatOf('Random 2').textContent).toBe('Random 2100')
})

test('the pot leaves out the bets still in front of the players', () => {
  render(
    <Table
      table={table({ pot: 28, seats: [seat('Tuned 1', { bet: 6 }), seat('Random 2', { bet: 2 })] })}
    />,
  )
  expect(potOnTable()).toBe(20)
})

test('shows an empty pot too', () => {
  render(<Table table={table()} />)
  expect(potOnTable()).toBe(0)
})

test('the dealer button sits with the player who has it', () => {
  render(<Table table={table({ button: 'Random 2' })} />)
  expect(within(seatOf('Random 2')).getByRole('img', { name: 'Dealer button' })).toBeTruthy()
  expect(screen.getAllByRole('img', { name: 'Dealer button' })).toHaveLength(1)
})

test('there is no dealer button before the first hand', () => {
  render(<Table table={table({ button: null })} />)
  expect(screen.queryByRole('img', { name: 'Dealer button' })).toBeNull()
})

test('draws the board in the order it was dealt, and keeps room for the rest', () => {
  render(<Table table={table({ board: ['9S', '6H', '3D'] })} />)
  const board = screen.getByRole('group', { name: 'Board' })
  expect(cardsIn(board)).toEqual(['9 of spades', '6 of hearts', '3 of diamonds'])
  expect(board.children).toHaveLength(5)
})

test('a full board leaves no empty places', () => {
  render(<Table table={table({ board: ['9S', '6H', '3D', '10C', '2S'] })} />)
  const board = screen.getByRole('group', { name: 'Board' })
  expect(cardsIn(board)).toHaveLength(5)
  expect(board.children).toHaveLength(5)
})

test('puts each player in their own place around the table', () => {
  render(
    <Table
      table={table({
        seats: [seat('Tuned 1'), seat('Random 2'), seat('Tight 3'), seat('Calling 4')],
      })}
    />,
  )
  const direction = (name: string) => {
    const { style } = seatOf(name)
    // Adding 0 turns the -0 that rounding can give into a plain 0.
    return [style.getPropertyValue('--across'), style.getPropertyValue('--down')].map(
      (value) => Math.round(Number(value)) + 0,
    )
  }
  expect(direction('Tuned 1')).toEqual([0, 1])
  expect(direction('Random 2')).toEqual([-1, 0])
  expect(direction('Tight 3')).toEqual([0, -1])
  expect(direction('Calling 4')).toEqual([1, 0])
})

// These two draw the table over 100 times, which can take a while on a busy computer.
const MANY_TABLES = { timeout: 60_000 }

test('draws every sample state at every table size', MANY_TABLES, () => {
  const sizes = new Set<number>()
  for (const messages of SAMPLES) {
    for (const { table: state } of messages) {
      sizes.add(state.seats.length)
      render(<Table table={state} />)
      const seats = seatsDrawn()
      expect(seats.map((seat) => seat.getAttribute('aria-label'))).toEqual(
        state.seats.map(({ name }) => name),
      )
      state.seats.forEach(({ name, chips, bet, cards }, index) => {
        expect(stackIn(seats[index])).toBe(String(chips))
        expect(betIn(seats[index])).toBe(bet > 0 ? String(bet) : undefined)
        expect(cardsIn(seats[index])).toEqual(cards.map(cardName))
        expect(within(seats[index]).queryAllByLabelText('Dealer button')).toHaveLength(
          name === state.button ? 1 : 0,
        )
      })
      const board = screen.getByRole('group', { name: 'Board' })
      expect(cardsIn(board)).toEqual(state.board.map(cardName))
      cleanup()
    }
  }
  expect([...sizes].sort()).toEqual([2, 3, 4, 5, 6, 7, 8])
})

test('the chips drawn always add up to the chips the match started with', MANY_TABLES, () => {
  let betsAndPotTogether = false
  for (const messages of SAMPLES) {
    const inPlay = messages[0].table.seats.reduce((total, { chips }) => total + chips, 0)
    for (const { table: state } of messages) {
      render(<Table table={state} />)
      const drawn = seatsDrawn().map((seat) => Number(stackIn(seat)) + Number(betIn(seat) ?? 0))
      expect(drawn.reduce((total, chips) => total + chips, 0) + potOnTable()).toBe(inPlay)
      betsAndPotTogether ||= potOnTable() > 0 && state.seats.some(({ bet }) => bet > 0)
      cleanup()
    }
  }
  // The samples have to show a bet and a pot at the same moment for this to mean anything.
  expect(betsAndPotTogether).toBe(true)
})
