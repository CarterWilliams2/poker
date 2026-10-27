from dataclasses import dataclass
from card import Card
from game import Game, Action, Street
from player import Player

@dataclass(frozen=True)
class SeatView:
    """What everyone at the table can see about one player. Never their cards."""
    name: str
    chips: int
    committed_this_round: int
    committed_this_hand: int
    folded: bool

    @property
    def all_in(self):
        return not self.folded and self.chips == 0

@dataclass(frozen=True)
class ActionRecord:
    """One decision from this hand. amount is the player's total bet this round after a call
    or raise, and 0 for a check or fold."""
    name: str
    street: Street
    action: Action
    amount: int

@dataclass(frozen=True)
class LegalActions:
    """The moves open to the player whose turn it is. Folding is always allowed."""
    can_check: bool
    # Chips it takes to call, capped at the player's stack. 0 when there's nothing to call.
    to_call: int
    # The smallest and largest totals the player can raise to, or None when raising isn't allowed.
    # Every total in between is legal too.
    min_raise_to: int | None
    max_raise_to: int | None

    @property
    def can_call(self):
        return self.to_call > 0

    @property
    def can_raise(self):
        return self.min_raise_to is not None

@dataclass(frozen=True)
class TableView:
    """Everything one player is allowed to know when it's their turn: their own cards plus the
    public state of the table. Agents get this instead of the game, so they can't see anyone
    else's cards."""
    name: str
    hand: tuple[Card, ...]
    chips: int
    committed_this_round: int
    committed_this_hand: int
    community_cards: tuple[Card, ...]
    street: Street
    pot: int
    current_bet: int
    min_raise: int
    small_blind: int
    big_blind: int
    # Everyone dealt into this hand, starting from the button.
    seats: tuple[SeatView, ...]
    history: tuple[ActionRecord, ...]
    legal: LegalActions

    @property
    def button(self):
        return self.seats[0].name

    @property
    def opponents(self):
        return tuple(seat for seat in self.seats if seat.name != self.name)

    @classmethod
    def for_player(cls, player: Player, game: Game):
        return cls(
            name=player.name,
            hand=tuple(player.hand),
            chips=player.chips,
            committed_this_round=player.committed_this_round,
            committed_this_hand=player.committed_this_hand,
            community_cards=tuple(game.community_cards),
            street=game.street,
            pot=game.pot,
            current_bet=game.current_bet,
            min_raise=game.min_raise,
            small_blind=game.small_blind,
            big_blind=game.big_blind,
            seats=tuple(SeatView(p.name, p.chips, p.committed_this_round, p.committed_this_hand,
                                 p.folded) for p in game.seated),
            history=tuple(ActionRecord(p.name, street, action, amount)
                          for p, street, action, amount in game.history),
            legal=_legal_actions(player, game),
        )

def _legal_actions(player: Player, game: Game):
    all_in_total = player.committed_this_round + player.chips
    to_call = min(game.current_bet - player.committed_this_round, player.chips)
    min_raise_to = max_raise_to = None
    if game.is_legal(player, Action.RAISE, all_in_total):
        min_raise_to = min(game.current_bet + game.min_raise, all_in_total)
        max_raise_to = all_in_total
    return LegalActions(game.is_legal(player, Action.CHECK, 0), to_call, min_raise_to, max_raise_to)
