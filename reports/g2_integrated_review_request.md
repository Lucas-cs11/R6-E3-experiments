# G2_INTEGRATED_PASS 审签申请（主理论助手）

状态：`PENDING_THEORY_REVIEW`。本申请只汇总已有证据与边界，不预设通过；签署前 E3-03/E3-04 保持组件级/小模型级结论。

## 1. 申请范围

R6-01..R6-13 组件 + E3-04 统一引擎（模型接口 + 四计算路径）在**继承模型集与明确预算**内的集成证据。不申请：一般 LSTPN 全称结论、连续调度域、52×4 中 16 微模型（原始字节缺失）、任何性能优势声明、全量主域结论（另见 E3-05 域签署申请）。

## 2. 证据清单

| 证据 | 位置 | 内容 |
|---|---|---|
| 组件实现与测试 | `implementations/subject/r6_components{,_b,_c,_d,_e,_f}.py`、`tests/test_r6_components*.py` | 13 组件：主体/独立参考双路径、正反例、特异性变异、自计算验收记录 |
| 组件独立总评审 | 会话记录（independent-auditor） | R6-01..04 限定 PASS 后修补（R604 特异性变异、验收记录自计算）；R6-05..11 限定 PASS（独立性/变异/边界确认）；R6-12/13 NOT_PRESENT 后补真正组件 |
| 引擎接口 | `implementations/subject/engine_interface.py` | 逐字段适用性理由；初始完成模型统一拒绝（评审后补） |
| 四路径引擎 | `implementations/subject/engine_paths.py`、`oracles/independent/engine_paths_reference.py` | 四方法真实消融（path_stats 差异实测）、独立参考（枚举+solve_square LP+差分约束，深度≤9 明示） |
| 52×4 矩阵 | Actions run 45555991744、`runs/actions/matrix_45555991744/` | 144 调用全 EXHAUSTED verdict=1；64 微模型 NOT_RUNNABLE_PROVENANCE；144 证书 SHA 合法；资源实测互异 |
| B1 对照 | `reports/e3_06/b1_same_task_analysis.json` | 四方法 36/36 verdict 一致；MAIN 扩展数中位 10 vs FULL_HISTORY 14；墙钟差异在噪声级不作性能声明 |
| 测试基线 | 90 项单元/集成测试全绿（Actions CI 随推送通过） | 含全部变异检出 |

## 3. 明示边界（签署即接受这些限制写入结论）

1. 引擎包络筛选用作分组统计与等价诊断，非状态空间剪枝证明；`state_classes` 为派生计数。
2. 独立参考与主体共用 `check_applicability`（接口级共享，非判定逻辑共享）；参考完成深度≤9。
3. 循环检测对任何 pre==post 自循环保守触发（含理论不可达者），为保守未决非精确证明。
4. 资源为 wall/CPU/tracemalloc 实测（Python 分配峰值），单次计时无对照统计；不声称加速/内存优势。
5. 36 生成点全部 verdict=1 是该小故障点集的性质，不外推一般可诊断性；16 微模型不参与任何分母。
6. R6-11 零测度例仅对称先验；R6-10 单射布尔字段恒真（实际拒绝依赖 by_word 检查）；R6-09 支持域为 ≤2 次有理分段密度（高次为实现限制）。

## 4. 请求裁决

1. 是否授予 `G2_INTEGRATED_PASS`（限定于第 1、3 节范围）？
2. 若需补充证据（指定模型、指定变异、指定边界用例），请列出最小集合。
3. 与 E3-05 域签署的依赖关系：G2 是否以域签署为前置，或可在继承模型集上先行？

## 5. 签署栏

- 主理论助手：____________  日期：________  结论：G2_INTEGRATED_PASS / G2_LIMITED（附条件） / G2_REJECTED（附理由）
