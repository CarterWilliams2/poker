import json
import random
from typing import Callable, Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from server.cards import card_text
from server.engine import AGENTS, MAX_PLAYERS, MIN_PLAYERS, Match, evaluate, hand_name

# How many cards are on the board once each street has been dealt.
BOARD_SIZES = {"flop": 3, "turn": 4, "river": 5}

class WatchSettings(BaseModel):
    """The start message, which chooses the match. ui/PROTOCOL.md describes each field."""
    # Strict so that "100" isn't taken for 100, and a misspelled field is an error, not ignored.
    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["start"]
    bots: list[str] = Field(default_factory=lambda: list(AGENTS)[:MAX_PLAYERS],
                            min_length=MIN_PLAYERS, max_length=MAX_PLAYERS)
    chips: int = Field(default=100, ge=1)
    small_blind: int = Field(default=1, ge=1)
    big_blind: int = Field(default=2, ge=1)
    seed: int | None = None
    max_hands: int = Field(default=1000, ge=1)

    @field_validator("bots")
    @classmethod
    def bots_exist(cls, bots: list[str]):
        for bot in bots:
            if bot not in AGENTS:
                raise ValueError(f"there's no bot called {bot!r}, choose from "
                                 f"{', '.join(sorted(AGENTS))}")
        return bots

    @model_validator(mode="after")
    def blinds_in_order(self):
        if self.small_blind > self.big_blind:
            raise ValueError("small_blind can't be more than big_blind")
        return self

def describe(problem: dict):
    """One thing pydantic found wrong, as the field's name and what's wrong with it."""
    return ": ".join([*map(str, problem["loc"]), problem["msg"].removeprefix("Value error, ")])

def parse_start(text: str):
    """The settings in a start message. Raises ValueError saying what's wrong with them."""
    try:
        return WatchSettings.model_validate_json(text)
    except ValidationError as error:
        raise ValueError("; ".join(map(describe, error.errors()))) from None

def card_texts(cards):
    return [card_text(card) for card in cards]

