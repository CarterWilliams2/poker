import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { StrictMode } from 'react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { bubblesAt, pauseAfter, sweptBets } from './events.ts'
import type { TableMessage } from './protocol.ts'
import Table from './Table.tsx'
import Watch from './Watch.tsx'

// Every recorded match, as the server sent it.
const SAMPLES = import.meta.glob<TableMessage[]>('../../fixtures/*.json', {
  eager: true,
  import: 'default',
})
const HEADS_UP = SAMPLES['../../fixtures/heads-up.json']
const SPLIT_POT = SAMPLES['../../fixtures/split-pot.json']
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
  vi.useFakeTimers()
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})


// Opens the page and connects it to the server.
function watching() {
  const page = render(<Watch />)
  sockets[0].connect()
  return page
}

// The server sends a whole match at once.
function receiveAll(messages: TableMessage[], socket = sockets[0]) {
  for (const message of messages) socket.receive(message)
}

const wait = (ms: number) => act(() => vi.advanceTimersByTime(ms))

const drawnTable = () => screen.queryByRole('region', { name: 'Table' })
const status = () => screen.getByRole('heading', { name: 'Watch' }).nextElementSibling!.textContent
const button = (name: string) => screen.getByRole('button', { name }) as HTMLButtonElement
const potOnTable = () => screen.getByText(/^Pot /).textContent
const bubbleOf = (name: string) =>
  within(screen.getByRole('region', { name })).queryByTitle('Last action')

test('asks this address for a match, once connected', () => {
  render(<Watch />)
  expect(sockets).toHaveLength(1)
  expect(sockets[0].url).toBe(`ws://${location.host}/ws/watch`)
  expect(sockets[0].sent).toEqual([])
  sockets[0].connect()
  expect(sockets[0].sent).toEqual(['{"type":"start"}'])
})

test('says the match is starting until the first hand is shown', () => {
  watching()
  expect(status()).toBe('Starting the match…')
  expect(drawnTable()).toBeNull()

  sockets[0].receive(HEADS_UP[0])
  expect(status()).toBe('Starting the match…')
  expect(drawnTable()).toBeTruthy()

  sockets[0].receive(FIRST_HAND)
  expect(status()).toBe('Starting the match…')
  wait(pauseAfter(HEADS_UP[0]))
  expect(status()).toBe('Hand 1')
})

test('shows the first message as soon as it arrives', () => {
  watching()
  sockets[0].receive(FIRST_HAND)
  expect(status()).toBe('Hand 1')
})

test('plays a match that arrives all at once back one message at a time', () => {
  watching()
  receiveAll(HEADS_UP)
  expect(potOnTable()).toBe('Pot 0')
  wait(pauseAfter(HEADS_UP[0]) - 1)
  expect(status()).toBe('Starting the match…')
  wait(1)
  expect(status()).toBe('Hand 1')
  // The blinds are in.
  expect(screen.getAllByTitle('Bet').map((bet) => bet.textContent)).toEqual(['1', '2'])
})

test('the whole match takes as long as its pauses add up to', () => {
  watching()
  receiveAll(HEADS_UP)
  const pauses = HEADS_UP.slice(0, -1).map(pauseAfter)
  const total = pauses.reduce((sum, pause) => sum + pause, 0)
  // At a readable pace, this two-hand match takes over ten seconds.
  expect(total).toBeGreaterThan(10_000)
  for (const pause of pauses.slice(0, -1)) wait(pause)
  wait(pauses[pauses.length - 1] - 1)
  expect(status()).not.toMatch(/Match over/)
  wait(1)
  expect(status()).toBe('Match over after 2 hands')
})

test('redraws the table with every message in every sample', { timeout: 60_000 }, () => {
  for (const messages of Object.values(SAMPLES)) {
    const { unmount } = watching()
    receiveAll(messages)
    messages.forEach((message, index) => {
      const expected = render(
        <Table
          table={message.table}
          bubbles={bubblesAt(messages, index)}
          swept={sweptBets(messages[index - 1]?.table, message.table)}
        />,
      )
      const [drawn, wanted] = screen.getAllByRole('region', { name: 'Table' })
      expect(drawn.outerHTML).toBe(wanted.outerHTML)
      expected.unmount()
      wait(pauseAfter(message))
    })
    unmount()
    sockets = []
  }
})

test('keeps up with the hand number', () => {
  watching()
  receiveAll(HEADS_UP)
  wait(pauseAfter(HEADS_UP[0]))
  for (const message of HEADS_UP.slice(1, -1)) {
    expect(status()).toBe(`Hand ${message.table.hand}`)
    wait(pauseAfter(message))
  }
})

