"""ViZDoom setup, observations and buttons."""

from __future__ import annotations

import os

import vizdoom as vzd

from .policies import Decision
from .state import Observation, observe

BUTTONS = [vzd.Button.TURN_LEFT, vzd.Button.TURN_RIGHT, vzd.Button.ATTACK, vzd.Button.MOVE_FORWARD]
VARIABLES = [vzd.GameVariable.HEALTH, vzd.GameVariable.AMMO2, vzd.GameVariable.KILLCOUNT,
             vzd.GameVariable.POSITION_X, vzd.GameVariable.POSITION_Y]


def make_game(scenario: str = "defend_the_center", resolution: vzd.ScreenResolution | None = None,
              hud: bool = False) -> vzd.DoomGame:
    """The engine runs in synchronous mode: loop.realtime charges latency
    in game tics. resolution and hud are for display only: the observation
    does not depend on them."""
    game = vzd.DoomGame()
    game.load_config(os.path.join(vzd.scenarios_path, f"{scenario}.cfg"))
    if resolution is not None:
        game.set_screen_resolution(resolution)
        game.set_screen_format(vzd.ScreenFormat.RGB24)
    if hud:
        game.set_render_hud(True)
        game.set_render_crosshair(True)
    game.set_available_buttons(BUTTONS)
    game.set_available_game_variables(VARIABLES)
    game.set_labels_buffer_enabled(True)
    game.set_window_visible(False)
    game.set_mode(vzd.Mode.PLAYER)
    game.init()
    return game


def variables(state) -> dict[str, float]:
    return {v.name: x for v, x in zip(VARIABLES, state.game_variables)}


def observation(game: vzd.DoomGame) -> Observation:
    state = game.get_state()
    v = variables(state)
    return observe(state.labels, game.get_screen_width(), (v["POSITION_X"], v["POSITION_Y"]), v["HEALTH"], v["AMMO2"])


def buttons(d: Decision) -> list[int]:
    """left, right and scan turn; advance walks; fire holds the trigger."""
    left = d.turn == "left"
    right = d.turn in ("right", "scan")
    return [int(left), int(right), int(d.fire), int(d.turn == "advance")]


def kills(game: vzd.DoomGame) -> int:
    return int(game.get_game_variable(vzd.GameVariable.KILLCOUNT))
