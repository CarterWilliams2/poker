import argparse
import random
from hand_strength_agent import HandStrengthAgent
from tuning import Parameter, Tuner

DEFAULTS = {"preflop_raise": 10, "preflop_call": 7, "postflop_raise": 0.75,
            "call_margin": 0.0, "raise_size": 1.0}

PARAMETERS = [
    Parameter("preflop_raise", 1, 5, 20),
    Parameter("preflop_call", 1, -1, 20),
    Parameter("postflop_raise", 0.05, 0.5, 1.0),
    Parameter("call_margin", 0.05, -0.2, 0.5),
    Parameter("raise_size", 0.25, 0.25, 3.0),
]

def main():
    parser = argparse.ArgumentParser(
        description="Tune the hand strength agent's settings by playing them against each other.")
    parser.add_argument("--rounds", type=int, default=5, help="most rounds to run (default 5)")
    parser.add_argument("--deals", type=int, default=1000,
                        help="duplicate deals per trial (default 1000)")
    parser.add_argument("--check-deals", type=int, default=4000,
                        help="fresh deals for the final check against the defaults (default 4000)")
    parser.add_argument("--samples", type=int, default=100,
                        help="equity samples per decision (default 100)")
    parser.add_argument("--seed", type=int, default=None, help="seed for repeatable results")
    args = parser.parse_args()

    def make_agent(settings, rng):
        return HandStrengthAgent(rng, samples=args.samples, **settings)

    def on_trial(trial):
        change = ", ".join(f"{name}={value}" for name, value in trial.settings.items()
                           if value != best_so_far[name])
        verdict = "kept" if trial.accepted else "rejected"
        print(f"  round {trial.round}: {change:<22} {trial.bb_per_100:+7.1f} "
              f"± {trial.margin:.1f} bb/100  {verdict}", flush=True)
        if trial.accepted:
            best_so_far.update(trial.settings)

    best_so_far = dict(DEFAULTS)
    tuner = Tuner(make_agent, PARAMETERS, args.deals, rng=random.Random(args.seed))
    print(f"Tuning from {DEFAULTS}")
    tuned = tuner.tune(DEFAULTS, args.rounds, on_trial)

    print(f"\nTuned settings: {tuned}")
    if tuned != DEFAULTS:
        check = Tuner(make_agent, PARAMETERS, args.check_deals,
                      rng=random.Random(None if args.seed is None else args.seed + 1)
                      ).compare(0, tuned, DEFAULTS)
        print(f"Against the defaults over {args.check_deals} fresh deals: "
              f"{check.bb_per_100:+.1f} ± {check.margin:.1f} bb/100")

if __name__ == "__main__":
    main()
