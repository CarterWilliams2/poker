import argparse
import random
from match import MIN_PLAYERS, MAX_PLAYERS
from random_agent import RandomAgent
from simulation import Simulation

# Agents that can be picked by name. New agents (an AI agent, say) get added here.
AGENTS = {
    "random": lambda rng: RandomAgent(rng),
}

def main():
    parser = argparse.ArgumentParser(description="Play many games between bots and count the wins.")
    parser.add_argument("-g", "--games", type=int, default=100, help="games to play (default 100)")
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

    rng = random.Random(args.seed)
    if args.seed is not None:
        random.seed(args.seed)  # The deck shuffles with the global random module.
    seats = [(f"{kind.capitalize()} {i + 1}", AGENTS[kind](random.Random(rng.random())))
             for i, kind in enumerate(kinds)]

    def on_game(number, match):
        if number % max(1, args.games // 10) == 0 or number == args.games:
            print(f"  {number}/{args.games} games played", flush=True)

    simulation = Simulation(seats, args.chips, small_blind=1, big_blind=2, max_hands=args.max_hands)
    results = simulation.run(args.games, on_game)

    print(f"\n{results.games} games, {results.hands} hands, {results.draws} draws\n")
    width = max(len(name) for name in results.records)
    print(f"{'Agent':<{width}}  {'Wins':>6}  {'Win %':>6}  {'Avg place':>9}")
    for name, record in results.ranked():
        print(f"{name:<{width}}  {record.wins:>6}  {record.win_rate:>6.1%}  {record.average_place:>9.2f}")

if __name__ == "__main__":
    main()
