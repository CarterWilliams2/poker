import { act, cleanup, render, screen } from '@testing-library/react'
import { StrictMode } from 'react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import type { TableMessage } from './protocol.ts'
import Table from './Table.tsx'
import Watch from './Watch.tsx'

// Every recorded match, as the server sent it.
const SAMPLES = import.meta.glob<TableMessage[]>('../../fixtures/*.json', {
  eager: true,
  import: 'default',
})
const HEADS_UP = SAMPLES['../../fixtures/heads-up.json']
const FIRST_HAND = HEADS_UP[1]
const MATCH_OVER = HEADS_UP[HEADS_UP.length - 1]

// Stands in for the browser's WebSocket, so that a test decides what the server does and when.
class FakeSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 3

  readyState = FakeSocket.CONNECTING
  sent: string[] = []
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  url: string

  constructor(url: string) {
    this.url = url
    sockets.push(this)
  }

  send(text: string) {
    this.sent.push(text)
  }

  close() {
    this.readyState = FakeSocket.CLOSED
  }

  connect() {
    this.readyState = FakeSocket.OPEN
    this.onopen?.()
  }

  receive(message: object) {
    act(() => this.onmessage?.({ data: JSON.stringify(message) }))
  }

  drop() {
    this.readyState = FakeSocket.CLOSED
    act(() => this.onclose?.())
  }
}

let sockets: FakeSocket[]

beforeEach(() => {
  sockets = []
  vi.stubGlobal('WebSocket', FakeSocket)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// Opens the page and connects it to the server.
function watching() {
  const page = render(<Watch />)
  sockets[0].connect()
  return page
}

const drawnTable = () => screen.queryByRole('region', { name: 'Table' })

test('asks this address for a match, once connected', () => {
  render(<Watch />)
  expect(sockets).toHaveLength(1)
  expect(sockets[0].url).toBe(`ws://${location.host}/ws/watch`)
  expect(sockets[0].sent).toEqual([])
  sockets[0].connect()
  expect(sockets[0].sent).toEqual(['{"type":"start"}'])
})

test('says the match is starting until the first hand is dealt', () => {
  watching()
  expect(screen.getByText('Starting the match…')).toBeTruthy()
  expect(drawnTable()).toBeNull()

  sockets[0].receive(HEADS_UP[0])
  expect(screen.getByText('Starting the match…')).toBeTruthy()
  expect(drawnTable()).toBeTruthy()

  sockets[0].receive(FIRST_HAND)
  expect(screen.getByText('Hand 1')).toBeTruthy()
  expect(screen.queryByText('Starting the match…')).toBeNull()
})

test('redraws the table with every message in every sample', { timeout: 60_000 }, () => {
  for (const messages of Object.values(SAMPLES)) {
    const { unmount } = watching()
    for (const message of messages) {
      sockets[sockets.length - 1].receive(message)
      const expected = render(<Table table={message.table} />)
      const [drawn, wanted] = screen.getAllByRole('region', { name: 'Table' })
      expect(drawn.outerHTML).toBe(wanted.outerHTML)
      expected.unmount()
    }
    unmount()
    sockets = []
  }
})

test('keeps up with the hand number', () => {
  watching()
  for (const message of HEADS_UP.slice(1, -1)) {
    sockets[0].receive(message)
    expect(screen.getByText(`Hand ${message.table.hand}`)).toBeTruthy()
  }
})

test('says when the match is over and how long it took', () => {
  watching()
  sockets[0].receive(MATCH_OVER)
  expect(screen.getByText('Match over after 2 hands')).toBeTruthy()
  expect(screen.queryByText(/^Hand /)).toBeNull()
})

test('says one hand, not one hands', () => {
  watching()
  sockets[0].receive({ ...MATCH_OVER, hands_played: 1 })
  expect(screen.getByText('Match over after 1 hand')).toBeTruthy()
})

test('the server closing the connection after the match is not a problem', () => {
  watching()
  sockets[0].receive(MATCH_OVER)
  sockets[0].drop()
  expect(screen.queryByRole('alert')).toBeNull()
  expect(screen.getByText('Match over after 2 hands')).toBeTruthy()
})

test('says so when the server cannot be reached', () => {
  render(<Watch />)
  sockets[0].drop()
  expect(screen.getByRole('alert').textContent).toContain('python ui/play.py')
  expect(screen.queryByText('Starting the match…')).toBeNull()
  expect(drawnTable()).toBeNull()
})

test('keeps the last table when the connection is lost during a match', () => {
  watching()
  sockets[0].receive(FIRST_HAND)
  const table = drawnTable()!.outerHTML
  sockets[0].drop()
  expect(screen.getByRole('alert').textContent).toContain('python ui/play.py')
  expect(drawnTable()!.outerHTML).toBe(table)
  expect(screen.queryByText(/Match over/)).toBeNull()
})

test('shows an error from the server, and stays on it', () => {
  watching()
  sockets[0].receive({ type: 'error', message: 'chips: Input should be greater than or equal to 1' })
  expect(screen.getByRole('alert').textContent).toBe(
    'chips: Input should be greater than or equal to 1',
  )
  expect(drawnTable()).toBeNull()
  sockets[0].drop()
  expect(screen.getByRole('alert').textContent).toContain('chips: Input')
})

test('leaving the page closes the connection and stops listening', () => {
  const { unmount } = watching()
  sockets[0].receive(FIRST_HAND)
  unmount()
  expect(sockets[0].readyState).toBe(FakeSocket.CLOSED)
  expect(sockets[0].onmessage).toBeNull()
  expect(sockets[0].onclose).toBeNull()
})

test('leaving before it connects closes the connection as soon as it does', () => {
  const { unmount } = render(<Watch />)
  unmount()
  expect(sockets[0].readyState).toBe(FakeSocket.CONNECTING)
  sockets[0].connect()
  expect(sockets[0].readyState).toBe(FakeSocket.CLOSED)
  expect(sockets[0].sent).toEqual([])
})

// In development React starts everything twice to shake out bugs like two matches running at once.
test('only one match runs under StrictMode', () => {
  render(
    <StrictMode>
      <Watch />
    </StrictMode>,
  )
  expect(sockets).toHaveLength(2)
  for (const socket of sockets) {
    socket.connect()
  }
  expect(sockets[0].sent).toEqual([])
  expect(sockets[0].readyState).toBe(FakeSocket.CLOSED)
  expect(sockets[1].sent).toEqual(['{"type":"start"}'])
  sockets[1].receive(FIRST_HAND)
  expect(screen.getByText('Hand 1')).toBeTruthy()
})
