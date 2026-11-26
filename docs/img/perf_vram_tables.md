| card | strategy | ask p50/p95/p99 | hearing p50/p95/p99 | face look p50/p95/p99 | camera p50/p95/p99 | background jobs in 60 s | on the GPU |
|---|---|---|---|---|---|---|---|
| 2 GB | spill | 71 / 5124 / 5269 | 4145 / 5008 / 5080 | 80 / 197 / 209 | 95 / 126 / 140 | 13 | none |
| 2 GB | swap | 75 / 4231 / 5144 | 3990 / 4630 / 4799 | 78 / 186 / 206 | 95 / 126 / 145 | 14 | none |
| 2 GB | hybrid | 92 / 9919 / 10289 | 8037 / 10927 / 12052 | 83 / 217 / 242 | 96 / 127 / 142 | 86 | none |
| 4 GB | spill | 70 / 2248 / 2578 | 1041 / 1563 / 1774 | 91 / 234 / 275 | 95 / 129 / 143 | 50 | whisper-th-medium-ct2 |
| 4 GB | swap | 93 / 4266 / 4950 | 3981 / 4395 / 4521 | 78 / 187 / 203 | 95 / 127 / 141 | 14 | small |
| 4 GB | hybrid | 94 / 3849 / 5462 | 1593 / 3487 / 4377 | 87 / 219 / 264 | 95 / 127 / 143 | 96 | whisper-th-medium-ct2 |
| 6 GB | spill | 68 / 2185 / 2482 | 1110 / 1542 / 1747 | 86 / 202 / 226 | 95 / 126 / 146 | 50 | medium, whisper-th-medium-ct2 |
| 6 GB | swap | 78 / 3180 / 3620 | 3666 / 3902 / 3994 | 78 / 184 / 200 | 95 / 126 / 145 | 16 | Qwen2.5-0.5B-Instruct, medium, small |
| 6 GB | hybrid | 90 / 4540 / 6344 | 1525 / 4452 / 4661 | 96 / 227 / 269 | 95 / 126 / 139 | 96 | medium, whisper-th-medium-ct2 |
| 8 GB | spill | 68 / 1444 / 1802 | 1025 / 1307 / 1421 | 93 / 199 / 228 | 95 / 127 / 144 | 84 | Qwen2.5-0.5B-Instruct, medium, small, whisper-th-medium-ct2 |
| 10 GB | spill | 69 / 1543 / 1774 | 1036 / 1328 / 1421 | 96 / 205 / 238 | 95 / 127 / 141 | 81 | Qwen2.5-0.5B-Instruct, medium, small, whisper-th-medium-ct2 |
| 12 GB | spill | 67 / 1699 / 2020 | 1064 / 1347 / 1466 | 96 / 203 / 246 | 95 / 126 / 146 | 78 | Qwen2.5-0.5B-Instruct, medium, small, whisper-th-medium-ct2 |
| whole card | spill | 72 / 1517 / 2027 | 997 / 1326 / 1518 | 93 / 200 / 233 | 95 / 127 / 141 | 81 | Qwen2.5-0.5B-Instruct, medium, small, whisper-th-medium-ct2 |
