"""A visible game with the model's view and decisions, in real time.

The game runs at 35 tics per second as in `loop.realtime`. Each frame
shows the game, a box around each enemy the observation found, the text
the model read for its last decision, the probabilities of its answers,
its latency and the score. With `record`, frames are piped to ffmpeg.
"""

from __future__ import annotations

import os
import statistics
import subprocess
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402
import vizdoom as vzd  # noqa: E402

from . import loop  # noqa: E402
from .game import make_game, variables  # noqa: E402
from .questions import TURN_OPTIONS  # noqa: E402
from .state import is_monster  # noqa: E402

W, H = 1920, 1080
GAME_W, GAME_H = 1344, 756  # 1024x576 scaled by 1.3125
PANEL_X = GAME_W
BG = (14, 16, 22)
FG = (228, 230, 236)
DIM = (130, 136, 150)
ACCENT = (255, 176, 32)
GREEN = (80, 220, 120)
RED = (235, 80, 70)
BAR_BG = (40, 44, 56)
FOOTER = "github.com/Bornholm/indecis  ·  github.com/Bornholm/indecis-vizdoom  ·  ViZDoom defend_the_center, real time"


class Display:
    def __init__(self, title: str, subtitle: str, scale: float, record: str | None) -> None:
        pygame.init()
        pygame.display.set_caption(title)
        self.window = pygame.display.set_mode((int(W * scale), int(H * scale)))
        self.canvas = pygame.Surface((W, H))
        self.title, self.subtitle = title, subtitle
        font = lambda size, bold=False: pygame.font.SysFont("dejavusans,liberationsans,arial", size, bold=bold)
        self.big, self.mid, self.small, self.mono = font(40, True), font(28), font(24), pygame.font.SysFont("dejavusansmono,monospace", 22)
        self.ffmpeg = None
        if record:
            self.ffmpeg = subprocess.Popen(
                ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                 "-r", "35", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                 "-pix_fmt", "yuv420p", record], stdin=subprocess.PIPE)

    def text(self, s, font, color, x, y) -> int:
        img = font.render(s, True, color)
        self.canvas.blit(img, (x, y))
        return y + img.get_height()

    def wrapped(self, s, font, color, x, y, width) -> int:
        line = ""
        for word in s.split():
            candidate = f"{line} {word}".strip()
            if font.size(candidate)[0] > width and line:
                y = self.text(line, font, color, x, y) + 4
                line = word
            else:
                line = candidate
        if line:
            y = self.text(line, font, color, x, y) + 4
        return y

    def bar(self, label, p, x, y, width, chosen) -> int:
        color = ACCENT if chosen else DIM
        self.text(label, self.mid, FG if chosen else DIM, x, y)
        bx, bw = x + 150, width - 250
        pygame.draw.rect(self.canvas, BAR_BG, (bx, y + 8, bw, 22), border_radius=4)
        pygame.draw.rect(self.canvas, color, (bx, y + 8, max(2, int(bw * p)), 22), border_radius=4)
        self.text(f"{p:.0%}", self.small, FG if chosen else DIM, bx + bw + 14, y + 4)
        return y + 44

    def frame(self, state, info: dict) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return False
        c = self.canvas
        c.fill(BG)
        if state is not None:
            img = pygame.image.frombuffer(state.screen_buffer.tobytes(), (state.screen_buffer.shape[1], state.screen_buffer.shape[0]), "RGB")
            sx = GAME_W / img.get_width()
            c.blit(pygame.transform.smoothscale(img, (GAME_W, GAME_H)), (0, 0))
            for label in state.labels:
                if is_monster(label.object_name):
                    centre = img.get_width() / 2
                    lined = label.x <= centre <= label.x + label.width
                    rect = pygame.Rect(label.x * sx, label.y * sx, label.width * sx, label.height * sx)
                    pygame.draw.rect(c, GREEN if lined else ACCENT, rect, 3)
        # Header, right panel.
        x, width = PANEL_X + 40, W - PANEL_X - 80
        y = self.text(self.title, self.big, FG, x, 36)
        y = self.wrapped(self.subtitle, self.small, DIM, x, y + 8, width) + 24
        d = info.get("decision")
        y = self.text("fire", self.big, FG, x, y) + 8
        p_fire = d.p_fire if d else 0.0
        y = self.bar("yes", p_fire, x, y, width, bool(d and d.fire))
        y = self.bar("no", 1 - p_fire, x, y, width, bool(d and not d.fire)) + 24
        y = self.text("turn", self.big, FG, x, y) + 8
        for option in TURN_OPTIONS:
            p = (d.turn_probs.get(option, 0.0) if d else 0.0)
            y = self.bar(option, p, x, y, width, bool(d and d.turn == option))
        y += 24
        lat = info.get("latencies", [])
        rows = [
            ("latency", f"{lat[-1]:.1f} ms (median {statistics.median(lat):.1f})" if lat else "-"),
            ("decisions", f"{info.get('decisions_per_second', 0):.1f} per second"),
            ("skipped", str(info.get("skipped", 0))),
            ("kills", str(info.get("kills", 0))),
            ("health", str(info.get("health", 0))),
            ("episode", info.get("episode", "")),
        ]
        for k, v in rows:
            self.text(k, self.mid, DIM, x, y)
            y = self.text(v, self.mid, FG, x + 170, y) + 6
        # What the model read, under the game.
        y = self.text("What the model reads", self.mid, DIM, 40, GAME_H + 24) + 10
        self.wrapped(info.get("text", ""), self.mid, FG, 40, y, GAME_W - 80)
        self.text(FOOTER, self.small, DIM, 40, H - 56)
        pygame.transform.smoothscale(c, self.window.get_size(), self.window) if self.window.get_size() != (W, H) else self.window.blit(c, (0, 0))
        pygame.display.flip()
        if self.ffmpeg:
            self.ffmpeg.stdin.write(pygame.image.tobytes(c, "RGB"))
        return True

    def close(self) -> None:
        if self.ffmpeg:
            self.ffmpeg.stdin.close()
            self.ffmpeg.wait()
        pygame.quit()


def show(policy, title: str, subtitle: str, seeds, scenario: str, interval: int = 4,
         scale: float = 1.0, record: str | None = None) -> None:
    """Plays in real time (loop.realtime), one frame per tic, paced at 35
    frames per second."""
    game = make_game(scenario, resolution=vzd.ScreenResolution.RES_1024X576, hud=True)
    display = Display(title, subtitle, scale, record)
    try:
        for n, seed in enumerate(seeds, 1):
            episode = f"{n} of {len(seeds)} (seed {seed})"
            clock = {"start": time.monotonic(), "tics": 0, "last": None}

            def on_tic(state, info):
                info["episode"] = episode
                info["health"] = int(variables(state)["HEALTH"])
                clock["last"] = (state, dict(info))
                # Pace to 35 frames per second; a video frame per tic.
                clock["tics"] += 1
                wait = clock["start"] + clock["tics"] / 35 - time.monotonic()
                if wait > 0 and not record:
                    time.sleep(wait)
                return display.frame(state, info)

            loop.realtime(game, policy, seed, interval, on_tic)
            if clock["last"] is None:
                continue
            state, info = clock["last"]
            for _ in range(35):  # hold the last frame for a second
                if not display.frame(state, info):
                    return
                if not record:
                    time.sleep(1 / 35)
    finally:
        display.close()
        game.close()
