import json
import logging
import random
import re
import threading
import time
from contextlib import contextmanager
from pathlib import Path
import pytest
import uvicorn
from websockets.exceptions import ConnectionClosedOK
from websockets.sync.client import connect
from server.app import create_app
from server.engine import AGENTS, Card, Match, evaluate, hand_name
from server.watch import WatchSettings, parse_start, play_match

# Seconds to wait for the server before failing. Each message takes far less.
PATIENCE = 10

SHORT_MATCH = {"bots": ["calling", "aggressive"], "chips": 4, "seed": 1}


def watch(**settings):
    """Every message of a match, decoded."""
    messages = []
    play_match(WatchSettings(type="start", **settings),
               lambda text: messages.append(json.loads(text)))
    return messages


@contextmanager
def serving(app):
    """The address of /ws/watch with an app on real uvicorn, in this process so that coverage sees
    it. The test client skips uvicorn, can't show a browser leaving because its socket never fails,
    and waits forever if the server goes quiet."""
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_config=None))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        assert thread.is_alive()
        time.sleep(0.01)
    yield f"ws://127.0.0.1:{server.servers[0].sockets[0].getsockname()[1]}/ws/watch"
    server.should_exit = True
    thread.join(timeout=PATIENCE)
    assert not thread.is_alive()


@pytest.fixture
def address(caplog):
    """The address of /ws/watch on a real server. Any error the server logs fails the test."""
    with caplog.at_level(logging.ERROR), serving(create_app(Path("no-web-app"))) as found:
        yield found
    assert "Exception" not in caplog.text


def receive(browser):
    return json.loads(browser.recv(timeout=PATIENCE))


def read_to_the_end(browser):
    """Everything the server sends from here until it closes the socket normally."""
    messages = []
    while True:
        try:
            messages.append(receive(browser))
        except ConnectionClosedOK as closed:
            assert closed.rcvd.code == 1000
            return messages


def stream(address, start):
    """Everything the server sends over the socket after a start message."""
    with connect(address, proxy=None) as browser:
        browser.send(json.dumps({"type": "start", **start}))
        return read_to_the_end(browser)


@pytest.fixture(scope="module")
def matches():
    """Matches at every table size, with short and deep stacks, and every kind of bot."""
    simple_bots = ["random", "calling", "aggressive", "random",
                   "random", "calling", "random", "random"]
    found = [watch(bots=simple_bots[:size], chips=chips, seed=seed)
             for size in range(2, 9) for chips in (2, 10, 50) for seed in range(4)]
    found += [watch(bots=[bot, "random"], chips=30, seed=seed)
              for bot in AGENTS for seed in range(2)]
    found.append(watch(bots=list(AGENTS)[:8], chips=30, seed=1))
    return found


def all_messages(matches):
    return [message for messages in matches for message in messages]


def pairs(matches):
    """Each message with the one before it."""
    return [pair for messages in matches for pair in zip(messages, messages[1:])]


def hands(messages):
    """A match's messages, split up by hand."""
    found = []
    for message in messages:
        if message["type"] == "hand_start":
            found.append([])
        if found and message["type"] != "match_over":
            found[-1].append(message)
    return found


def seat(table, name):
    return next(seat for seat in table["seats"] if seat["name"] == name)


def chips_on_table(table):
    return sum(seat["chips"] for seat in table["seats"]) + table["pot"]


def cards(texts):
    """Engine cards from strings like "AS"."""
    return [Card(text[:-1], text[-1]) for text in texts]


def test_the_same_seed_gives_the_same_messages():
    settings = {"bots": list(AGENTS)[:8], "chips": 30, "seed": 7}
    assert watch(**settings) == watch(**settings)


def test_a_different_seed_gives_different_messages():
    settings = {"bots": list(AGENTS)[:8], "chips": 30}
    assert watch(**settings, seed=7) != watch(**settings, seed=8)


def test_without_a_seed_it_picks_one_that_replays_the_match():
    first = watch(bots=["random", "random"], chips=20)
    second = watch(bots=["random", "random"], chips=20)
    assert first[0]["seed"] != second[0]["seed"]
    assert watch(bots=["random", "random"], chips=20, seed=first[0]["seed"]) == first


def test_no_chips_appear_or_vanish(matches):
    for messages in matches:
        total = chips_on_table(messages[0]["table"])
        for message in messages:
            table = message["table"]
            assert chips_on_table(table) == total, message
            assert table["pot"] >= 0, message
            assert all(seat["chips"] >= 0 and seat["bet"] >= 0 for seat in table["seats"]), message
            assert sum(seat["bet"] for seat in table["seats"]) <= table["pot"], message