class MatchReporter:
    """Plays a match between bots and reports it to send, one JSON message per thing that happens.

    The engine plays a whole hand at once, so this takes a look at the game whenever a bot is about
    to decide, and again when the hand ends, and reports what has happened since the last look.
    _table is the table as of the last message. It can't simply be read from the game, because the
    game may have moved on: a call that ends a betting round is only seen once the next street has
    cleared the bets, and the last action of a hand only once the winners have been paid.
    """

    def __init__(self, settings: WatchSettings, seed: int, send: Callable[[str], None]):
        self._max_hands = settings.max_hands
        self._seed = seed
        self._send = send
        # Seeds the bots and the deck the way simulate.py does.
        rng = random.Random(seed)
        seats = [(f"{bot.capitalize()} {number}",
                  self._looking_first(AGENTS[bot](random.Random(rng.random()))))
                 for number, bot in enumerate(settings.bots, start=1)]
        self._match = Match(seats, settings.chips, settings.small_blind, settings.big_blind,
                            rng=random.Random(rng.random()))
        self._seats = {player.name: {"name": player.name, "chips": player.chips, "bet": 0,
                                     "cards": [], "folded": False, "place": None}
                       for player in self._match.players}
        self._table = {"hand": 0, "street": None, "button": None, "small_blind": None,
                       "big_blind": None, "board": [], "pot": 0,
                       "seats": list(self._seats.values())}
        # What each player had when this hand started. The engine pays the winners before the last
        # look at a hand, but committed_this_hand still says what each player put in.
        self._stacks = {player.name: player.chips for player in self._match.players}
        self._hand_started = False
        self._actions_reported = 0

    def _looking_first(self, agent):
        def decide(view):
            self._look()
            return agent(view)
        return decide

    def play(self):
        self._report("match_start", seed=self._seed)
        standings = self._match.run(self._max_hands, self._finish_hand)
        self._report("match_over", hands_played=self._match.hands_played,
                     standings=[{"name": player.name, "chips": player.chips, "place": place}
                                for place, player in enumerate(standings, start=1)])

    def _report(self, kind: str, **details):
        self._send(json.dumps({"type": kind, **details, "table": self._table},
                              separators=(",", ":")))

    def _look(self):
        """Reports everything that has happened since the last look. That can't be more than one
        action, because the game asks for each one, but it can be several streets: nobody is
        asked anything once all but one of the players are all-in."""
        game = self._match.game
        if not self._hand_started:
            self._start_hand()
        for player, _, action, amount in game.history[self._actions_reported:]:
            self._report_action(player, action.value, amount)
            self._actions_reported += 1
        board = card_texts(game.community_cards)
        for street, size in BOARD_SIZES.items():
            if len(self._table["board"]) < size <= len(board):
                self._report_street(street, board[:size])

    def _start_hand(self):
        game = self._match.game
        seated = game.seated
        # Nobody has acted yet, so only the blinds have put chips in. Seats go from the button, and
        # the small blind comes before the big blind even when the button is the small blind.
        small_blind, big_blind = [p.name for p in seated if p.committed_this_hand > 0]
        self._table.update(hand=self._table["hand"] + 1, street="preflop", button=seated[0].name,
                           small_blind=small_blind, big_blind=big_blind, board=[])
        for player in self._match.players:
            self._seats[player.name].update(bet=player.committed_this_hand, folded=False,
                                            cards=card_texts(player.hand))
        self._update_chips()
        self._hand_started = True
        self._report("hand_start")

    def _update_chips(self):
        players = self._match.players
        for player in players:
            seat = self._seats[player.name]
            seat["chips"] = self._stacks[player.name] - player.committed_this_hand
        self._table["pot"] = sum(player.committed_this_hand for player in players)

    def _report_action(self, player, action: str, amount: int):
        seat = self._seats[player.name]
        self._update_chips()
        if action == "fold":
            seat.update(folded=True, cards=[])
        elif amount > 0:
            seat["bet"] = amount
        self._report("action", name=player.name, action=action, amount=amount)

    def _clear_bets(self):
        for seat in self._seats.values():
            seat["bet"] = 0

    def _report_street(self, street: str, board: list[str]):
        new_cards = board[len(self._table["board"]):]
        self._clear_bets()
        self._table.update(street=street, board=board)
        self._report("street", street=street, cards=new_cards)

    def _finish_hand(self, _hands_played: int, results: list):
        self._look()
        game = self._match.game
        in_hand = [player for player in game.seated if not player.folded]
        self._clear_bets()
        if len(in_hand) > 1:
            self._report_showdown(in_hand, game.community_cards)
        for amount, winners in results:
            self._report_pot(amount, winners)
        self._report_busts()
        self._stacks = {player.name: player.chips for player in self._match.players}
        self._hand_started = False
        self._actions_reported = 0

    def _report_showdown(self, in_hand: list, board: list):
        self._table["street"] = "showdown"
        self._report("showdown", hands=[{"name": player.name, "cards": card_texts(player.hand),
                                         "hand": hand_name(evaluate(player.hand + board))}
                                        for player in in_hand])

    def _report_pot(self, amount: int, winners: list):
        # Pays out the way the engine does, which only reports each pot's total: an even share
        # each, and any odd chips to the first winner.
        share, odd_chips = divmod(amount, len(winners))
        for winner in winners:
            self._seats[winner.name]["chips"] += share
        self._seats[winners[0].name]["chips"] += odd_chips
        self._table["pot"] -= amount
        self._report("pot", amount=amount, winners=[winner.name for winner in winners])

    def _report_busts(self):
        players = self._match.players
        for number_out_before, player in enumerate(self._match.eliminated):
            seat = self._seats[player.name]
            if seat["place"] is None:
                seat["place"] = len(players) - number_out_before
                self._report("busted", name=player.name, place=seat["place"])

def play_match(settings: WatchSettings, send: Callable[[str], None]):
    """Plays the match settings describe, passing each message to send as JSON text, and returns
    when it's over. If send raises, the match stops there. Without a seed it picks one, which the
    first message reports, so any match can be replayed."""
    seed = random.randrange(2 ** 32) if settings.seed is None else settings.seed
    MatchReporter(settings, seed, send).play()
