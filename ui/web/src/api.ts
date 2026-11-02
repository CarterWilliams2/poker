export type Deal = { hand: string[]; board: string[] }

// Asks the server for two hole cards and a five-card board from the engine's deck.
export async function fetchDeal(): Promise<Deal> {
  const response = await fetch('/api/deal')
  if (!response.ok) {
    throw new Error(`The server answered ${response.status}`)
  }
  return response.json()
}
