import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from indecis_vizdoom.game import buttons  # noqa: E402
from indecis_vizdoom.policies import Decision, scripted  # noqa: E402
from indecis_vizdoom.state import describe, is_monster, observe  # noqa: E402


def label(name, x, width, px, py):
    return SimpleNamespace(object_name=name, x=x, width=width, object_position_x=px, object_position_y=py)


def test_monsters():
    assert is_monster("Demon")
    assert is_monster("MarineChainsawVzd")
    assert not is_monster("DeadDemon")
    assert not is_monster("BulletPuff")
    assert not is_monster("DoomPlayer")


def test_no_enemy_means_scan():
    obs = observe([label("BulletPuff", 150, 2, 100, 0)], 320, (0, 0), 100, 26)
    assert describe(obs) == "Health 100%, 26 bullets left. No enemy in sight."
    d = scripted(obs)
    assert (d.fire, d.turn) == (False, "scan")


def test_nearest_enemy_first_and_lined_up():
    obs = observe([label("MarineChainsawVzd", 20, 10, 700, 0), label("Demon", 150, 30, 300, 0)], 320, (0, 0), 80, 10)
    text = describe(obs)
    assert "2 enemies in sight" in text
    assert "The nearest, a demon, is close and lined up with the crosshair." in text
    assert "Another, a marine with a chainsaw, is far away and far to the left of the crosshair." in text
    d = scripted(obs)
    assert (d.fire, d.turn) == (True, "hold")


def test_lined_up_enemy_not_close_means_advance():
    obs = observe([label("Demon", 155, 10, 900, 0)], 320, (0, 0), 100, 26)
    assert scripted(obs).turn == "advance"
    obs = observe([label("Demon", 155, 10, 500, 0)], 320, (0, 0), 100, 26)
    assert "at mid range" in describe(obs)
    assert scripted(obs).turn == "advance"


def test_turn_toward_the_side():
    obs = observe([label("Demon", 200, 10, 500, 0)], 320, (0, 0), 100, 26)
    assert "slightly" not in describe(obs)
    assert scripted(obs).turn == "right"


def test_nudge_when_slightly_off():
    obs = observe([label("Demon", 140, 10, 500, 0)], 320, (0, 0), 100, 26)
    assert "slightly to the left" in describe(obs)
    assert scripted(obs).turn == "nudge_left"


def test_buttons():
    assert buttons(Decision(True, "left")) == [-2.5, 1.0, 0.0]
    assert buttons(Decision(False, "nudge_right")) == [0.5, 0.0, 0.0]
    assert buttons(Decision(False, "scan")) == [2.0, 0.0, 1.0]
    assert buttons(Decision(False, "advance")) == [0.0, 0.0, 1.0]
    assert buttons(Decision(False, "hold")) == [0.0, 0.0, 0.0]
