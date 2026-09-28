"""Playing episodes.

In lockstep, the game waits for each decision: latency does not matter.

In real time, latency costs game time, as if the game ran at 35 tics per
second while the policy thinks. The game is advanced by the engine in
synchronous mode, so the result is reproducible: a decision taken on the
state at a slot arrives `latency / 28.6 ms` tics later; until then the
previous action stays applied. A decision slot opens every `interval`
tics; the slots that open while a decision is being computed are skipped.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from .game import buttons, kills, observation
from .policies import Decision, timed
from .state import describe

TICS_PER_SECOND = 35


@dataclass
class Episode:
    seed: int
    score: float
    kills: int
    tics: int
    decisions: int
    skipped: int
    latencies: list[float] = field(default_factory=list)
    turns: dict[str, int] = field(default_factory=dict)

    @property
    def decisions_per_second(self) -> float:
        return self.decisions / max(self.tics / TICS_PER_SECOND, 1e-9)


def _count(ep: Episode, d: Decision) -> None:
    ep.decisions += 1
    ep.turns[d.turn] = ep.turns.get(d.turn, 0) + 1


def lockstep(game, policy, seed: int, interval: int = 4, record=None) -> Episode:
    game.set_seed(seed)
    game.new_episode()
    ep = Episode(seed, 0, 0, 0, 0, 0)
    while not game.is_episode_finished():
        obs = observation(game)
        d, ms = timed(policy, obs)
        if record is not None:
            record(describe(obs), d)
        ep.latencies.append(ms)
        _count(ep, d)
        game.make_action(buttons(d), interval)
        ep.tics += interval
    ep.score, ep.kills = game.get_total_reward(), kills(game)
    return ep


TIC_MS = 1000 / TICS_PER_SECOND


def realtime(game, policy, seed: int, interval: int = 4, on_tic=None) -> Episode:
    """on_tic(state, info) is called before each tic, for display; it
    returns False to stop."""
    game.set_seed(seed)
    game.new_episode()
    ep = Episode(seed, 0, 0, 0, 0, 0)
    action = [0, 0, 0, 0]
    info: dict = {"decision": None, "text": "", "latencies": ep.latencies}
    while not game.is_episode_finished():
        obs = observation(game)
        d, ms = timed(policy, obs)
        ep.latencies.append(ms)
        _count(ep, d)
        delay = int(ms // TIC_MS)
        slots = delay // interval + 1
        ep.skipped += slots - 1
        for i in range(slots * interval):
            if game.is_episode_finished():
                break
            if i == delay:
                action = buttons(d)
                info.update(decision=d, text=describe(obs))
            if on_tic is not None:
                info.update(skipped=ep.skipped, kills=kills(game), tics=ep.tics,
                            decisions_per_second=ep.decisions_per_second)
                if on_tic(game.get_state(), info) is False:
                    return ep
            game.make_action(action, 1)
            ep.tics += 1
    ep.score, ep.kills = game.get_total_reward(), kills(game)
    return ep


def summary(policy: str, eps: list[Episode]) -> dict:
    lat = sorted(x for e in eps for x in e.latencies)
    pct = lambda q: lat[min(len(lat) - 1, int(q * len(lat)))] if lat else 0.0
    scores = [e.score for e in eps]
    turns: dict[str, int] = {}
    for e in eps:
        for k, v in e.turns.items():
            turns[k] = turns.get(k, 0) + v
    total = sum(turns.values()) or 1
    return {
        "policy": policy,
        "episodes": len(eps),
        "score": statistics.mean(scores),
        "score_sd": statistics.stdev(scores) if len(scores) > 1 else 0.0,
        "kills": statistics.mean(e.kills for e in eps),
        "decisions_per_second": statistics.mean(e.decisions_per_second for e in eps),
        "latency_p50_ms": pct(0.5),
        "latency_p95_ms": pct(0.95),
        "skipped_per_episode": statistics.mean(e.skipped for e in eps),
        "turns": {k: round(v / total, 3) for k, v in sorted(turns.items())},
    }
