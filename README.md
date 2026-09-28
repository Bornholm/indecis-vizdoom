# indecis-vizdoom

A small [indecis](https://github.com/Bornholm/indecis) model plays [ViZDoom](https://github.com/Farama-Foundation/ViZDoom)'s `defend_the_center`: the player stands in a round room, turns, walks and shoots at monsters coming from every side. The idea comes from [laya-doom](https://github.com/dylanbstorey/laya-doom), where LAYA, a 421M-parameter decision model, plays the same scenario.

Everything is pinned for reproducibility: indecis v0.2.0 release binaries (checksums verified), bekko-embedding-v1-a8m at a fixed Hugging Face revision, ViZDoom 1.3.1, fixed seeds.

## How it plays

Every 4 tics (8.75 times per second), the game state becomes a short English text:

> Health 100%, 26 bullets left. 2 enemies in sight. The nearest, a demon, is at mid range and to the left of the crosshair. Another, a marine with a chainsaw, is far away and far to the right of the crosshair.

The model answers two questions about it:

- `fire` (yes/no): is an enemy lined up with the crosshair?
- `turn` (choice): `left` or `right` (enemy well off the crosshair: 10 degrees), `nudge_left` or `nudge_right` (enemy slightly off: 2 degrees), `hold` (lined up and close: stop and shoot), `advance` (lined up but not close: walk toward it) or `scan` (nothing in sight: walk and turn to search).

Turns use ViZDoom's delta button, an exact angle per tic. The plain turn buttons accelerate when held, which made the aim overshoot and swing from side to side; with fixed angles and small nudges near the target, the scripted policy went from +12.8 to +21.8.

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
make video                 # the same, recorded with sound to build/defend_the_center.mp4 (needs ffmpeg)
make video SHOW_EPISODES=1
```

The window shows the game with a box around each enemy the observation found (green when lined up with the crosshair), the text the model read for its current decision, the probabilities of its answers, its latency and the memory of the model server. It runs the same real-time loop as the bench, one frame per tic. Escape quits.

Recorded videos carry the game's own sound, captured tic by tic: Freedoom's music and sound effects, under the BSD license. `SCENARIO=deadly_corridor make video` records the other scenario.

## Results

20 episodes per policy on `defend_the_center` (seeds 2001 to 2020, never used for training), on a laptop (Core Ultra 7 265U), September 28, 2026:

| Policy | Score, real time | Kills | Score, lockstep | Latency p50 | p95 | Skipped slots |
| --- | --- | --- | --- | --- | --- | --- |
| `scripted` | +21.8 (sd 1.6) | 22.8 | +21.8 | 0 | 0 | 0 |
| `trained` | +21.8 (sd 1.6) | 22.8 | +21.8 | 6.0 ms | 16.0 ms | 0 |
| `backbone` | +5.8 (sd 0.7) | 6.8 | +5.6 | 10.6 ms | 25.7 ms | 0 |
| `random` | +0.2 (sd 1.0) | 1.1 | +0.2 | 0 | 0 | 0 |

The score is the scenario's reward: one point per kill, minus one for dying. Full tables, with the share of each `turn` answer, are in `results/`.

- The trained model gets every one of the 3,637 test states right, and plays exactly like `scripted`, episode by episode, in real time too: its decisions take less than one tic (28.6 ms).
- Latency includes the HTTP round trip. The model itself takes about 5 ms on a performance core for these 60-token texts; the operating system often schedules the server on the efficiency cores, two to three times slower. The server process takes about 65 MB of memory, 58 MB of it private.
- For comparison, laya-doom reports +8.0 for LAYA (421M parameters, p50 98.5 ms on an M1 Max, 65 skipped slots per episode) and +12.4 for its scripted policy, with its own state description, action mapping and hardware. The numbers are not directly comparable.

### A scenario it never saw: `deadly_corridor`

The same model, trained on `defend_the_center` only, in a corridor lined with shooting enemies (10 episodes, seeds 2001 to 2010). The reward is the distance walked toward the armor at the end, minus 100 for dying:

| Policy | Score | Kills |
| --- | --- | --- |
| `scripted` | +311.8 (sd 259.2) | 5.3 |
| `trained` | +363.4 (sd 249.4) | 5.7 |
| `random` | +41.9 (sd 128.5) | 0.9 |

The text description does not depend on the map, so the model plays as the script would: same scores on 9 episodes out of 10, the tenth differing by a decision that arrived a tic later. Neither reaches the armor: the difficulty is set to the maximum, and nothing in the description tells where the corridor leads.

## What this shows, and what it does not

- The trained model imitates `scripted`, which labels its data. It cannot play better than the script; it answers from text, fast enough to never skip a decision slot.
- The backbone alone does not play: open mode ranks options but cannot tell "the enemy is on the left" from "on the right" without training.
- Beating the script would need labels from outcomes (which decisions led to kills), not from a rule.

## License

MIT. ViZDoom is under the MIT license; its scenarios use Freedoom assets, graphics, music and sounds, under the BSD license.