def test_the_pots_pay_out_every_chip_bet_in_the_hand(matches):
    for messages in matches:
        for hand in hands(messages):
            pots = [message for message in hand if message["type"] == "pot"]
            before_paying = hand[hand.index(pots[0]) - 1]["table"]
            assert sum(pot["amount"] for pot in pots) == before_paying["pot"]
            assert pots[-1]["table"]["pot"] == 0


def test_stacks_carry_over_to_the_next_hand(matches):
    for messages in matches:
        for hand, next_hand in zip(hands(messages), hands(messages)[1:]):
            for before, after in zip(hand[-1]["table"]["seats"], next_hand[0]["table"]["seats"]):
                assert before["chips"] == after["chips"] + after["bet"]


@pytest.mark.parametrize("bots, chips, seed", [
    (["random", "random"], 20, 1),
    (["random", "calling", "random", "aggressive", "random"], 30, 2),
    (["random", "random", "calling", "random", "random", "aggressive", "random", "calling"], 40, 3),
    (["tuned", "strength", "tight", "random"], 30, 4),
])
def test_the_messages_match_what_the_engine_did(bots, chips, seed):
    """Plays the same match on the engine directly and compares every hand."""
    rng = random.Random(seed)
    seats = [(f"{bot.capitalize()} {number}", AGENTS[bot](random.Random(rng.random())))
             for number, bot in enumerate(bots, start=1)]
    match = Match(seats, chips, 1, 2, rng=random.Random(rng.random()))
    played = []

    def record_hand(number, pots):
        game = match.game
        left = [player.name for player in game.seated if not player.folded]
        played.append({
            "button": game.seated[0].name,
            "actions": [(player.name, street.value, action.value, amount)
                        for player, street, action, amount in game.history],
            "board": [card.value + card.suit for card in game.community_cards],
            "pots": [[amount, [winner.name for winner in winners]] for amount, winners in pots],
            "chips": {player.name: player.chips for player in match.players},
            "showdown": sorted(left) if len(left) > 1 else [],
        })
    standings = match.run(on_hand=record_hand)

    messages = watch(bots=bots, chips=chips, seed=seed)
    reported = []
    for hand in hands(messages):
        showdown = [message for message in hand if message["type"] == "showdown"]
        reported.append({
            "button": hand[0]["table"]["button"],
            "actions": [(message["name"], message["table"]["street"], message["action"],
                         message["amount"])
                        for message in hand if message["type"] == "action"],
            "board": hand[-1]["table"]["board"],
            "pots": [[message["amount"], message["winners"]]
                     for message in hand if message["type"] == "pot"],
            "chips": {seat["name"]: seat["chips"] for seat in hand[-1]["table"]["seats"]},
            "showdown": sorted(entry["name"] for entry in showdown[0]["hands"])
                        if showdown else [],
        })
    assert reported == played
    assert [message["name"] for message in messages if message["type"] == "busted"] == [
        player.name for player in match.eliminated]
    assert [entry["name"] for entry in messages[-1]["standings"]] == [
        player.name for player in standings]
    assert messages[-1]["hands_played"] == match.hands_played


def test_messages_come_in_the_order_the_protocol_gives(matches):
    letters = {"match_start": "M", "hand_start": "H", "action": "a", "street": "s", "showdown": "S",
               "pot": "p", "busted": "b", "match_over": "O"}
    for messages in matches:
        order = "".join(letters[message["type"]] for message in messages)
        assert re.fullmatch(r"M(H[as]*S?p+b*)+O", order), order


def test_streets_come_in_order_and_each_action_is_on_the_street_it_happened(matches):
    for messages in matches:
        for hand in hands(messages):
            streets = [message["street"] for message in hand if message["type"] == "street"]
            assert streets == ["flop", "turn", "river"][:len(streets)]
            street = "preflop"
            for message in hand:
                if message["type"] == "street":
                    street = message["street"]
                elif message["type"] == "action":
                    assert message["table"]["street"] == street


def test_an_action_moves_only_that_players_chips(matches):
    seen = set()
    for previous, message in pairs(matches):
        if message["type"] != "action":
            continue
        seen.add(message["action"])
        name, before, after = message["name"], previous["table"], message["table"]
        others = [[seat for seat in table["seats"] if seat["name"] != name]
                  for table in (before, after)]
        assert others[0] == others[1]
        assert before["board"] == after["board"]
        was, now = seat(before, name), seat(after, name)
        if message["action"] in ("call", "raise"):
            paid = message["amount"] - was["bet"]
            assert paid > 0
            assert now["bet"] == message["amount"]
            assert now["chips"] == was["chips"] - paid
            assert after["pot"] == before["pot"] + paid
            assert now["cards"] == was["cards"]
        else:
            assert message["amount"] == 0
            assert (now["bet"], now["chips"]) == (was["bet"], was["chips"])
            assert after["pot"] == before["pot"]
        if message["action"] == "fold":
            assert now["folded"]
            assert now["cards"] == []
    assert seen == {"fold", "check", "call", "raise"}


