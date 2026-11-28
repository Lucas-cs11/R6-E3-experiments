# E3-11 四层独立终验：工具映射与缺口清单

依据合同 E3-11（字节、内容、数学、研究范围四层）。本文件把每层映射到已有工具和缺口，作为终验施工单。

## 第 1 层｜字节级（byte）

| 已有 | 位置 | 缺口 |
|---|---|---|
| 归档 ZIP SHA/CRC 核验（4,003+4,001 成员） | `runs/input_freeze/archive_verification.json` | 终验时对新交付 ZIP 重跑同流程（脚本可复用） |
| 权威清单 4,020 行逐行 SHA | `tests/verify_authority_manifest.py`（CI 每次推送运行） | 无 |
| 冻结输入指纹（ZIP/TeX/合同） | `contracts/input_inventory.json` | 无 |
| 解释器/工具版本登记 | `contracts/replay_environment.json` | 终验时补 sklearn 1.9.1、TINA 4.0.0、PRISM 4.11、Sirio 2.0.5 条目 |
| 外部原始数据可复现性分级 | PyScrew `AGENT_LOCAL_REPLAYED` vs `RAW_NOT_VERIFIED_ON_AUDITOR_MACHINE` | 终验 ZIP 不含原始 JSON 时必须显示 `FULL_RAW_REPRODUCIBLE=false`（合同硬性要求） |

## 第 2 层｜内容级（content）

| 已有 | 位置 | 缺口 |
|---|---|---|
| 继承证据语义重放（R604 六轨迹 + TINA 107,520 行） | `tests/accept_e3.py` + `oracles/independent/tina_raw_replay.py`（含 Pins） | 无（限定两份继承对象） |
| 六类端到端篡改负测 | `runs/math_p0/gate_semantic_v3/e2e_negatives/` | 终验时对交付 ZIP 重放 |
| 引擎结果证书（model/trace SHA） | 52×4 矩阵 144 份、E3-07 批处理 | 终验时从原始日志独立复算关键 verdict（不能只查 PASS/行数/哈希长度） |
| 质量/风险复算 | `immediate_mass`/`immediate_metrics`/`r6_components_e` 独立参考 | 567 概率运行后接入 |

## 第 3 层｜数学级（math）

| 已有 | 位置 | 缺口 |
|---|---|---|
| 区间/联合可行域独立多面体参考 | `oracles/independent/ap41_polytope.py` | 无 |
| 精确积分双算法（原函数 vs Simpson） | `r6_components_e(_reference).py` | 无 |
| 时间语义双实现（相对钟龄 vs 绝对日期） | `timed_trace.py` / `absolute_schedule.py` | 无 |
| 引擎独立参考（枚举+LP+差分约束） | `engine_paths_reference.py` | 深度≤9 边界已明示 |
| 概率证书绑定 | `immediate_evidence.py`（模型 SHA 钉死） | 567 运行后逐格接入 |

## 第 4 层｜研究范围级（scope）

| 已有 | 位置 | 缺口 |
|---|---|---|
| 当前证据口径（CURRENT 仅 3 项） | `reports/current_evidence_scope.md` + CI 核对 | 终验时按最终结果重算 |
| 域事实审计（故障饱和/语义身份/谱系） | `runs/domain_audit/`、`reports/formal_domain_adjudication_request.md` | 等签署 |
| 签署申请包 | 域、G2、同题、567 定义四份 | 等签署；签署后核对结论与申请一致性 |
| 未闭合清单 | `reports/remaining_blockers.md` | 终验时清零或逐项保留原因 |

## 终验执行顺序（合同建议）

1. 新交付 ZIP 洁净解压 → 第 1 层全量；
2. 第 2 层：继承证据 + 新运行证据的内容重放与篡改负测；
3. 第 3 层：抽样+全量关键 verdict 的独立复算（原始 TINA stdout、LP/积分中间数据）；
4. 第 4 层：范围对账（分母、签署、未决）；
5. 输出 `independent_acceptance.md`：每项有运行命令、原始证据路径、适用范围、当前状态、未解决反例；四层全过才授予 `E3_ACCEPTED_WITH_DECLARED_LIMITS`。

## 当前状态

第 1、2 层工具就绪并经实测；第 3 层组件级就绪、待 567/全量运行接入；第 4 层等签署。任何一层未过：总状态保持 `PARTIAL_NOT_CLOSED`。
