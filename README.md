# indecis-vizdoom

A small [indecis](https://github.com/Bornholm/indecis) model plays [ViZDoom](https://github.com/Farama-Foundation/ViZDoom)'s `defend_the_center`: the player stands in a round room, turns, walks and shoots at monsters coming from every side. The idea comes from [laya-doom](https://github.com/dylanbstorey/laya-doom), where LAYA, a 421M-parameter decision model, plays the same scenario.

Everything is pinned for reproducibility: indecis v0.2.0 release binaries (checksums verified), bekko-embedding-v1-a8m at a fixed Hugging Face revision, ViZDoom 1.3.1, fixed seeds.

## How it plays

Every 4 tics (8.75 times per second), the game state becomes a short English text:

> Health 100%, 26 bullets left. 2 enemies in sight. The nearest, a demon, is at mid range and to the left of the crosshair. Another, a marine with a chainsaw, is far away and far to the right of the crosshair.

The model answers two questions about it:

- `fire` (yes/no): is an enemy lined up with the crosshair?
- `turn` (choice): `left`, `right`, `hold`, `advance` (walk toward a far enemy) or `scan` (turn to search the room).

`indecis-serve` answers over HTTP with the TypeSafe decision API, the format laya-doom uses with LAYA.

In real time, latency costs game time: a decision taken on the state at a slot takes effect `latency / 28.6 ms` tics later (Doom runs at 35 tics per second), the previous action staying applied meanwhile, and the slots that open while a decision is computed are skipped. The engine itself runs in synchronous mode, so this accounting is exact and the runs are reproducible up to the measured latencies. In lockstep, the game waits for each decision.

## Policies

| Policy | Decision |
| --- | --- |
| `scripted` | code: turn toward the nearest enemy, fire when one is lined up |
| `random` | uniform choice, for the floor |
| `trained` | a8m fine-tuned on states labeled by `scripted` |
| `backbone` | a8m without training, in open mode: compares the state with the description of each option |

All four read the same observation and drive the same buttons, so a gap in score comes from the decision alone.

## Reproducing

Requires Linux (amd64 or arm64), [uv](https://docs.astral.sh/uv/), curl and make.

```bash
make tools      # indecis v0.2.0, then `indecis check` on this processor
make backbone   # bekko-embedding-v1-a8m, 210 MB
make data       # 200 training episodes, 40 test episodes, played by `scripted`
make model      # about 11 minutes on a laptop
make bench      # the four policies, 20 episodes each, in real time then in lockstep
```

## Watching it play

```bash
make show                  # a 1920x1080 window; SHOW_SCALE=0.6 for a smaller one
make video                 # the same, recorded to build/indecis-doom.mp4 (needs ffmpeg)
make video SHOW_EPISODES=1
```

The window shows the game with a box around each enemy the observation found (green when lined up with the crosshair), the text the model read for its current decision, the probabilities of its answers, and its latency. It runs the same real-time loop as the bench, one frame per tic. Escape quits.

## Results

20 episodes per policy (seeds 2001 to 2020, never used for training), on a laptop (Core Ultra 7 265U), September 28, 2026:

| Policy | Score, real time | Kills | Score, lockstep | Latency p50 | p95 | Skipped slots |
| --- | --- | --- | --- | --- | --- | --- |
| `scripted` | +12.8 (sd 6.6) | 13.8 | +12.8 | 0 | 0 | 0 |
| `trained` | +12.2 (sd 6.1) | 13.2 | +12.8 | 8.5 ms | 21.1 ms | 0 |
| `backbone` | +0.9 (sd 1.2) | 1.9 | +1.0 | 8.5 ms | 19.8 ms | 0 |
| `random` | +0.9 (sd 1.4) | 1.9 | +0.9 | 0 | 0 | 0 |

The score is the scenario's reward: one point per kill, minus one for dying. Full tables, with the share of each `turn` answer, are in `results/`.

- The trained model gets every one of the 3,278 test states right, and in lockstep it plays exactly like `scripted`. In real time it reaches 95% of its score: a few decisions take longer than one tic (28.6 ms) and arrive one tic late.
- Latency includes the HTTP round trip. The model itself takes 5.4 ms on a performance core for these 60-token texts; the operating system often schedules the server on the efficiency cores, two to three times slower.
- For comparison, laya-doom reports +8.0 for LAYA (421M parameters, p50 98.5 ms on an M1 Max, 65 skipped slots per episode) and +12.4 for its scripted policy, with its own state description, action mapping and hardware. The numbers are not directly comparable.

## What this shows, and what it does not

- The trained model imitates `scripted`, which labels its data. It cannot play better than the script; it answers from text, fast enough to never skip a decision slot.
- The backbone alone does not play: open mode ranks options but cannot tell "the enemy is on the left" from "on the right" without training.
- Beating the script would need labels from outcomes (which decisions led to kills), not from a rule.

## License

MIT. ViZDoom is under the MIT license, its scenarios use Freedoom assets (BSD).
