"""Game state to text.

The model reads a short English description of what the player sees. The
code computes the observation (where each enemy is, how far, whether it is
lined up with the crosshair); the model decides what to do about it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Monster actors of the ViZDoom scenarios. ViZDoom's own marines are named
# Marine...Vzd. Corpses (Dead...), blood and bullet puffs are not enemies.
MONSTERS = frozenset({
    "Zombieman", "ShotgunGuy", "ChaingunGuy", "DoomImp", "Demon", "Spectre",
    "Cacodemon", "BaronOfHell", "HellKnight", "LostSoul", "PainElemental",
    "Revenant", "Fatso", "Arachnotron", "Archvile", "Cyberdemon",
    "SpiderMastermind", "WolfensteinSS",
})

NAMES = {
    "Zombieman": "a zombie", "ShotgunGuy": "a shotgun zombie", "ChaingunGuy": "a chaingun zombie",
    "DoomImp": "an imp", "Demon": "a demon", "Spectre": "a spectre", "Cacodemon": "a cacodemon",
    "LostSoul": "a lost soul", "BaronOfHell": "a baron of hell", "HellKnight": "a hell knight",
}

# World units. In defend_the_center, monsters spawn about 700 units away.
DISTANCES = ((200, "very close"), (400, "close"), (650, "at mid range"))
FAR = "far away"

# Fraction of the half screen width (45 degrees with Doom's 90 degree view).
BEARINGS = ((0.15, "slightly to the {side} of"), (0.5, "to the {side} of"))
FAR_BEARING = "far to the {side} of"

MAX_DESCRIBED = 3


def is_monster(name: str) -> bool:
    if name.startswith("Dead"):
        return False
    return name in MONSTERS or name.startswith("Marine")


def plain_name(name: str) -> str:
    if name.startswith("Marine"):
        return "a marine with a chainsaw" if "Chainsaw" in name else "a marine"
    return NAMES.get(name, "an enemy")


@dataclass(frozen=True)
class Enemy:
    name: str
    offset: float  # -1 (left edge) to 1 (right edge) of the screen
    distance: float
    lined_up: bool  # the crosshair falls inside its bounding box

    @property
    def side(self) -> str:
        return "left" if self.offset < 0 else "right"

    @property
    def far(self) -> bool:
        return self.distance >= DISTANCES[-1][0]

    @property
    def close(self) -> bool:
        """"very close" or "close" in the text."""
        return self.distance < DISTANCES[1][0]

    @property
    def slightly_off(self) -> bool:
        """"slightly to the ... of the crosshair" in the text."""
        return not self.lined_up and abs(self.offset) <= BEARINGS[0][0]

    def where(self) -> str:
        if self.lined_up:
            return "lined up with the crosshair"
        for limit, phrase in BEARINGS:
            if abs(self.offset) <= limit:
                return phrase.format(side=self.side) + " the crosshair"
        return FAR_BEARING.format(side=self.side) + " the crosshair"

    def how_far(self) -> str:
        for limit, phrase in DISTANCES:
            if self.distance < limit:
                return phrase
        return FAR


@dataclass(frozen=True)
class Observation:
    health: int
    ammo: int
    enemies: tuple[Enemy, ...] = field(default_factory=tuple)  # nearest first

    @property
    def nearest(self) -> Enemy | None:
        return self.enemies[0] if self.enemies else None

    @property
    def lined_up(self) -> bool:
        return any(e.lined_up for e in self.enemies)


def observe(labels, width: int, player_xy: tuple[float, float], health: float, ammo: float) -> Observation:
    """Builds an observation from ViZDoom labels (state.labels)."""
    centre = width / 2
    px, py = player_xy
    enemies = []
    for label in labels:
        if not is_monster(label.object_name):
            continue
        middle = label.x + label.width / 2
        distance = ((label.object_position_x - px) ** 2 + (label.object_position_y - py) ** 2) ** 0.5
        lined_up = label.x <= centre <= label.x + label.width
        enemies.append(Enemy(label.object_name, (middle - centre) / centre, distance, lined_up))
    enemies.sort(key=lambda e: e.distance)
    return Observation(int(health), int(ammo), tuple(enemies))


def describe(obs: Observation) -> str:
    """The text the model reads."""
    parts = [f"Health {obs.health}%, {obs.ammo} bullets left."]
    if not obs.enemies:
        parts.append("No enemy in sight.")
        return " ".join(parts)
    n = len(obs.enemies)
    parts.append("One enemy in sight." if n == 1 else f"{n} enemies in sight.")
    for i, e in enumerate(obs.enemies[:MAX_DESCRIBED]):
        lead = "The nearest" if i == 0 else "Another"
        parts.append(f"{lead}, {plain_name(e.name)}, is {e.how_far()} and {e.where()}.")
    if obs.lined_up and not any(e.lined_up for e in obs.enemies[:MAX_DESCRIBED]):
        parts.append("An enemy further back is lined up with the crosshair.")
    return " ".join(parts)
