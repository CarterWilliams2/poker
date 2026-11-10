import { bubblesAt, type Bubbles } from './events.ts'
import type { TableMessage } from './protocol.ts'
import Table from './Table.tsx'

// Every recorded match in ui/fixtures, smallest table first.
const SAMPLES = Object.entries(
  import.meta.glob<TableMessage[]>('../../fixtures/*.json', { eager: true, import: 'default' }),
)
  .map(([path, messages]) => ({
    name: path.split('/').pop()!.replace('.json', ''),
    seats: messages[0].table.seats.length,
    messages,
  }))
  .sort((a, b) => a.seats - b.seats)

// A page for reviewing the table: it draws it for every message in every sample.
export default function Fixtures() {
  return (
    <main className="fixtures">
      <h1>Sample states</h1>
      <p>
        The table as it stands after each message in the matches recorded in{' '}
        <code>ui/fixtures</code>.
      </p>
      <nav>
        {SAMPLES.map(({ name }) => (
          <a key={name} href={`#${name}`}>
            {name}
          </a>
        ))}
      </nav>
      {SAMPLES.map(({ name, seats, messages }) => (
        <section key={name} id={name} aria-label={name}>
          <h2>
            {name}: {seats} seats, {messages.length} states
          </h2>
          <div className="fixture-states">
            {messages.map((message, index) => (
              <State
                key={index}
                number={index + 1}
                message={message}
                bubbles={bubblesAt(messages, index)}
              />
            ))}
          </div>
        </section>
      ))}
    </main>
  )
}

type StateProps = { number: number; message: TableMessage; bubbles: Bubbles }

// One message: what happened, then the table as it stands afterwards, with what each player last
// did this betting round.
function State({ number, message, bubbles }: StateProps) {
  const { table, ...event } = message
  return (
    <figure className="fixture-state">
      <figcaption>
        {number}. <code>{JSON.stringify(event)}</code>
      </figcaption>
      <Table table={table} bubbles={bubbles} />
    </figure>
  )
}
