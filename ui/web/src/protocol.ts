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

// Most types of message have more fields of their own, which the web app doesn't use yet.
export type Message = { type: string; table: TableState }