def test_a_new_street_clears_the_bets_and_adds_its_cards(matches):
    seen = set()
    for previous, message in pairs(matches):
        if message["type"] != "street":
            continue
        seen.add(message["street"])
        before, after = previous["table"], message["table"]
        assert after["street"] == message["street"]
        assert len(message["cards"]) == (3 if message["street"] == "flop" else 1)
        assert after["board"] == before["board"] + message["cards"]
        assert all(seat["bet"] == 0 for seat in after["seats"])
        assert after["pot"] == before["pot"]
        assert [s["chips"] for s in before["seats"]] == [s["chips"] for s in after["seats"]]
    assert seen == {"flop", "turn", "river"}


def test_a_hand_deals_two_different_cards_to_everyone_still_in(matches):
    for messages in matches:
        for hand in hands(messages):
            start = hand[0]["table"]
            playing = [seat for seat in start["seats"] if seat["place"] is None]
            assert all(len(seat["cards"]) == 2 for seat in playing)
            assert all(seat["cards"] == [] for seat in start["seats"] if seat["place"] is not None)
            assert not any(seat["folded"] for seat in start["seats"])
            hole_cards = [card for seat in start["seats"] for card in seat["cards"]]
            dealt = hole_cards + hand[-1]["table"]["board"]
            assert len(dealt) == len(set(dealt))


def test_a_hand_starts_with_the_blinds_in_and_the_button_moved_on(matches):
    for messages in matches:
        button = None
        order = [seat["name"] for seat in messages[0]["table"]["seats"]]
        for hand in hands(messages):
            table = hand[0]["table"]
            playing = [seat["name"] for seat in table["seats"] if seat["place"] is None]
            # The button goes to the next player still in, and the blinds follow it.
            start = order.index(button) + 1 if button else 0
            button = next(name for name in order[start:] + order[:start] if name in playing)
            assert table["button"] == button
            start = order.index(button)
            from_button = [name for name in order[start:] + order[:start] if name in playing]
            blinds = from_button[:2] if len(playing) == 2 else from_button[1:3]
            assert [table["small_blind"], table["big_blind"]] == blinds
            assert 0 < seat(table, blinds[0])["bet"] <= 1
            assert 0 < seat(table, blinds[1])["bet"] <= 2
            assert sum(seat["bet"] for seat in table["seats"]) == table["pot"]
            assert sum(seat["bet"] > 0 for seat in table["seats"]) == 2


def test_a_showdown_shows_everyone_left_and_names_their_hands(matches):
    showdowns = won_by_folding = 0
    for messages in matches:
        for hand in hands(messages):
            found = [message for message in hand if message["type"] == "showdown"]
            before_paying = next(message for message in hand if message["type"] == "pot")["table"]
            left = [seat for seat in before_paying["seats"]
                    if seat["place"] is None and not seat["folded"]]
            if found:
                showdowns += 1
                table = found[0]["table"]
                assert table["street"] == "showdown"
                assert len(table["board"]) == 5
                assert all(seat["bet"] == 0 for seat in table["seats"])
                assert sorted(entry["name"] for entry in found[0]["hands"]) == sorted(
                    seat["name"] for seat in left)
                for entry in found[0]["hands"]:
                    assert entry["cards"] == seat(table, entry["name"])["cards"]
                    seven_cards = cards(entry["cards"] + table["board"])
                    assert entry["hand"] == hand_name(evaluate(seven_cards))
            else:
                won_by_folding += 1
                assert len(left) == 1
                assert all(message["winners"] == [left[0]["name"]]
                           for message in hand if message["type"] == "pot")
    assert showdowns and won_by_folding


def test_a_pot_goes_to_its_winners_and_any_odd_chips_to_the_first(matches):
    splits = odd_chips = 0
    for previous, message in pairs(matches):
        if message["type"] != "pot":
            continue
        before, after = previous["table"], message["table"]
        assert all(seat["bet"] == 0 for seat in after["seats"])
        assert after["pot"] == before["pot"] - message["amount"]
        share, left_over = divmod(message["amount"], len(message["winners"]))
        for was, now in zip(before["seats"], after["seats"]):
            won = 0
            if now["name"] in message["winners"]:
                won = share + (left_over if now["name"] == message["winners"][0] else 0)
            assert now["chips"] == was["chips"] + won
        splits += len(message["winners"]) > 1
        odd_chips += left_over > 0
    assert splits and odd_chips


