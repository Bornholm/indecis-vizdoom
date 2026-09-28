"""Decision procedures. All read the same observation and answer the same
two questions, so that a gap in score comes from the decision alone."""

from __future__ import annotations

import http.client
import json
import random
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .questions import QUESTIONS, TURN_OPTIONS
from .state import Observation, describe


@dataclass
class Decision:
    fire: bool
    turn: str
    p_fire: float = 0.0
    turn_probs: dict[str, float] = field(default_factory=dict)


def scripted(obs: Observation) -> Decision:
    """Turns toward the nearest enemy and fires when one is lined up. It
    labels the training data, so it is the ceiling of the trained model."""
    nearest = obs.nearest
    if nearest is None:
        turn = "scan"
    elif nearest.lined_up:
        turn = "advance" if nearest.far else "hold"
    else:
        turn = nearest.side
    fire = obs.lined_up
    return Decision(fire, turn, 1.0 if fire else 0.0, {turn: 1.0})


class Scripted:
    name = "scripted"

    def decide(self, obs: Observation) -> Decision:
        return scripted(obs)

    def close(self) -> None:
        pass


class Random:
    name = "random"

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def decide(self, obs: Observation) -> Decision:
        fire = self.rng.random() < 0.5
        return Decision(fire, self.rng.choice(TURN_OPTIONS), float(fire))

    def close(self) -> None:
        pass


class Indecis:
    """Asks indecis-serve (TypeSafe decision API) over a kept-alive connection."""

    def __init__(self, url: str, model: str, threshold: float = 0.5) -> None:
        u = urlparse(url)
        self.conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=10)
        self.model, self.threshold = model, threshold
        self.name = f"indecis:{model}"

    def decide(self, obs: Observation) -> Decision:
        body = json.dumps({"model": self.model, "state": describe(obs), "questions": QUESTIONS})
        self.conn.request("POST", "/api/alpha/decisions", body, {"Content-Type": "application/json"})
        res = self.conn.getresponse()
        data = json.loads(res.read())
        if res.status != 200:
            raise RuntimeError(f"indecis-serve: {res.status} {data}")
        fire, turn = data["answers"]["fire"], data["answers"]["turn"]
        return Decision(fire["noul"] >= self.threshold, turn["choice"], fire["noul"], turn.get("probabilities", {}))

    def close(self) -> None:
        self.conn.close()


def timed(policy, obs: Observation) -> tuple[Decision, float]:
    """Decision and its latency in milliseconds."""
    start = time.perf_counter()
    d = policy.decide(obs)
    return d, (time.perf_counter() - start) * 1000
