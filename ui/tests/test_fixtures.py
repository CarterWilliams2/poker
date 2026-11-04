import json
from pathlib import Path
import pytest
from server.fixtures import FOLDER, SAMPLES, write

PROTOCOL = Path(__file__).resolve().parents[1] / "PROTOCOL.md"


def sample(name):
    return json.loads((FOLDER / f"{name}.json").read_text())


def test_the_samples_are_what_the_server_sends(tmp_path):
    write(tmp_path)
    for name in SAMPLES:
        assert (tmp_path / f"{name}.json").read_text() == (FOLDER / f"{name}.json").read_text(), (
            f"ui/fixtures/{name}.json doesn't match what the server sends. If you changed a "
            "message on purpose, update ui/PROTOCOL.md, then run python -m server.fixtures from "
            "ui/. If you changed how the engine plays, the UI team needs to do that once this "
            "merges.")


def test_the_heads_up_sample_has_every_kind_of_message():
    messages = sample("heads-up")
    assert {message["type"] for message in messages} == {
        "match_start", "hand_start", "action", "street", "showdown", "pot", "busted", "match_over"}
    assert {message["action"] for message in messages if message["type"] == "action"} == {
        "fold", "check", "call", "raise"}
    assert {message["street"] for message in messages if message["type"] == "street"} == {
        "flop", "turn", "river"}
    assert len(messages[0]["table"]["seats"]) == 2


def test_the_split_pot_sample_has_a_split_with_an_odd_chip():
    assert any(message["type"] == "pot" and len(message["winners"]) > 1
               and message["amount"] % len(message["winners"]) > 0
               for message in sample("split-pot"))


def test_the_full_table_sample_has_a_side_pot_and_two_players_busting_at_once():
    messages = sample("full-table")
    assert len(messages[0]["table"]["seats"]) == 8
    pots = []
    busts = []
    side_pot = two_busted = False
    for message in messages:
        if message["type"] == "hand_start":
            pots, busts = [], []
        elif message["type"] == "pot":
            pots.append(message["winners"])
            side_pot = side_pot or any(winners != pots[0] for winners in pots)
        elif message["type"] == "busted":
            busts.append(message["name"])
            two_busted = two_busted or len(busts) > 1
    assert side_pot and two_busted


@pytest.mark.parametrize("name", SAMPLES)
def test_the_protocol_describes_every_message_in_the_samples(name):
    protocol = PROTOCOL.read_text()
    for message in sample(name):
        assert f"`{message['type']}`" in protocol
        for field in (*message, *message["table"], *message["table"]["seats"][0]):
            assert f"`{field}`" in protocol, field
