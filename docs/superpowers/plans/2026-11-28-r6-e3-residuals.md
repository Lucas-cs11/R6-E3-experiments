# R6-E3 剩余工作实施计划（E3-06/07/08/09/11/12）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在已有 R6_E3 工作区上闭合 E3-06/07/08/09/11/12，产出可交付的完整与便携证据 ZIP，并经四层独立验收。

**Architecture:** 实验全部在 GitHub Actions 上执行（cron 波次 + release 台账断点续跑，单任务≤8 分钟以避开平台杀进程，被杀自动接力）；实现按 TDD 编写并 push 前跑全量测试；每阶段以独立验收报告收尾；主线程只做计划、评审与用户对话，执行交子 Agent 与 Actions。

**Tech Stack:** Python 3（标准库 + fractions 精确有理数 + sklearn 1.9.1 仅 PyScrew 经验段）、GitHub Actions（托管 runner）、gh CLI、unittest。

**Spec:** `reports/rulings/decision_trace.csv`（12 条签署口径）、`reports/rulings/01_研究域_E3-05_主理论裁定附录.md`、`reports/rulings/02_G2集成审签_主理论裁定附录.md`、`reports/rulings/03_B1B2同题定义_主理论裁定附录.md`、`reports/rulings/04_概率567定义_主理论裁定附录.md`、`reports/verifications/e3_08_lh_spec.md`、`reports/verifications/e3_09_21points_verification.md`、执行指令 `baseline_readonly/inputs/R6_E3_v3_..._执行指令.md`。

## Global Constraints

- 冻结 TeX SHA-256 必须为 `a4196145...c174c5a`；E2 ZIP SHA `bb72a68a...8656715`；原始数据 release `de161758...2d545`。任一不符 → 停止数学任务并报阻断。
- 任何结果行必须有 `result_status`（NOT_EXECUTED/EXHAUSTED_FOR_MODEL/UNRESOLVED/UNSUPPORTED/FAILED）；禁止预填 verdict 或墙钟；禁止删行；TIMEOUT/失败/未决全保留。
- 证据分级：`SOURCE_REPORTED` / `INDEPENDENTLY_REPLAYED` / `MATH_SIGNED_SCOPE` / `FINAL_ACCEPTED` 四档不可混用。
- `G2=LIMITED`、`G4/G5/G7=NOT_CLOSED` 在主理论重新审签前不变；未过集成验收的全域结果标 `PROVISIONAL`。
- 不修改 frozen TeX、E2 ZIP 内任何字节、历史证据；不改数学定义或缩小正式域。
- 每个任务结束：全量测试全绿 → `git commit`（不 push，Lead 评审后统一 push）。

## Review Focus

1. cron 波次中 release 资产并发覆盖：两个波次同时上传同一 shard 会丢进度 → 上传前必须下载最新且 guard 串行。
2. 概率引擎的 Gamma 定义域（计划 X3 vs 观测 Y0）未裁定前，任何 Gamma 结果必须同时报两个定义值。
3. F2/F3 密度换到真实拓扑后 Pe 无闭式 → 只能报引擎值 + 独立参考值，禁止套用 F1 公式。
4. Q2/Q3 量化后观测类别为区间原子，推前分布与 Pe 需在量化空间重算，不能复用 Q1 数值。
5. E3-08 的 VACUOUS_WINDOW（R^c=∅ 导致 v_L=1）必须单列，不得并入诊断率分母的 PASS 计数。

---

### Task 1: 全量主实验完成与终账合并

**Files:**
- Modify: `.github/workflows/e3-e-full.yml:merge job`（已完成，核验其正确性）
- Create: `tests/merge_final_ledger.py`
- Test: `tests/test_merge_final_ledger.py`
- Output: `runs/e3_07/final_ledger.csv` + `reports/e3_07_full_run_complete.md`

**Interfaces:**
- Consumes: release `e3-full-ledger` 的 `shard_000.csv..shard_063.csv`（字段见 `tests/run_e3_07_matrix.py:preregister`）
- Produces: `merge_final_ledger.merge(shard_paths) -> dict`（keys: rows, task_ids_unique, status_counts, content_level_counts）

