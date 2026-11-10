import type { CSSProperties } from 'react'
import Card from './Card.tsx'
import type { Bubbles } from './events.ts'
import type { SeatState, TableState } from './protocol.ts'
import { seatDirection } from './seats.ts'

const BOARD_SIZE = 5

type TableProps = {
  table: TableState
  // What each player last did this betting round, from bubblesAt in events.ts.
  bubbles?: Bubbles
  // Bets that have just gone into the middle, by player, which slide there from in front of them.
  swept?: Record<string, number>
  // How fast it's playing, from SPEEDS in Playback.tsx. Animations keep up with it.
  speed?: number
}

// The poker table as one message from the server describes it. It fills the width it's given.
export default function Table({ table, bubbles = {}, swept = {}, speed = 1 }: TableProps) {
  // Bets stay in front of the players until the betting round ends, so aren't in the middle yet.
  const middle = table.pot - table.seats.reduce((total, seat) => total + seat.bet, 0)
  return (
    <section
      className="poker-table"
      aria-label="Table"
      style={{ '--speed': speed } as CSSProperties}
    >
      <div className="felt">
        <div className="middle">
          <p className="pot">Pot {middle}</p>
          <div className="board" role="group" aria-label="Board">
            {table.board.map((card) => (
              <Card key={card} card={card} />
            ))}
            {/* Keeps the cards in place as the next ones are dealt. */}
            {Array.from({ length: BOARD_SIZE - table.board.length }, (_, index) => (
              <div key={index} className="card empty" />
            ))}
          </div>
        </div>
        {table.seats.map((seat, index) => (
          <Seat
            key={seat.name}
            seat={seat}
            direction={seatDirection(index, table.seats.length)}
            hasButton={seat.name === table.button}
            bubble={bubbles[seat.name]}
            swept={swept[seat.name]}
          />
        ))}
      </div>
    </section>
  )
}

type SeatProps = {
  seat: SeatState
  direction: { across: number; down: number }
  hasButton: boolean
  bubble?: Bubbles[string]
  swept?: number
}

// One player. styles.css uses the direction to place them around the table, with their bet and the
// dealer button in front of them, towards the middle.
function Seat({ seat, direction, hasButton, bubble, swept }: SeatProps) {
  const place = { '--across': direction.across, '--down': direction.down } as CSSProperties
  return (
    <section className="seat" aria-label={seat.name} style={place}>
      <div className="seat-cards">
        {seat.cards.map((card) => (
          <Card key={card} card={card} />
        ))}
      </div>
      <div className="nameplate">
        <span className="seat-name">{seat.name}</span>
        <span className="stack" title="Stack">
          {seat.chips}
        </span>
        {bubble && (
          <span className={bubble.latest ? 'bubble latest' : 'bubble'} title="Last action">
            {bubble.text}
          </span>
        )}
      </div>
      {seat.bet > 0 && (
        <span className="bet" title="Bet">
          {seat.bet}
        </span>
      )}
      {/* Only there to be seen moving. The pot already counts these chips. */}
      {swept !== undefined && (
        <span className="bet swept" aria-hidden="true">
          {swept}
        </span>
      )}
      {hasButton && (
        <span className="dealer-button" role="img" aria-label="Dealer button">
          D
        </span>
      )}
    </section>
  )
}
