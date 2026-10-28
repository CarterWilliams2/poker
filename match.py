import random
from typing import Callable
from agent import Agent
from game import Game, Action
from player import Player
from table_view import TableView

MIN_PLAYERS = 2
MAX_PLAYERS = 8

class IllegalActionError(Exception):
    """An agent returned an action the rules don't allow. The game would otherwise ask it forever."""

class Match:
    """Seats 2 to 8 agents at one table and plays hands until one player has all the chips.

    Every seat is driven by an agent, so the same match works for random bots now and AI
    agents later. on_action is called after each decision with (player, action, amount, game).
    rng shuffles the deck; pass a seeded one for repeatable deals.
    """

    def __init__(self, seats: list[tuple[str, Agent]], starting_chips: int,
                 small_blind: int, big_blind: int,
                 on_action: Callable[[Player, Action, int, Game], None] | None = None,
                 rng: random.Random | None = None):
        if not MIN_PLAYERS <= len(seats) <= MAX_PLAYERS:
            raise ValueError(f"A match needs {MIN_PLAYERS} to {MAX_PLAYERS} players, got {len(seats)}.")
        names = [name for name, _ in seats]
        if len(set(names)) != len(names):
            raise ValueError("Every player needs a different name.")
        self.players = [Player(name, starting_chips) for name in names]
        self._agents = {player: agent for player, (_, agent) in zip(self.players, seats)}
        self._on_action = on_action
        self.game = Game(self.players, small_blind, big_blind, self._decide, rng)
        self.hands_played = 0
        # Busted players, in the order they ran out of chips.
        self.eliminated: list[Player] = []

    def _decide(self, player: Player, game: Game):
        action, amount = self._agents[player](TableView.for_player(player, game))
        if not game.is_legal(player, action, amount):
            raise IllegalActionError(f"{player.name} tried to {action.value} {amount}.")
        if self._on_action:
            self._on_action(player, action, amount, game)
        return action, amount

    def is_over(self):
        return self.game.is_over()

    def play_hand(self):
        """Plays one hand and returns the pots as (amount, winners) pairs."""
        results = self.game.play_hand()
        self.hands_played += 1
        busted = [p for p in self.players if p.chips == 0 and p not in self.eliminated]
        # Whoever started the hand with more chips places higher, so goes out later.
        busted.sort(key=lambda p: p.committed_this_hand)
        self.eliminated.extend(busted)
        return results

    def run(self, max_hands: int | None = None,
            on_hand: Callable[[int, list[tuple[int, list[Player]]]], None] | None = None):
        """Plays until one player is left or max_hands is reached, and returns the standings."""
        while not self.is_over() and (max_hands is None or self.hands_played < max_hands):
            results = self.play_hand()
            if on_hand:
                on_hand(self.hands_played, results)
        return self.standings()

    def standings(self):
        """Players still in, from most chips to fewest, then busted players, last out first."""
        alive = [p for p in self.players if p.chips > 0]
        alive.sort(key=lambda p: p.chips, reverse=True)
        return alive + self.eliminated[::-1]
