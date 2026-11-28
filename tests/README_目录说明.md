# tests/ 目录说明

目录保持扁平（CI 用 `python3 -m unittest discover -s tests` 直接发现），文件按用途分四类：

| 前缀/类型 | 用途 | 例子 |
|---|---|---|
| `test_*.py` | 单元与回归测试（CI 自动发现，必须全绿） | `test_engine_paths.py`、`test_lstpn_parallel.py` |
| `run_*.py` | 正式实验/矩阵的入口（Actions 工作流调用，可断点续跑） | `run_e3_07_matrix.py`、`run_e3_10_stage2.py` |
| `audit_*.py` `probe_*.py` | 域事实审计与规模探测（一次性证据生成） | `audit_fault_saturation.py`、`probe_scale.py` |
| `build_*.py` `merge_*.py` `split_*.py` | 台账/工件构建与合并工具 | `build_frozen_domain.py`、`merge_final_ledger.py` |
| `accept_e3.py` | 继承证据内容门禁（CI 调用） | — |

新增文件按此命名；正式实验入口一律 `run_` 前缀，测试一律 `test_` 前缀。
