import sys
from pathlib import Path

# The UI reaches the engine only through this module, so if the engine is reorganized, this is the
# one file to change. The engine's modules sit at the repo root, two folders up from here, which
# isn't on the import path when the server runs from ui/.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from card import Card
from deck import Deck
from hand_evaluator import evaluate, hand_name
from match import MAX_PLAYERS, MIN_PLAYERS, Match
from simulate import AGENTS

# Everything the UI uses from the engine. Only public names, never ones starting with _.
__all__ = ["AGENTS", "Card", "Deck", "MAX_PLAYERS", "MIN_PLAYERS", "Match", "evaluate", "hand_name"]
