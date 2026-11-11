// The server's messages, as ui/PROTOCOL.md describes them.

export type SeatState = {
  name: string
  chips: number
  bet: number
  cards: string[]
  folded: boolean
  place: number | null
}

export type TableState = {
  hand: number
  street: string | null
  button: string | null
  small_blind: string | null
  big_blind: string | null
  board: string[]
  pot: number
  seats: SeatState[]
}

export type ActionMessage = {
  type: 'action'
  name: string
  action: 'fold' | 'check' | 'call' | 'raise'
  amount: number
  table: TableState
}

// A player's cards at the showdown, and the name of the best hand they make, like "Two Pair".
export type ShownHand = { name: string; cards: string[]; hand: string }

// Some types of message have more fields of their own, which the web app doesn't use yet.
export type TableMessage =
  | ActionMessage
  | { type: 'street'; street: string; cards: string[]; table: TableState }
  | { type: 'showdown'; hands: ShownHand[]; table: TableState }
  | { type: 'pot'; amount: number; winners: string[]; table: TableState }
  | { type: 'busted'; name: string; place: number; table: TableState }
  | { type: 'match_over'; hands_played: number; table: TableState }
  | { type: 'match_start' | 'hand_start'; table: TableState }

export type Message = TableMessage | { type: 'error'; message: string }
