import type { ActionMessage, TableMessage, TableState } from './protocol.ts'

// How long each type of message stays on screen before the next one, in milliseconds at normal
// speed. Long enough to read what happened, and longer where there's more to take in.
const PAUSES: Record<TableMessage['type'], number> = {
  match_start: 600,
  hand_start: 1200,
  action: 1000,
  street: 1200,
  showdown: 2500,
  pot: 1800,
  busted: 1500,
  match_over: 0,
}

export const pauseAfter = (message: TableMessage) => PAUSES[message.type]

// What a player did, as their bubble on the table says it, like "Raises to 40". `before` is the
// table just before they acted.
export function describeAction(message: ActionMessage, before: TableState) {
  switch (message.action) {
    case 'fold':
      return 'Folds'
    case 'check':
      return 'Checks'
    case 'call': {
      // The amount is their whole bet this round, so a call says how much more they put in.
      const bet = before.seats.find((seat) => seat.name === message.name)!.bet
      return `Calls ${message.amount - bet}`
    }
    case 'raise':
      // The blinds count as bets, so raising them is a raise, not the first bet.
      return before.seats.some((seat) => seat.bet > 0)
        ? `Raises to ${message.amount}`
        : `Bets ${message.amount}`
  }
}

// Each player's last action this betting round, by name, as the table stands after
// messages[index]. `latest` marks the one that's just happened.
export type Bubbles = Record<string, { text: string; latest: boolean }>

export function bubblesAt(messages: TableMessage[], index: number): Bubbles {
  const { hand, street } = messages[index].table
  const bubbles: Bubbles = {}
  // Back to where this betting round started. Going further would find the round before's.
  for (let at = index; at > 0; at--) {
    const message = messages[at]
    if (message.table.hand !== hand || message.table.street !== street) break
    if (message.type === 'action' && !(message.name in bubbles)) {
      bubbles[message.name] = {
        text: describeAction(message, messages[at - 1].table),
        latest: at === index,
      }
    }
  }
  return bubbles
}

// The bets swept into the middle between two tables, by the name of the player who made them.
export function sweptBets(before: TableState | undefined, after: TableState) {
  const swept: Record<string, number> = {}
  if (!before || before.hand !== after.hand) return swept
  for (const [index, { name, bet }] of before.seats.entries()) {
    if (bet > 0 && after.seats[index].bet === 0) swept[name] = bet
  }
  return swept
}
