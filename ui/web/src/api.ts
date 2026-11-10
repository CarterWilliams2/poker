import type { Message } from './protocol.ts'

// A player's two cards, the name of the best hand they make with the board, like "Full House",
// and whether it wins. When hands tie for the best, they all win.
export type Hand = { cards: string[]; name: string; wins: boolean }

export type Deal = { hands: Hand[]; board: string[] }

// Asks the server for two hands and a five-card board from the engine's deck, with each hand
// named and the winner marked.
export async function fetchDeal(): Promise<Deal> {
  const response = await fetch('/api/deal')
  if (!response.ok) {
    throw new Error(`The server answered ${response.status}`)
  }
  return response.json()
}

// Asks the server to play a match between bots. Calls onMessage with each message it sends, and
// onClose when the connection ends or can't be made, which also happens after the match is over.
// Returns a function that stops watching.
export function watchMatch(onMessage: (message: Message) => void, onClose: () => void) {
  const socket = new WebSocket(`ws://${location.host}/ws/watch`)
  socket.onopen = () => socket.send(JSON.stringify({ type: 'start' }))
  socket.onmessage = (event) => onMessage(JSON.parse(event.data))
  socket.onclose = onClose
  return () => {
    socket.onmessage = socket.onclose = null
    // Closing a socket that's still connecting logs an error in the browser's console.
    if (socket.readyState === WebSocket.CONNECTING) {
      socket.onopen = () => socket.close()
    } else {
      socket.close()
    }
  }
}