- [ ] Step 1: 写失败测试：64 个玩具 shard（各 3 行）合并后 rows=192、task_ids_unique=192、status_counts 正确；重复 task_id 必须抛 ValueError。
- [ ] Step 2: 运行确认失败（模块不存在）。
- [ ] Step 3: 实现 `merge(shard_paths)`：读全部 shard，校验 task_id 全局唯一、行数=430,080 断言、输出状态分布与内容级（85,024 网络）聚合。
- [ ] Step 4: 测试通过；用真实 64 shard 跑一次生成 `runs/e3_07/final_ledger.csv`。
- [ ] Step 5: 写 `reports/e3_07_full_run_complete.md`（波次数、总 wall、状态分布、逐轴分层、平台中断次数）。
- [ ] Step 6: commit。

### Task 2: E3-09 557 配置执行引擎（v_P 与 R_delta）

**Files:**
- Create: `implementations/probability/parallel_config_runner.py`
- Create: `tests/run_e3_09_units.py`
- Test: `tests/test_parallel_config_runner.py`

**Interfaces:**
- Consumes: `implementations/probability/lstpn_parallel.py`（`f0`, `f1`, `pe_exact`, `gamma_structural`, `gamma_exact`）；`runs/e3_09/frozen_567_configs.csv`；`frozen_135_specs.csv`
- Produces: `run_config(config_row, spec_rows) -> list[dict]`（每 spec 一行：v_P∈{0,1,⊥}、R_delta、阈值判定、证书 SHA）

- [ ] Step 1: 写失败测试：对 F1/W1/Q1 的 a4=3 配置，Pe=1/4、Gamma=1/2、135 个 spec 的 v_P 全部应为 1（阈值 γ≤Γ 时可靠）；ε=0、γ=1 边界单独断言。
- [ ] Step 2: 确认失败。
- [ ] Step 3: 实现密度族（F1 用 lstpn_parallel；F2 `f4(t)=2(5-t)/(5-a4)^2`；F3 两段阶梯）、权重（W2/W3 改变 q 后重算推前）、量化（Q2/Q3 在量化空间重算 Pe_quant 与覆盖）、阈值规则 v_P=1 iff R_delta ≥ γ（δ 来自 spec）、证书生成（SHA 绑定 config+spec+定义）。
- [ ] Step 4: 测试通过（F2/F3 至少各 1 个正例；Q2 至少 1 个反例显示 v_P=0/⊥）。
- [ ] Step 5: commit。

### Task 3: E3-09 76,545 判定单元在 Actions 上执行

**Files:**
- Create: `.github/workflows/e3-09-units.yml`
- Create: `tests/e3_09_shard.py`（按 shard 读写 release 台账，模式同 `run_e3_07_matrix.py:execute_shard_file`）
- Output: release `e3-09-units` + `runs/e3_09/units_results.csv`

- [ ] Step 1: 本地小样本（9 单元）跑通 shard 脚本，断言输出字段齐全。
- [ ] Step 2: 预注册 76,545 行拆 32 shard 上传 release `e3-09-units`（tarball，SHA 记录）。
- [ ] Step 3: workflow：cron `*/20` + 32 分片 + wall 240s + release 断点；guard 清零后 merge 并上传 artifact。
- [ ] Step 4: dispatch 验证首波（≥1 分片成功、台账前进）。
- [ ] Step 5: commit。

### Task 4: E3-08 L/H 签署落地与敏感性执行

**Files:**
- Modify: `tests/run_e3_08_sensitivity.py`（L/H 由 SPEC_BLOCKED 改为签署档位）
- Create: `.github/workflows/e3-08-sensitivity.yml`

**Interfaces:**
- Consumes: `reports/verifications/e3_08_lh_spec.md` §一（L∈{2,6,10}、H∈{19.5,33,39} 或按 j 分档备选）
- Produces: `runs/e3_08/sensitivity_results.csv`（含 VACUOUS_WINDOW 单列）

