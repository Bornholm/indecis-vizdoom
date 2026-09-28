Mode: lockstep

| Policy | Score | Kills | Decisions/s | Latency p50 | p95 | Skipped slots | Turn choices |
| --- | --- | --- | --- | --- | --- | --- | --- |
| scripted | +21.8 (sd 1.6) | 22.8 | 8.8 | 0.0 ms | 0.0 ms | 0.0 | advance 14%, hold 16%, left 6%, nudge_left 5%, nudge_right 10%, right 20%, scan 30% |
| random | +0.2 (sd 1.0) | 1.1 | 8.8 | 0.0 ms | 0.0 ms | 0.0 | advance 15%, hold 14%, left 14%, nudge_left 15%, nudge_right 13%, right 15%, scan 14% |
| trained | +21.8 (sd 1.6) | 22.8 | 8.8 | 6.2 ms | 17.6 ms | 0.0 | advance 14%, hold 16%, left 6%, nudge_left 5%, nudge_right 10%, right 20%, scan 30% |
| backbone | +5.6 (sd 0.8) | 6.6 | 8.8 | 10.2 ms | 28.0 ms | 0.0 | hold 16%, left 56%, right 28% |
