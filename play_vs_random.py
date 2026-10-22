from player import Player
from game import Game, Action
from hand_evaluator import evaluate, hand_name
from random_agent import RandomAgent

def cards_text(cards):
    return ", ".join(card.to_string() for card in cards) or "none"

class Table:
    """Prints a header with the board whenever a new street starts, before anyone acts on it."""

    def __init__(self, human: Player):
        self._human = human
        self._street = None

    def new_hand(self, number: int):
        print(f"\n========== Hand {number} ==========")
        self._street = None

    def show_street(self, game: Game):
        if game.street == self._street:
            return
        self._street = game.street
        print(f"\n--- {game.street.value.capitalize()} ---")
        if game.community_cards:
            print(f"Board: {cards_text(game.community_cards)}")
        print(f"Your hand: {cards_text(self._human.hand)}")
        print(f"Pot: {game.pot}\n")

def ask_human(table: Table):
    def act(player: Player, game: Game):
        table.show_street(game)
        to_call = game.current_bet - player.committed_this_round
        print(f"Your turn. Pot: {game.pot}, to call: {to_call}, your chips: {player.chips}")
        while True:
            words = input("fold, check, call, or raise <total>: ").strip().lower().split()
            if len(words) == 1 and words[0] in ("fold", "check", "call"):
                action, amount = Action(words[0]), 0
            elif len(words) == 2 and words[0] == "raise" and words[1].isdigit():
                action, amount = Action.RAISE, int(words[1])
            else:
                print("Didn't understand that.")
                continue
            if game.is_legal(player, action, amount):
                print()
                return action, amount
            print("That isn't legal right now.")
    return act

def announce(table: Table, agent: RandomAgent):
    def act(player: Player, game: Game):
        table.show_street(game)
        action, amount = agent(player, game)
        if action == Action.RAISE:
            verb = "bets" if game.current_bet == 0 else "raises to"
            print(f"{player.name} {verb} {amount}.\n")
        else:
            print(f"{player.name} {action.value}s.\n")
        return action, amount
    return act

def main():
    human = Player("You", 100)
    bot = Player("Random Bot", 100)
    table = Table(human)
    deciders = {human: ask_human(table), bot: announce(table, RandomAgent())}
    game = Game([human, bot], small_blind=1, big_blind=2,
                get_action=lambda player, game: deciders[player](player, game))
    hand_number = 0
    while not game.is_over():
        hand_number += 1
        table.new_hand(hand_number)
        results = game.play_hand()
        print("--- Result ---")
        if not human.folded and not bot.folded:
            print(f"Board: {cards_text(game.community_cards)}")
            for player in (human, bot):
                score = evaluate(player.hand + game.community_cards)
                print(f"{player.name}: {cards_text(player.hand)} ({hand_name(score)})")
        for index, (amount, winners) in enumerate(results):
            label = "Main pot" if index == 0 else f"Side pot {index}"
            print(f"{label} ({amount}) goes to {', '.join(p.name for p in winners)}")
        print(f"Chips - You: {human.chips}, Random Bot: {bot.chips}")
    print("\nYou win!" if human.chips > 0 else "\nThe random bot wins.")

if __name__ == "__main__":
    main()
