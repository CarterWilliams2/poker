from player import Player
from game import Game, Action
from hand_evaluator import evaluate, hand_name
from random_agent import RandomAgent

def cards_text(cards):
    return ", ".join(card.to_string() for card in cards) or "none"

def ask_human(player: Player, game: Game):
    to_call = game.current_bet - player.committed_this_round
    print(f"--- {game.street.value}: your turn ---")
    print(f"Your hand: {cards_text(player.hand)}")
    print(f"Community cards: {cards_text(game.community_cards)}")
    print(f"Pot: {game.pot}, to call: {to_call}, your chips: {player.chips}")
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
            return action, amount
        print("That isn't legal right now.")

def announce(agent: RandomAgent):
    def act(player: Player, game: Game):
        action, amount = agent(player, game)
        detail = f" to {amount}" if action == Action.RAISE else ""
        print(f"{player.name} {action.value}s{detail}.")
        return action, amount
    return act

def main():
    human = Player("You", 100)
    bot = Player("Random Bot", 100)
    deciders = {human: ask_human, bot: announce(RandomAgent())}
    game = Game([human, bot], small_blind=1, big_blind=2,
                get_action=lambda player, game: deciders[player](player, game))
    while not game.is_over():
        results = game.play_hand()
        print()
        showdown = not human.folded and not bot.folded
        if showdown:
            print(f"Community cards: {cards_text(game.community_cards)}")
            for player in (human, bot):
                score = evaluate(player.hand + game.community_cards)
                print(f"{player.name}: {cards_text(player.hand)} ({hand_name(score)})")
        for index, (amount, winners) in enumerate(results):
            label = "Main pot" if index == 0 else f"Side pot {index}"
            print(f"{label} ({amount}) goes to {', '.join(p.name for p in winners)}")
        print(f"Chips - You: {human.chips}, Random Bot: {bot.chips}\n")
    print("You win!" if human.chips > 0 else "The random bot wins.")

if __name__ == "__main__":
    main()