test('says what each player did in a bubble by their seat', () => {
  watching()
  receiveAll(HEADS_UP)
  wait(pauseAfter(HEADS_UP[0]))
  expect(bubbleOf('Random 1')).toBeNull()
  wait(pauseAfter(HEADS_UP[1]))
  expect(bubbleOf('Random 1')!.textContent).toBe('Folds')
  expect(bubbleOf('Random 1')!.className).toBe('bubble latest')
  expect(bubbleOf('Calling 2')).toBeNull()
})

test("slides the bets into the pot when a betting round ends, then they're gone", () => {
  watching()
  receiveAll(SPLIT_POT)
  for (const message of SPLIT_POT.slice(0, 13)) wait(pauseAfter(message))
  expect(SPLIT_POT[13].type).toBe('action')
  expect(document.querySelectorAll('.swept')).toHaveLength(0)

  wait(pauseAfter(SPLIT_POT[13]))
  expect(SPLIT_POT[14].type).toBe('street')
  const swept = [...document.querySelectorAll('.swept')]
  expect(swept.map((bet) => bet.textContent)).toEqual(['9', '9', '9'])
  // Only for show: the pot already counts them, and they aren't bets any more.
  expect(swept.every((bet) => bet.getAttribute('aria-hidden') === 'true')).toBe(true)
  expect(screen.queryAllByTitle('Bet')).toHaveLength(0)
  expect(potOnTable()).toBe('Pot 27')

  wait(pauseAfter(SPLIT_POT[14]))
  expect(document.querySelectorAll('.swept')).toHaveLength(0)
})

test('plays at the speed picked, which starts at 1×', () => {
  watching()
  receiveAll(HEADS_UP)
  const speeds = within(screen.getByRole('group', { name: 'Speed' })).getAllByRole('button')
  expect(speeds.map((speed) => speed.textContent)).toEqual(['½×', '1×', '2×', '4×'])
  const pressed = () => speeds.filter((speed) => speed.ariaPressed === 'true')
  expect(pressed()).toEqual([button('1×')])

  fireEvent.click(button('4×'))
  expect(pressed()).toEqual([button('4×')])
  wait(pauseAfter(HEADS_UP[0]) / 4)
  expect(status()).toBe('Hand 1')

  fireEvent.click(button('½×'))
  expect(pressed()).toEqual([button('½×')])
  wait(pauseAfter(HEADS_UP[1]) * 2 - 1)
  expect(bubbleOf('Random 1')).toBeNull()
  wait(1)
  expect(bubbleOf('Random 1')!.textContent).toBe('Folds')
})

test('animations keep up with the speed', () => {
  watching()
  sockets[0].receive(FIRST_HAND)
  const speedOnTable = () => drawnTable()!.style.getPropertyValue('--speed')
  expect(speedOnTable()).toBe('1')
  fireEvent.click(button('2×'))
  expect(speedOnTable()).toBe('2')
})

test('speeding up counts the time already spent on a message', () => {
  watching()
  receiveAll(HEADS_UP)
  wait(pauseAfter(HEADS_UP[0]))
  expect(status()).toBe('Hand 1')
  // Halfway through the new hand's pause, 4× wants only a quarter of it, so it's already done.
  wait(pauseAfter(HEADS_UP[1]) / 2)
  expect(bubbleOf('Random 1')).toBeNull()
  fireEvent.click(button('4×'))
  expect(bubbleOf('Random 1')!.textContent).toBe('Folds')
})

test('a message that arrives late shows as soon as the one before has had its time', () => {
  watching()
  sockets[0].receive(HEADS_UP[0])
  wait(5000)
  sockets[0].receive(FIRST_HAND)
  expect(status()).toBe('Hand 1')
  // And the next one still waits its turn.
  sockets[0].receive(HEADS_UP[2])
  wait(pauseAfter(FIRST_HAND) - 1)
  expect(bubbleOf('Random 1')).toBeNull()
  wait(1)
  expect(bubbleOf('Random 1')).toBeTruthy()
})

test('pauses and carries on', () => {
  watching()
  receiveAll(HEADS_UP)
  fireEvent.click(button('Pause'))
  wait(60_000)
  expect(status()).toBe('Starting the match…')
  expect(button('Play')).toBeTruthy()

  fireEvent.click(button('Play'))
  // It's had more than long enough already.
  expect(status()).toBe('Hand 1')
  expect(button('Pause')).toBeTruthy()
  wait(pauseAfter(FIRST_HAND) - 1)
  expect(bubbleOf('Random 1')).toBeNull()
  wait(1)
  expect(bubbleOf('Random 1')).toBeTruthy()
})

test('steps one message at a time, pausing first', () => {
  watching()
  receiveAll(HEADS_UP)
  fireEvent.click(button('Step'))
  expect(status()).toBe('Hand 1')
  expect(button('Play')).toBeTruthy()
  wait(60_000)
  expect(status()).toBe('Hand 1')
  fireEvent.click(button('Step'))
  expect(bubbleOf('Random 1')!.textContent).toBe('Folds')
  for (const _ of HEADS_UP.slice(3)) fireEvent.click(button('Step'))
  expect(status()).toBe('Match over after 2 hands')
  expect(button('Step').disabled).toBe(true)
})

