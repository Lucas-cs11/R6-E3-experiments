# R6-E2 实验资料交付说明

**交付状态：`PARTIAL_VALIDATED_NOT_CLOSED`。** 本交付汇集已取得的实验材料、失败产物、冻结输入和复核记录；未执行的合同条目不作为已交付实验结果。

## 从哪里开始

| 内容 | 包内入口 |
|---|---|
| 执行合同、R6-E1 审计、冻结 TeX | `baseline_readonly/`，以 `input_inventory.json` 核对冻结资产 |
| 八轴总体与合法性 | `scope/generator_candidate_universe_full.csv`、`scope/model_validity_rules.json`、`scope/protocol_lineage.md` |
| 生成、结构与哈希 | `results/all_population_results.csv`、`results/model_hash_replay.csv` |
| PyScrew 来源、划分及比较语义 | `scope/pyscrew_raw_manifest.csv`、`scope/comparison_candidates_48.csv`、`chapter6/split_plan.csv`、`chapter6/PYScrew_DATASET_PROVENANCE.md` |
| G1/G2 模块、独立参考、失败样本与变异 | `implementations/subject/`、`oracles/independent/`、`runs/g1_r608/`、`runs/g2_*` |
| 基线与历史对照 | `baselines/`、`results/baseline_adapter_52.csv`、`scope/逻辑逐行_完整精度.csv` |
| TINA 当前证据 | `runs/tina_cloud_45192651608/terminal_replay.json`、同目录 `merged_candidate_verdicts.csv`；原始输出在两个严格运行目录（45127189704、45192651608）的 `download/` |
| 修正后的连续概率结果 | `results/probability_a4_21points.csv`、`runs/g4_probability_scope_audit/audit.json`、`runs/g4_probability_estimand_legacy/` |
| 分层状态 | 本文件与 `results/delivery_gate_status.csv` |

## 当前有效结论和缺口

- **G0 部分通过。** 143,360 个唯一候选，107,520 个合法格实际生成并通过结构检查，35,840 个按冻结规则排除。5,000 个原始 JSON 已在有数据的本地环境匹配原文哈希，计 2,500 个工件、50 个来源组，包含 693 条非 OK。48 个比较候选仅限经验分类，缺可核验的原模型故障发射及首次完成映射；研究域裁定与更强的定时语义检查仍待完成。
- **G1/G2 局部通过。** G1 20 个用例和 5 个变异；G2 13 个组件、68 个用例、36 个变异。仍缺多类别的完整联合约束、原始证书绑定与集成引擎的合同必测域。
- **G3 部分完成。** 已登记 18 项；历史 52 格中 36 格结构适配，16 个微型模型未接入本轮适配。TINA 仅验证无时间 P/T 投影，不是定时故障诊断同题基线，不纳入诊断加速比。
- **G4 未闭合。** TINA 两轮合并覆盖 107,520 个候选，104,052 个有界、3,468 个超时未决。逐条复核了原始输出；输入 PNML 哈希另作重放核对。八轴四实现诊断及 1,620 格逻辑敏感性诊断仍待执行，结构生成不计求解。等先验、连续观测的 21 点已精确复算；合同 567 模型、135 数值规格、76,545 个潜在判定组合尚未验收。PyScrew 全源新评价、历史 32 组独立复验及 1,413 / 1,421 行交集复原未完成。
- **G5 未执行。** 当前 ZIP 的 CRC、逐文件 SHA 和洁净解压回放是交付自检，不是独立终验；本轮不宣称 E2 或整篇论文闭合。

## 历史材料的读取边界

- `results/tina_all_merged*` 和 `results/tina_github/` 含旧版失败解析，不能用于无界结论；`results/tina_52_models.csv`、`results/tina_54_cells.csv`、`results/tina_1620_diagnosis.csv` 等旧布尔输出亦未通过严格判定重放。严格运行中被截断的批次和所有超时产物保留审计。
- 旧 `results/probability_567_*`、旧 Gamma 推导及配套报告属于已撤回或非合同口径证据，不能当成合同矩阵。此前的总账、汇报和阶段摘要保留原貌以便追溯；以本说明、分层状态和上述当前证据入口为准。

## 解压后验证

在解压所得 `R6_E2` 目录执行以下命令。完整包清单名为 `SHA256SUMS`，便携包为 `SHA256SUMS.portable`。

```sh
shasum -a 256 -c SHA256SUMS       # 便携包替换为 SHA256SUMS.portable
python3 -B tests/final_verify_r6_e2.py
python3 -B tests/final_verify_r6_e2.py --raw-root /path/to/pyscrew
```

`--raw-root` 指向带 `raw_json/<physical_class>/<file_name>` 的 PyScrew 目录。原始 5,000 个 JSON 不入两个资料包；数据版本和来源校验见包内溯源文件。未提供原始目录的回放只审核来源清单。验收器 `PASS` 的范围仅为 `EVIDENCE_INTEGRITY_ONLY_NOT_PHASE_GATE`。

完整包保留冻结的两个 R6-E1 ZIP；便携包仅省略这两个嵌套 ZIP。两包均省略 Git 对象、Python 字节码缓存和旧的 E2 交付 ZIP；保留 GitHub 工作流、云端求解证据、旧版结果和失败记录。外层发布校验和与解压验证记录随包分发。
