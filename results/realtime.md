Mode: real time

| Policy | Score | Kills | Decisions/s | Latency p50 | p95 | Skipped slots | Turn choices |
| --- | --- | --- | --- | --- | --- | --- | --- |
| scripted | +12.8 (sd 6.6) | 13.8 | 8.8 | 0.0 ms | 0.0 ms | 0.0 | advance 2%, hold 14%, left 29%, right 41%, scan 14% |
| random | +0.9 (sd 1.4) | 1.9 | 8.8 | 0.0 ms | 0.0 ms | 0.0 | advance 19%, hold 20%, left 21%, right 20%, scan 20% |
| trained | +12.2 (sd 6.1) | 13.2 | 8.8 | 8.5 ms | 21.1 ms | 0.0 | advance 2%, hold 13%, left 29%, right 41%, scan 14% |
| backbone | +0.9 (sd 1.2) | 1.9 | 8.8 | 8.5 ms | 19.8 ms | 0.0 | hold 89%, left 8%, right 3% |
