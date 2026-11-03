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
