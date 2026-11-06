# Protocol

How the web app and the server talk: JSON over a WebSocket, where every message is one object with a `type`. Change this file whenever a message changes, and re-record the samples (see [Samples](#samples)).

Cards are strings, rank then suit: `"10H"`, `"AS"`.

## Watching bots play: `/ws/watch`

1. The browser opens the socket and sends `start`.
2. The server sends one message for each thing that happens, from `match_start` to `match_over`.
3. The server closes the socket with code 1000. If the browser closes it first, the match stops there.

The server sends each message as soon as it happens, so a whole match can arrive in under a second. Playing them back at a readable pace is the web app's job.

### `start`

```json
{"type": "start", "bots": ["tuned", "random"], "chips": 100, "small_blind": 1, "big_blind": 2, "seed": 7, "max_hands": 1000}
```

| Field | Default | Meaning |
|---|---|---|
| `bots` | One of each, up to 8 | The bot in each seat, 2 to 8 of them, by their names in the engine's `simulate.AGENTS`. |
| `chips` | 100 | Each player's starting stack. |
| `small_blind`, `big_blind` | 1, 2 | The blinds, at least 1 each, and the small blind can't be more than the big blind. |
| `seed` | Picked by the server | The same `start` with the same `seed` gets exactly the same messages. |
| `max_hands` | 1000 | Ends the match after this many hands, in case nobody has all the chips by then. |

Only `type` is required. Anything else gets an `error` and the server keeps waiting for a good `start`:

```json
{"type": "error", "message": "chips: Input should be greater than or equal to 1"}
```

### `table`

Every message from `match_start` on carries the whole table as it stands right after that message's event, so the web app can draw any message without remembering the ones before it.

```json
{"hand": 2, "street": "river", "button": "Random 2", "small_blind": "Calling 3", "big_blind": "Random 1",
 "board": ["9S", "6H", "3D", "10C", "2S"], "pot": 28,
 "seats": [{"name": "Random 1", "chips": 0, "bet": 1, "cards": ["7C", "QC"], "folded": false, "place": null},
           {"name": "Random 2", "chips": 0, "bet": 0, "cards": ["6D", "5S"], "folded": false, "place": null},
           {"name": "Calling 3", "chips": 2, "bet": 0, "cards": ["5H", "4S"], "folded": false, "place": null}]}
```

| Field | Meaning |
|---|---|
| `hand` | The hand number, from 1. 0 before the first hand. |
| `street` | `preflop`, `flop`, `turn`, `river` or `showdown`, and `null` before the first hand. A hand that ends with everyone else folding stays on the street it ended on. |
| `button`, `small_blind`, `big_blind` | The names of the players in those positions this hand, and `null` before the first hand. With two players left, the button is also the small blind. |
| `board` | The cards dealt so far. |
| `pot` | Every chip bet this hand, including the `bet`s still in front of the players. The chips to draw in the middle are `pot` minus every seat's `bet`. |
| `seats` | Every player, busted ones too, in the same order for the whole match. |

And in each seat:

| Field | Meaning |
|---|---|
| `name` | The bot and the seat number, like `Tuned 1`. |
| `chips` | The player's stack, not counting their `bet`. |
| `bet` | The chips in front of them this betting round. |
| `cards` | Their two cards, which watching shows for every player. Empty once they fold or while they're busted. |
| `folded` | Whether they've folded this hand. |
| `place` | Where they finished, once they've busted, and `null` until then. |

A player is all-in when `chips` is 0, `folded` is false and `place` is `null`.

Two things hold at every message, and the tests check them: every seat's `chips` plus the `pot` always add up to the chips the match started with, and nobody's `chips` go below 0.

### Messages from the server

Each of these also has a `table`.

| `type` | Other fields | What happened |
|---|---|---|
| `match_start` | `seed` | The match is set up, and hasn't dealt yet. `seed` replays it, whether it was chosen or picked by the server. |
| `hand_start` | | The cards are dealt and the blinds are in. |
| `action` | `name`, `action`, `amount` | A player decided. `action` is `fold`, `check`, `call` or `raise`. `amount` is their total bet this round after a call or raise, and 0 for a check or fold. |
| `street` | `street`, `cards` | A betting round ended and a new `street` was dealt, `flop`, `turn` or `river`. `cards` are the new ones. Bets in `table` are cleared into the pot. |
| `showdown` | `hands` | Two or more players are left after the river. `hands` lists each one as `{"name": "Tuned 1", "cards": ["10H", "QD"], "hand": "Two Pair"}`. |
| `pot` | `amount`, `winners` | A pot was paid out to the players named in `winners`. `table` shows it moved from `pot` to their `chips`. |
| `busted` | `name`, `place` | A player ran out of chips and finished in `place`. |
| `match_over` | `hands_played`, `standings` | One player has all the chips, or `max_hands` ran out. `standings` lists everyone from first to last as `{"name": "Tuned 1", "chips": 200, "place": 1}`. |

Each hand goes in this order:

1. `hand_start`.
2. `action`s and `street`s as they happen. Once all but one of the players are all-in, nobody is asked anything, so the remaining `street`s follow with no `action`s between them. If the blinds put everyone all-in, the hand has no `action`s at all.
3. `showdown`, unless everyone else folded. Then there's no showdown and the board stays as it was.
4. One or more `pot`s, in the order the engine pays them: the main pot, then any side pots.
5. A `busted` for each player who ran out, worst place first.

Some things about `pot` the web app can't tell from these messages:

- **A bet nobody could call comes back as a `pot` with one winner.** The engine doesn't say which pots are like that.
- **A pot that doesn't split evenly gives its odd chips to the first player in `winners`.**

## Samples

`fixtures/` has real matches recorded from the server, for the server and web tests to check against. Each file is a JSON array of the messages from `match_start` to `match_over`, with one message per line. `server/fixtures.py` lists what each one shows.

A server test fails when the samples no longer match what the server sends. After changing a message on purpose, re-record them from `ui/`:

```sh
../.venv/bin/python -m server.fixtures
```