def test_seats_stay_in_order_and_busted_players_keep_their_place(matches):
    both_at_once = False
    for messages in matches:
        order = [seat["name"] for seat in messages[0]["table"]["seats"]]
        places = {}
        for hand in hands(messages):
            out_this_hand = [message for message in hand if message["type"] == "busted"]
            both_at_once = both_at_once or len(out_this_hand) > 1
            for message in hand:
                assert [seat["name"] for seat in message["table"]["seats"]] == order
                if message["type"] == "busted":
                    assert seat(message["table"], message["name"])["chips"] == 0
                    places[message["name"]] = message["place"]
                assert places == {seat["name"]: seat["place"]
                                  for seat in message["table"]["seats"] if seat["place"]}
            # The worst place goes first.
            found = [message["place"] for message in out_this_hand]
            assert found == sorted(found, reverse=True)
    assert both_at_once


def test_the_standings_rank_everyone_and_agree_with_the_places_they_busted_in(matches):
    for messages in matches:
        over = messages[-1]
        table = over["table"]
        assert over["hands_played"] == table["hand"]
        assert [entry["place"] for entry in over["standings"]] == list(
            range(1, len(table["seats"]) + 1))
        for entry in over["standings"]:
            assert entry["chips"] == seat(table, entry["name"])["chips"]
            assert seat(table, entry["name"])["place"] in (None, entry["place"])
        assert sum(entry["chips"] for entry in over["standings"]) == chips_on_table(table)


def test_players_are_named_after_their_bot_and_seat():
    first = watch(bots=["tuned", "random", "tuned"], chips=10, seed=1)[0]
    assert [seat["name"] for seat in first["table"]["seats"]] == ["Tuned 1", "Random 2", "Tuned 3"]


def test_the_first_message_shows_the_table_before_the_first_hand():
    first = watch(bots=["random", "calling"], chips=30, seed=7)[0]
    assert first["type"] == "match_start"
    assert first["seed"] == 7
    assert first["table"] == {
        "hand": 0, "street": None, "button": None, "small_blind": None, "big_blind": None,
        "board": [], "pot": 0,
        "seats": [{"name": name, "chips": 30, "bet": 0, "cards": [], "folded": False, "place": None}
                  for name in ("Random 1", "Calling 2")]}


def test_all_in_before_the_flop_still_reports_the_whole_board():
    messages = watch(bots=["aggressive", "calling"], chips=4, seed=1)
    types = [message["type"] for message in hands(messages)[0]]
    assert types[:2] == ["hand_start", "action"]
    assert types[types.index("street"):types.index("showdown")] == ["street", "street", "street"]
    assert len(hands(messages)[0][-1]["table"]["board"]) == 5


def test_a_hand_can_have_no_actions_when_the_blinds_put_everyone_all_in():
    messages = watch(bots=["calling", "calling"], chips=1, seed=1)
    hand = hands(messages)[0]
    assert [message["type"] for message in hand][:5] == [
        "hand_start", "street", "street", "street", "showdown"]
    start = hand[0]["table"]
    assert (start["pot"], start["small_blind"], start["big_blind"]) == (2, "Calling 1", "Calling 2")
    assert [(seat["chips"], seat["bet"]) for seat in start["seats"]] == [(0, 1), (0, 1)]


def test_max_hands_ends_a_match_with_the_chip_leader_first():
    messages = watch(bots=["calling", "calling"], chips=100, seed=1, max_hands=5)
    over = messages[-1]
    assert over["hands_played"] == 5
    assert over["standings"][0]["chips"] >= over["standings"][1]["chips"] > 0
    assert not [message for message in messages if message["type"] == "busted"]


def test_the_chips_and_blinds_come_from_the_settings():
    messages = watch(bots=["calling", "calling", "calling"], chips=500, small_blind=5, big_blind=10,
                     seed=1)
    assert all(seat["chips"] == 500 for seat in messages[0]["table"]["seats"])
    table = hands(messages)[0][0]["table"]
    assert seat(table, table["small_blind"])["bet"] == 5
    assert seat(table, table["big_blind"])["bet"] == 10
    assert table["pot"] == 15


