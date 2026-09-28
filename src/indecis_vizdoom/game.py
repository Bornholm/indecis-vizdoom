"""ViZDoom setup, observations and buttons."""

from __future__ import annotations

import os

import vizdoom as vzd

from .policies import Decision
from .state import Observation, observe

BUTTONS = [vzd.Button.TURN_LEFT_RIGHT_DELTA, vzd.Button.ATTACK, vzd.Button.MOVE_FORWARD]

# Degrees per tic (positive turns right). A held TURN_LEFT / TURN_RIGHT
# accelerates after a few tics, which made the aim overshoot and swing;
# the delta button turns by an exact angle. Per decision (4 tics): 2 degrees
# for a nudge, 10 for a turn, 8 for a scan.
TURN_SPEED = {"nudge_left": -0.5, "nudge_right": 0.5, "left": -2.5, "right": 2.5, "scan": 2.0}
WALKING = ("advance", "scan")
VARIABLES = [vzd.GameVariable.HEALTH, vzd.GameVariable.AMMO2, vzd.GameVariable.KILLCOUNT,
             vzd.GameVariable.POSITION_X, vzd.GameVariable.POSITION_Y]


AUDIO_RATE = 44100


def make_game(scenario: str = "defend_the_center", resolution: vzd.ScreenResolution | None = None,
              hud: bool = False, audio: bool = False) -> vzd.DoomGame:
    """The engine runs in synchronous mode: loop.realtime charges latency
    in game tics. resolution and hud are for display only: the observation
    does not depend on them."""
    game = vzd.DoomGame()
    game.load_config(os.path.join(vzd.scenarios_path, f"{scenario}.cfg"))
    if resolution is not None:
        game.set_screen_resolution(resolution)
        game.set_screen_format(vzd.ScreenFormat.RGB24)
    if audio:  # Freedoom's sounds and music, one tic of samples per state
        game.set_sound_enabled(True)
        game.set_audio_buffer_enabled(True)
        game.set_audio_sampling_rate(vzd.SamplingRate.SR_44100)
        game.set_audio_buffer_size(1)
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


def buttons(d: Decision) -> list[float]:
    """Turn options turn, advance and scan walk, fire holds the trigger."""
    return [TURN_SPEED.get(d.turn, 0.0), float(d.fire), float(d.turn in WALKING)]


def kills(game: vzd.DoomGame) -> int:
    return int(game.get_game_variable(vzd.GameVariable.KILLCOUNT))