- [ ] Step 1: 写失败测试：真空配置（j=2 且 H=19.5）的窗口 R^c=∅ 时 result_status=VACUOUS_WINDOW 且不进 PASS 计数。
- [ ] Step 2: 实现档位注入与真空检测（先算 R^c 可达性再判）。
- [ ] Step 3: 测试通过；预注册 14,580 model-spec × 4 方法 = 58,320 行。
- [ ] Step 4: workflow（cron 波次，模式同 Task 3）。
- [ ] Step 5: commit。

### Task 5: E3-06 基线 B2/B3/B4 执行

**Files:**
- Create: `tests/run_e3_06_baselines.py`
- Create: `reports/e3_06/b2_tina_comparison.csv`（200 配置共同可比集）
- Create: `reports/e3_06/b3_prism_comparison.csv`（10 个 CTMC 对照）
- Create: `reports/e3_06/b4_sirio_smoke.csv`
- Test: `tests/test_baseline_comparison.py`

- [ ] Step 1: 写失败测试：TINA 共同可比集统计函数对玩具输入正确计数一致/不一致/缺席。
- [ ] Step 2: 实现对比脚本（TINA 侧用冻结账本匹配，不重跑历史）。
- [ ] Step 3: PRISM/Sirio 在 Actions 上跑（工具已在 release/acquire artifact）。
- [ ] Step 4: 测试通过；输出三张 CSV + review。
- [ ] Step 5: commit。

### Task 6: G2 新端到端回归集（10 类场景）

**Files:**
- Create: `tests/regression_e2e/`（10 个场景各一文件）
- Test: `tests/test_regression_e2e.py`

**Interfaces:** 覆盖 G2 裁定第 5 点 10 类：同次发射完成与故障、时钟重置、即时冲突、时限端点、未完成与完成区分、DBM 混合域拆分、观测单射（非路径 ID）、概率无效证据、可达循环、深度>9 合法路径；每类≥1 成立/不成立/未决/不适用。

- [ ] Step 1: 为每类写失败测试（断言 v_L 与证据结构）。
- [ ] Step 2: 补齐引擎缺口使测试通过（含深度>9 的抽样穷尽）。
- [ ] Step 3: 全量测试全绿；写 `reports/g2_regression_set.md`。
- [ ] Step 4: commit。

### Task 7: 四层独立验收与证据 ZIP

**Files:**
- Create: `reports/independent_acceptance.md`
- Modify: `tests/build_evidence_zip.py`（最终两档 ZIP + SHA256SUMS + 洁净解压复验）

- [ ] Step 1: 第 1 层字节：对新 ZIP 逐成员 SHA/CRC、清单核对、工具版本登记。
- [ ] Step 2: 第 2 层内容：继承证据 + 新运行证据重放与 6 类篡改负测。
- [ ] Step 3: 第 3 层数学：抽 20 个 verdict 独立复算（含概率单元）。
- [ ] Step 4: 第 4 层范围：分母、签署、未决对账。
- [ ] Step 5: 产出两档 ZIP + SHA256SUMS + 洁净解压记录；任一未过保持 `PARTIAL_NOT_CLOSED`。
- [ ] Step 6: commit。

### Task 8: 理论裁定项回收（Gamma 定义域、E3-08 档位、567 轴序）

**Files:**
- Create: `reports/e3_09_gamma_definition_request.md`、`reports/e3_08_lh_signoff_request.md`

- [ ] Step 1: 汇总 3 项待裁定（Gamma 定义域、L/H 档位、135 轴序确认）为一页申请。
- [ ] Step 2: 交付到 `~/Desktop/R6_E3_签署申请/05_补充裁定.md`。
- [ ] Step 3: 裁定回来后在 `decision_trace.csv` 追加 D13-D15 并更新对应实现。

### Task 9: 周维护与台账卫生

- [ ] Step 1: 每周一执行 `reports/file_cleanup_log.md` 增量清理 + 任务板归档 + schedule 检查。
- [ ] Step 2: 全量测试回归。
