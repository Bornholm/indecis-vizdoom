# indecis-vizdoom

A small [indecis](https://github.com/Bornholm/indecis) model plays [ViZDoom](https://github.com/Farama-Foundation/ViZDoom)'s `defend_the_center`: the player stands in a round room, turns, walks and shoots at monsters coming from every side. The idea comes from [laya-doom](https://github.com/dylanbstorey/laya-doom), where LAYA, a 421M-parameter decision model, plays the same scenario.

Everything is pinned for reproducibility: indecis v0.3.0 release binaries (checksums verified), bekko-embedding-v1-a8m at a fixed Hugging Face revision, ViZDoom 1.3.1, fixed seeds.

## Demo

**Defend the center**

[![indecis plays doom - defend the center](https://img.youtube.com/vi/QVsEgyEuKkM/0.jpg)](https://www.youtube.com/watch?v=QVsEgyEuKkM)


**Deadly corridor**

[![indecis plays doom - deadly corridor](https://img.youtube.com/vi/EwJQimi4GRo/0.jpg)](https://www.youtube.com/watch?v=EwJQimi4GRo)

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
make tools      # indecis v0.3.0, then `indecis check` on this processor
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

20 episodes per policy on `defend_the_center` (seeds 2001 to 2020, never used for training), on a laptop (Core Ultra 7 265U), with indecis v0.3.0, October 1, 2026:

| Policy | Score, real time | Kills | Score, lockstep | Latency p50 | p95 | Skipped slots |
| --- | --- | --- | --- | --- | --- | --- |
| `scripted` | +21.8 (sd 1.6) | 22.8 | +21.8 | 0 | 0 | 0 |
| `trained` | +21.8 (sd 1.6) | 22.8 | +21.8 | 6.8 ms | 19.7 ms | 0 |
| `backbone` | +5.5 (sd 1.2) | 6.5 | +5.6 | 12.6 ms | 30.9 ms | 0 |
| `random` | +0.2 (sd 1.0) | 1.1 | +0.2 | 0 | 0 | 0 |

The score is the scenario's reward: one point per kill, minus one for dying. Full tables, with the share of each `turn` answer, are in `results/`.

- The trained model gets every one of the 3,637 test states right, and plays exactly like `scripted`, episode by episode, in real time too: its decisions take less than one tic (28.6 ms).
- Latency includes the HTTP round trip. The model itself takes about 5 ms on a performance core for these 60-token texts; the operating system often schedules the server on the efficiency cores, two to three times slower. The server process takes about 65 MB of memory, 58 MB of it private.
- Moving from indecis v0.2.0 to v0.3.0 changed nothing measurable: `make model` gives byte-identical weights, and with the server pinned to one core both versions answer in 5.8 ms (p50, HTTP included). Unpinned, the p50 moves between 6.8 and 10.3 ms from run to run with either version, depending on the cores the system picks.
- For comparison, laya-doom reports +8.0 for LAYA (421M parameters, p50 98.5 ms on an M1 Max, 65 skipped slots per episode) and +12.4 for its scripted policy, with its own state description, action mapping and hardware. The numbers are not directly comparable.

### A scenario it never saw: `deadly_corridor`

The same model, trained on `defend_the_center` only, in a corridor lined with shooting enemies (10 episodes, seeds 2001 to 2010). The reward is the distance walked toward the armor at the end, minus 100 for dying:

| Policy | Score | Kills |
| --- | --- | --- |
| `scripted` | +311.8 (sd 259.2) | 5.3 |
| `trained` | +363.4 (sd 249.4) | 5.7 |
| `random` | +41.9 (sd 128.5) | 0.9 |

The text description does not depend on the map, so the model plays as the script would: same scores on 9 episodes out of 10, the tenth differing by a decision that arrived a tic later. Neither reaches the armor: the difficulty is set to the maximum, and nothing in the description tells where the corridor leads.

### What SIMD buys

The same trained model, served by indecis v0.2.0 built three ways, 20 real-time episodes each, server pinned to a performance core:

| Server | Latency p50 | Decisions/s | Skipped slots per episode | Score |
| --- | --- | --- | --- | --- |
| pure Go: no SIMD, no assembly (`GOEXPERIMENT=` and `INDECIS_NOASM=1`) | 180 ms | 4.7 | 60 | +2.1 |
| Go 1.27 portable SIMD only (`INDECIS_NOASM=1`) | 23 ms | 8.8 | 0 | +21.0 |
| release binary: portable SIMD, AVX2 + FMA and AVX-VNNI kernels | 4.7 ms | 8.8 | 0 | +21.8 |

In pure Go, a decision takes longer than the 114 ms between two slots: the player reacts two slots late, skips 60 slots per episode and scores ten times less. Measured on a single decision outside the game, pure Go takes 256 ms and the full stack 5.1 ms. Raw results: `results/simd-*.json`.

### From pixels

The same questions, answered from the raw frame instead of the text: 320×240 pixels, no HUD, no game data. The [SigLIP 2](https://huggingface.co/google/siglip2-base-patch32-256) image encoder (86M parameters, frozen) turns the frame into 64 patches of 32×32 pixels; a small spatial head, trained with `indecis train-vision` on frames labeled by `scripted`, reads each patch at its position.

```bash
make siglip
make data-pixels     # 6,671 training frames (60 episodes), 1,697 test frames (15 others)
make model-pixels    # encodes the frames (5 min), trains the head (30 s)
make bench-pixels
make video-pixels    # build/pixels.mp4
```

Each training frame is also used mirrored, left and right swapped: the scripted rules are symmetric about the screen center. The head reads the patches after 8 of the encoder's 12 layers, and the encoder stops there: a third less compute. On the test frames, it answers `fire` right 92.9% of the time and `turn` (7 options) 85.5%. In play, 20 real-time episodes (seeds 2001 to 2020), September 29, 2026; the default model again with indecis v0.3.0 on October 1, 2026:

| Pixel model | Score | Kills | Latency p50 | p95 | Skipped slots |
| --- | --- | --- | --- | --- | --- |
| mirrored frames, layer 8 (default) | +21.1 (sd 2.2) | 22.1 | 50.3 ms | 69.1 ms | 0.3 |
| mirrored frames, last layer | +19.4 (sd 2.1) | 20.4 | 72.5 ms | 92.7 ms | 2.0 |
| no mirroring, last layer | +18.9 (sd 2.8) | 19.9 | 71.4 ms | 90.7 ms | 1.1 |
| mirrored frames, two rounds of DAgger, last layer | +17.2 (sd 2.1) | 18.2 | 72.9 ms | 91.3 ms | 1.6 |

For reference, on the same 20 episodes, `scripted` scores +21.8 (sd 1.6) and the text model +22.1 (sd 1.6). From pixels alone, the model reaches 97% of the script's score, deciding in 50 ms, image encoding and HTTP included. Retrained with the v0.3.0 release, the head is byte-identical to the one trained before the image path was released. DAgger (the pixel model plays, the script labels what it sees) kept the test accuracy but lowered the score; mirroring raised the test accuracy by 6 points on `turn` for a gain in play within the noise. Test accuracy on frames the script saw predicts play poorly.

The server holds 128 MB after startup and about 214 MB under load: learned questions do not load SigLIP's text tower.

## What this shows, and what it does not

- The trained model imitates `scripted`, which labels its data. It cannot play better than the script; it answers from text, fast enough to never skip a decision slot.
- The backbone alone does not play: open mode ranks options but cannot tell "the enemy is on the left" from "on the right" without training.
- Beating the script would need labels from outcomes (which decisions led to kills), not from a rule.

## License

MIT. ViZDoom is under the MIT license; its scenarios use Freedoom assets, graphics, music and sounds, under the BSD license.
