Mode: real time

| Policy | Score | Kills | Decisions/s | Latency p50 | p95 | Skipped slots | Turn choices |
| --- | --- | --- | --- | --- | --- | --- | --- |
| scripted | +21.5 (sd 1.8) | 22.5 | 8.8 | 0.0 ms | 0.0 ms | 0.0 | advance 14%, hold 15%, left 5%, nudge_left 6%, nudge_right 9%, right 20%, scan 31% |
| trained | +21.6 (sd 2.2) | 22.6 | 8.8 | 7.5 ms | 20.3 ms | 0.0 | advance 14%, hold 16%, left 4%, nudge_left 5%, nudge_right 9%, right 20%, scan 32% |
| pixels | +19.7 (sd 0.9) | 20.7 | 8.7 | 74.0 ms | 96.5 ms | 3.4 | advance 10%, hold 11%, left 8%, nudge_left 9%, nudge_right 14%, right 19%, scan 28% |
