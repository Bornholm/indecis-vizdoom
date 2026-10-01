Mode: real time

| Policy | Score | Kills | Decisions/s | Latency p50 | p95 | Skipped slots | Turn choices |
| --- | --- | --- | --- | --- | --- | --- | --- |
| scripted | +21.8 (sd 1.6) | 22.8 | 8.8 | 0.0 ms | 0.0 ms | 0.0 | advance 14%, hold 16%, left 6%, nudge_left 5%, nudge_right 10%, right 20%, scan 30% |
| random | +0.2 (sd 1.0) | 1.1 | 8.8 | 0.0 ms | 0.0 ms | 0.0 | advance 15%, hold 14%, left 14%, nudge_left 15%, nudge_right 13%, right 15%, scan 14% |
| trained | +21.8 (sd 1.6) | 22.8 | 8.8 | 6.8 ms | 19.7 ms | 0.0 | advance 14%, hold 16%, left 6%, nudge_left 6%, nudge_right 10%, right 20%, scan 30% |
| backbone | +5.5 (sd 1.2) | 6.5 | 8.8 | 12.6 ms | 30.9 ms | 0.0 | hold 15%, left 57%, right 28% |
| pixels | +20.9 (sd 1.5) | 21.9 | 8.8 | 49.7 ms | 68.0 ms | 0.0 | advance 13%, hold 14%, left 7%, nudge_left 9%, nudge_right 10%, right 21%, scan 26% |
