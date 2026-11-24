# R6_E3 文件清理台账

用途：登记每次清理删除的文件、内容、原因与删除前核验，防止误读废弃/错误文件分散注意力。每周由定时任务执行一次增量清理并追加记录。

## 永不删除（红线）

- `baseline_readonly/`（冻结输入、E2 快照、ZIP）
- `contracts/`、`reports/`（合同、台账、签署申请）
- `runs/` 下被任何报告/测试引用的证据，以及失败、超时、未决记录（合同要求保留）
- `implementations/`、`oracles/`、`tests/`、`models/`、`.github/`
- 变异测试的首轮失败日志（如 `timed_trace_mutants/`、`local_source_mutants/`）

## 删除记录

### 2026-11-24（首次）

| 删除对象 | 内容 | 原因 | 删除前核验 |
|---|---|---|---|
| `runs/math_p0/content_gate/disposable/`（196 MB） | E2 冻结快照的可写副本，内含第 11 轮故意注入的两处篡改（R604 结果翻转、TINA 首行 BOUNDED→UNBOUNDED）及全部 E2 运行残留 | 篡改副本与真冻结快照并存，极易误读为真证据；可由 `tests/run_gate_e2e_negatives.py` 随时从冻结快照重建 | 全库 grep 确认仅该重建脚本引用此路径；回归 58 项测试通过 |
| `runs/domain_audit_run.log` | 故障饱和审计的终端输出 | 与 `runs/domain_audit/audit_run.log` 逐字节重复 | `cmp` 一致 |
| `runs/math_p0/scale_probe.jsonl` | 三模型规模探针输出 | 与 `runs/math_p0/scale_probe/probe.jsonl` 逐字节重复 | `cmp` 一致 |
| `/tmp/tina_replay.json(.err)`、`/tmp/runlog.txt`、`/tmp/probe_log.txt` | TINA 重放输出、Actions 日志临时副本 | 临时文件；正式副本已归档于 `runs/math_p0/tina_raw_replay/`、`runs/actions/` | `cmp` 一致（tina）；日志类已在证据目录留存 |

清理效果：`runs/` 由 226 MB 降至 30 MB。

## 增量清理规则（每次执行）

1. 只删：与归档副本逐字节重复的散落文件、/tmp 临时副本、可由脚本重建的篡改/实验副本、`__pycache__`、超过 14 天且无任何引用的 runner 下载缓存。
2. 删前必须：grep 全库引用（tests/、reports/、contracts/、.github/）确认为零引用或可重建；重复文件用 `cmp` 核验。
3. 每次删除后在本文件追加一行记录（对象、内容、原因、核验）。
4. 拿不准的一律保留并记入"待裁定"小节，不擅自删。
