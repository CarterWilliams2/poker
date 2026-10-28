import argparse
import random
from game import Action
from match import Match, MIN_PLAYERS, MAX_PLAYERS
from random_agent import RandomAgent

def main():
    parser = argparse.ArgumentParser(description="Watch random bots play each other.")
    parser.add_argument("-n", "--players", type=int, default=MAX_PLAYERS,
                        help=f"number of bots, {MIN_PLAYERS} to {MAX_PLAYERS} (default {MAX_PLAYERS})")
    parser.add_argument("--chips", type=int, default=100, help="starting chips (default 100)")
    parser.add_argument("--max-hands", type=int, default=None, help="stop after this many hands")
    parser.add_argument("--seed", type=int, default=None, help="seed for a repeatable match")
    parser.add_argument("-v", "--verbose", action="store_true", help="print every action")
    args = parser.parse_args()
    if not MIN_PLAYERS <= args.players <= MAX_PLAYERS:
        parser.error(f"--players must be {MIN_PLAYERS} to {MAX_PLAYERS}")

    rng = random.Random(args.seed)
    seats = [(f"Bot {i + 1}", RandomAgent(random.Random(rng.random()))) for i in range(args.players)]

    def on_action(player, action, amount, game):
        if match.hands_played not in headed:
            headed.add(match.hands_played)
            print(f"\nHand {match.hands_played + 1}:")
        if action == Action.RAISE:
            verb = "bets" if game.current_bet == 0 else "raises to"
            print(f"  [{game.street.value}] {player.name} {verb} {amount}")
        else:
            print(f"  [{game.street.value}] {player.name} {action.value}s")

    def on_hand(number, results):
        for amount, winners in results:
            print(f"Hand {number}: {amount} to {', '.join(p.name for p in winners)}")
        out = [p.name for p in match.eliminated if p.name not in reported]
        for name in out:
            print(f"  {name} is out.")
            reported.add(name)

    reported = set()
    headed = set()
    match = Match(seats, args.chips, small_blind=1, big_blind=2,
                  on_action=on_action if args.verbose else None, rng=random.Random(rng.random()))
    standings = match.run(args.max_hands, on_hand)

    print(f"\nFinal standings after {match.hands_played} hands:")
    for place, player in enumerate(standings, start=1):
        print(f"{place}. {player.name}: {player.chips}")

if __name__ == "__main__":
    main()
