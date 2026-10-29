import argparse
import random
from aggressive_agent import AggressiveAgent
from calling_station_agent import CallingStationAgent
from match import MIN_PLAYERS, MAX_PLAYERS
from hand_strength_agent import TUNED_SETTINGS, HandStrengthAgent
from random_agent import RandomAgent
from simulation import CashSimulation, Simulation

# Agents that can be picked by name. New agents (an AI agent, say) get added here.
AGENTS = {
    "random": lambda rng: RandomAgent(rng),
    "calling": lambda rng: CallingStationAgent(),
    "aggressive": lambda rng: AggressiveAgent(),
    "strength": lambda rng: HandStrengthAgent(rng),
    "tuned": lambda rng: HandStrengthAgent(rng, **TUNED_SETTINGS),
}

def main():
    parser = argparse.ArgumentParser(
        description="Play many games between bots and count the wins, or with --hands, play "
                    "single hands from fresh stacks and measure big blinds won per 100 hands.")
    parser.add_argument("-g", "--games", type=int, default=100, help="games to play (default 100)")
    parser.add_argument("--hands", type=int, default=None,
                        help="measure chips won over this many deals instead of counting wins")
    parser.add_argument("--no-duplicate", action="store_true",
                        help="with --hands, play each deal once instead of once from every seat")
    parser.add_argument("-n", "--players", type=int, default=MAX_PLAYERS,
                        help=f"number of random bots, {MIN_PLAYERS} to {MAX_PLAYERS} "
                             f"(default {MAX_PLAYERS}); ignored with --agents")
    parser.add_argument("--agents", nargs="+", choices=sorted(AGENTS), metavar="AGENT",
                        help=f"the agent in each seat, e.g. --agents random random "
                             f"(choices: {', '.join(sorted(AGENTS))})")
    parser.add_argument("--chips", type=int, default=100, help="starting chips (default 100)")
    parser.add_argument("--max-hands", type=int, default=1000,
                        help="hands before a game goes to the chip leader (default 1000)")
    parser.add_argument("--seed", type=int, default=None, help="seed for repeatable results")
    args = parser.parse_args()

    kinds = args.agents or ["random"] * args.players
    if not MIN_PLAYERS <= len(kinds) <= MAX_PLAYERS:
        parser.error(f"need {MIN_PLAYERS} to {MAX_PLAYERS} agents, got {len(kinds)}")
    if args.games < 1:
        parser.error("--games must be at least 1")
    if args.hands is not None and args.hands < 1:
        parser.error("--hands must be at least 1")

    rng = random.Random(args.seed)
    seats = [(f"{kind.capitalize()} {i + 1}", AGENTS[kind](random.Random(rng.random())))
             for i, kind in enumerate(kinds)]
    deck_rng = random.Random(rng.random())
    if args.hands is not None:
        measure_chips(seats, args, deck_rng)
    else:
        count_wins(seats, args, deck_rng)

def count_wins(seats, args, rng):
    def on_game(number, match):
        if number % max(1, args.games // 10) == 0 or number == args.games:
            print(f"  {number}/{args.games} games played", flush=True)

    simulation = Simulation(seats, args.chips, small_blind=1, big_blind=2,
                            max_hands=args.max_hands, rng=rng)
    results = simulation.run(args.games, on_game)

    print(f"\n{results.games} games, {results.hands} hands, {results.draws} draws\n")
    width = max(len(name) for name in results.records)
    print(f"{'Agent':<{width}}  {'Wins':>6}  {'Win %':>6}  {'Avg place':>9}")
    for name, record in results.ranked():
        print(f"{name:<{width}}  {record.wins:>6}  {record.win_rate:>6.1%}  {record.average_place:>9.2f}")

def measure_chips(seats, args, rng):
    def on_deal(number):
        if number % max(1, args.hands // 10) == 0 or number == args.hands:
            print(f"  {number}/{args.hands} deals played", flush=True)

    simulation = CashSimulation(seats, args.chips, small_blind=1, big_blind=2,
                                duplicate=not args.no_duplicate, rng=rng)
    results = simulation.run(args.hands, on_deal)

    print(f"\n{args.hands} deals, {results.hands} hands, stacks of {args.chips} reset every hand\n")
    width = max(len(name) for name in results.records)
    print(f"{'Agent':<{width}}  {'bb/100':>8}  {'95% interval':>18}")
    for name, record in results.ranked():
        low, high = record.bb_per_100 - record.margin, record.bb_per_100 + record.margin
        print(f"{name:<{width}}  {record.bb_per_100:>8.1f}  {f'{low:.1f} to {high:.1f}':>18}")

if __name__ == "__main__":
    main()