def test_the_defaults_seat_one_of_each_bot_for_a_thousand_hands():
    settings = parse_start('{"type": "start"}')
    assert (settings.bots, settings.chips, settings.small_blind, settings.big_blind, settings.seed,
            settings.max_hands) == (list(AGENTS)[:8], 100, 1, 2, None, 1000)


@pytest.mark.parametrize("at", [1, 2, 5, 12])
def test_when_sending_fails_the_match_stops_there(at):
    sent = []

    class BrowserLeft(Exception):
        pass

    def send(text):
        if len(sent) == at:
            raise BrowserLeft
        sent.append(text)

    with pytest.raises(BrowserLeft):
        play_match(WatchSettings(type="start", bots=["calling", "calling"], seed=1), send)
    assert len(sent) == at


def test_the_socket_streams_a_match_and_closes_normally(address):
    start = {"bots": ["tuned", "random", "calling"], "chips": 20, "seed": 7}
    messages = stream(address, start)
    assert messages[-1]["type"] == "match_over"
    assert messages == watch(**start)


def test_the_socket_runs_the_default_match_with_only_a_type(address):
    messages = stream(address, {})
    assert len(messages[0]["table"]["seats"]) == len(list(AGENTS)[:8])
    assert messages[-1]["type"] == "match_over"


@pytest.mark.parametrize("text, problem", [
    ("not json", "Invalid JSON"),
    ('"start"', "object"),
    ('{"chips": 100}', "type"),
    ('{"type": "act"}', "type"),
    ('{"type": "start", "chips": 0}', "chips"),
    ('{"type": "start", "chips": "100"}', "chips"),
    ('{"type": "start", "chips": true}', "chips"),
    ('{"type": "start", "small_blind": 0}', "small_blind"),
    ('{"type": "start", "big_blind": 0}', "big_blind"),
    ('{"type": "start", "small_blind": 3, "big_blind": 2}',
     "small_blind can't be more than big_blind"),
    ('{"type": "start", "chips": 0, "seed": "seven"}', "; seed"),
    ('{"type": "start", "bots": ["tuned"]}', "bots"),
    ('{"type": "start", "bots": "tuned"}', "bots"),
    (json.dumps({"type": "start", "bots": ["tuned"] * 9}), "bots"),
    ('{"type": "start", "bots": ["tuned", "wizard"]}',
     "bots: there's no bot called 'wizard', choose from aggressive"),
    ('{"type": "start", "seed": "seven"}', "seed"),
    ('{"type": "start", "max_hands": 0}', "max_hands"),
    ('{"type": "start", "seeds": 7}', "seeds"),
])
def test_a_bad_start_gets_an_error_and_a_good_one_still_works(address, text, problem):
    with connect(address, proxy=None) as browser:
        browser.send(text)
        answer = receive(browser)
        assert answer["type"] == "error"
        assert problem in answer["message"]
        browser.send(json.dumps({"type": "start", **SHORT_MATCH}))
        assert read_to_the_end(browser)[-1]["type"] == "match_over"


def test_the_socket_answers_next_to_the_built_web_app(tmp_path):
    (tmp_path / "index.html").write_text("<p>The table</p>")
    with serving(create_app(tmp_path)) as address:
        assert stream(address, SHORT_MATCH)[-1]["type"] == "match_over"


def test_a_browser_leaving_mid_match_ends_it(address, monkeypatch):
    finished = threading.Event()
    sent = []

    def playing(settings, send):
        def counting(text):
            sent.append(text)
            send(text)
        try:
            play_match(settings, counting)
        finally:
            finished.set()
    monkeypatch.setattr("server.app.play_match", playing)

    # Hundreds of thousands of messages if it plays to the end.
    start = {"type": "start", "bots": ["calling", "calling"], "chips": 1000000,
             "max_hands": 20000}
    with connect(address, proxy=None) as browser:
        browser.send(json.dumps(start))
        assert receive(browser)["type"] == "match_start"
    assert finished.wait(timeout=PATIENCE)
    assert len(sent) < 100000


def test_a_browser_leaving_before_it_starts_a_match_is_fine(address):
    with connect(address, proxy=None) as browser:
        browser.send("not json")
        assert receive(browser)["type"] == "error"


def test_matches_at_once_stay_separate(address):
    settings = {"bots": ["random", "calling", "random"], "chips": 40}
    results = {}

    def watch_over_a_socket(key, seed):
        results[key] = stream(address, {**settings, "seed": seed})

    threads = [threading.Thread(target=watch_over_a_socket, args=args)
               for args in (("first", 1), ("again", 1), ("other", 2))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results["first"] == results["again"] == watch(**settings, seed=1)
    assert results["other"] == watch(**settings, seed=2)