test('there is nothing to step to until the next message arrives', () => {
  watching()
  sockets[0].receive(HEADS_UP[0])
  expect(button('Step').disabled).toBe(true)
  sockets[0].receive(FIRST_HAND)
  expect(button('Step').disabled).toBe(false)
})

test('the playback controls only show once there is a table', () => {
  watching()
  expect(screen.queryByRole('group', { name: 'Playback' })).toBeNull()
  sockets[0].receive(HEADS_UP[0])
  expect(screen.getByRole('group', { name: 'Playback' })).toBeTruthy()
})

test('says when the match is over and how long it took', () => {
  watching()
  sockets[0].receive(MATCH_OVER)
  expect(status()).toBe('Match over after 2 hands')
})

test('says one hand, not one hands', () => {
  watching()
  sockets[0].receive({ ...MATCH_OVER, hands_played: 1 })
  expect(status()).toBe('Match over after 1 hand')
})

test('the server closing the connection after the match is not a problem', () => {
  watching()
  receiveAll(HEADS_UP)
  sockets[0].drop()
  for (const _ of HEADS_UP) wait(5000)
  expect(screen.queryByRole('alert')).toBeNull()
  expect(status()).toBe('Match over after 2 hands')
})

test('says so when the server cannot be reached', () => {
  render(<Watch />)
  sockets[0].drop()
  expect(screen.getByRole('alert').textContent).toContain('python ui/play.py')
  expect(screen.queryByText('Starting the match…')).toBeNull()
  expect(drawnTable()).toBeNull()
})

test('a connection lost during a match is reported once what did arrive has played', () => {
  watching()
  receiveAll(HEADS_UP.slice(0, 3))
  sockets[0].drop()
  expect(screen.queryByRole('alert')).toBeNull()
  wait(pauseAfter(HEADS_UP[0]))
  expect(screen.queryByRole('alert')).toBeNull()
  wait(pauseAfter(HEADS_UP[1]))
  expect(screen.getByRole('alert').textContent).toContain('python ui/play.py')
  // The last table that arrived stays on screen.
  expect(bubbleOf('Random 1')!.textContent).toBe('Folds')
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
  receiveAll(HEADS_UP)
  unmount()
  expect(sockets[0].readyState).toBe(FakeSocket.CLOSED)
  expect(sockets[0].onmessage).toBeNull()
  expect(sockets[0].onclose).toBeNull()
  // Nothing is left waiting to play.
  expect(vi.getTimerCount()).toBe(0)
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
test('only one match runs under StrictMode, at the same pace', () => {
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
  receiveAll(HEADS_UP, sockets[1])
  expect(status()).toBe('Starting the match…')
  wait(pauseAfter(HEADS_UP[0]) - 1)
  expect(status()).toBe('Starting the match…')
  wait(1)
  expect(status()).toBe('Hand 1')
})

test('logs the hand beside the table, keeping up with the playback', () => {
  watching()
  receiveAll(HEADS_UP)
  const log = () => screen.getByRole('complementary', { name: 'Hand log' })
  const lines = () => within(log()).queryAllByRole('listitem').map((line) => line.textContent)
  expect(log().textContent).toContain('The first hand is about to be dealt.')

  wait(pauseAfter(HEADS_UP[0]))
  expect(within(log()).getByRole('heading', { name: 'Hand 1' })).toBeTruthy()
  expect(lines()).toEqual([
    'Random 1 posts a small blind of 11',
    'Calling 2 posts a big blind of 23',
  ])

  wait(pauseAfter(HEADS_UP[1]))
  expect(lines().at(-1)).toBe('Random 1 folds3')
  wait(pauseAfter(HEADS_UP[2]))
  expect(lines().at(-1)).toBe('Calling 2 wins 30')

  // A new hand starts a new log.
  wait(pauseAfter(HEADS_UP[3]))
  expect(within(log()).getByRole('heading', { name: 'Hand 2' })).toBeTruthy()
  expect(lines()).toHaveLength(2)
})

test('the log stays on the last hand once the match is over', () => {
  watching()
  receiveAll(HEADS_UP)
  for (const _ of HEADS_UP) fireEvent.click(button('Step'))
  expect(status()).toBe('Match over after 2 hands')
  const log = screen.getByRole('complementary', { name: 'Hand log' })
  expect(within(log).getByRole('heading', { name: 'Hand 2' })).toBeTruthy()
  expect(within(log).getAllByRole('listitem').at(-1)!.textContent).toBe(
    'Random 1 is out, in 2nd place0',
  )
})
