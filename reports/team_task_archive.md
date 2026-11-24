# 团队任务板归档（2026-11-24 大扫除）

任务板只保留活动任务；已完成/过期任务归档于此并从头板删除。历史交付物本体在各自工作区（R4_V1_6、R4_V1_7、R6_E1、R6_E3），此处仅留索引。

## 上一阶段（R4_V1_6 / R4_V1_7，全部 completed，删除）

| 任务 | 主题 | 交付位置 |
|---|---|---|
| task-1 | AP41-R5-v1 理论合同提取 | R4_V1_6/contract_extraction.md |
| task-2 | V1.6 PN 模式与 B01–B06 模型冻结 | R4_V1_6/models、reports/model_semantics.md |
| task-3 | V1.6 独立参考判定与网络穷举 | R4_V1_6/oracle/ |
| task-4 | V1.5 历史回归与方程索引 | R4_V1_6/results、evidence/ |
| task-5 | V1.6 生产实验套件 | R4_V1_6/src、tests、results |
| task-6 | V1.6 独立审计 | R4_V1_6/reports/independent_review.md |
| task-7 | AP41 v1→v2 合同差异与 V1.7 preflight | R4_V1_7/contract_diff_v1_v2.md |
| task-8 | V1.6 五类定义域缺陷复现 | R4_V1_7/evidence/pre_fix_failures/ |

## R6_E1 阶段（E3 合同取代，删除）

| 任务 | 状态 | 处置 |
|---|---|---|
| task-9 | pending（未启动） | 被 E3-05 域审计取代，标记 OBSOLETE_SUPERSEDED_BY_E3 |
| task-10 | completed（PyScrew 5000 总体冻结） | 交付在 R6_E1/chapter6/，归档保留 |
| task-11 | in_progress（边界映射） | 拥有者长期不活跃，E1 阶段结束，标记 ABANDONED_SUPERSEDED_BY_E3 |
| task-12 | in_progress（S-1 独立审计） | 同上 |

## R6_E3 阶段已完成（删除，证据在工作区内）

| 任务 | 主题 | 证据 |
|---|---|---|
| task-13 | TINA 原始分片独立重放 | oracles/independent/tina_raw_replay.py、runs/math_p0/tina_raw_replay/ |
| task-14 | R604 输入重建与语义重放 | implementations/subject/r604_replay.py |
| task-15 | Actions 探针 run 45413821437 跟踪 | runs/actions/merged_probe_45413821437/ |
| task-16 | E3-03/04/06 工作流规划 | reports/e3_03_06_actions_plan.md |
| task-17 | Actions 探针 run 45417405202 跟踪 | runs/actions/merged_probe_45417405202/ |

## 保留

- task-18（in_progress，oracle-v16）：共享前缀约束存储。

## 维护规则

- 任务完成并归档后即从头板删除；头板只留在途与待办。
- 子 Agent 长期不活跃（上一阶段遗留）不复用，按需新派。
- 每周清理（schedule-15f8b045）同步检查任务板与 Agent 名册。
