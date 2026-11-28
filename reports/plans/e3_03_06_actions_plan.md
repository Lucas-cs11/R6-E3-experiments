# E3-03/04/06 GitHub Actions 工作流规划

状态：`PLANNED_NOT_EXECUTED`。本文只规划 YAML、运行矩阵和证据目录，不创建工作流文件，不触发 GitHub Actions，不启动本地实验。预算均为启动前的资源配置估算，不是既有运行的实测结果。

依据为 `R6_E3_v3_E2全部未闭合任务逐项整改_实验Agent执行指令.md` 第 84–139 行，以及冻结 E2 的 `baselines/baseline_registry.csv` 18 项登记。E2 的 18 项目前均为 `NOT_AVAILABLE / UNASSESSED / NONE_IN_WORKSPACE`，规划不会把这些状态改写成已取得、已适配或已运行。

## 1. 三条工作流和共同启动条件

| 工作流规划名 | 覆盖目标 | 运行分母 | 启动状态 |
|---|---|---:|---|
| `e3-03-r601-r613-integration.yml` | 旧 R4 P0/P1 缺陷复现与修复；R6-01—13 真实 PN/LSTPN 集成 | 1 个旧缺陷包 + 13 个组件包，再做一次集成门禁 | 待代码、模型和变异包就绪 |
| `e3-04-unified-engine.yml` | 统一诊断引擎、四条真实计算路径、52 模型身份与 208 次调用 | 16 微型 + 36 生成模型，每模型 4 方法，共 208 次 | 待 E3-03 组件回归和统一引擎就绪 |
| `e3-06-classic-baselines.yml` | B1 内部同题对照、B2/B3 外部经典基线、B4 概率基线登记与共同投影 | 18 项登记逐项审计；可执行项按共同域另算 | 预检可规划；获取和执行需分别授权 |

三条工作流都只配置 `workflow_dispatch`，不配置 `push`、`pull_request` 或定时触发。默认输入为 `mode=preflight`、`allow_external_acquisition=false`、`allow_execution=false`。正式运行要求同时提供冻结 ZIP SHA、E3 代码提交 SHA、模型包 SHA 和运行负责人；`allow_execution=true` 只解除内部实验执行，不替代外部下载、许可证或主理论签署。

共同预检在 `ubuntu-22.04` 上完成以下事项：

1. 在 `baseline_readonly/inputs/` 执行 `sha256sum -c SHA256SUMS.release`。完整工作区 ZIP 的固定 SHA-256 为 `bb72a68af34c852213e96588b4e29ecc602b0de428d406bbd30e8300a8656715`，ZIP 内根目录为 `R6_E2/`。
2. 只读解包到 `${{ runner.temp }}/frozen_e2/`，记录解包文件清单和逐文件 SHA。E3 新输出写入独立 `${{ runner.temp }}/e3_evidence/`，不回写 ZIP 或 `baseline_readonly/e2/`。
3. 检查 Python、LP/SMT 求解器、PN/LSTPN 引擎的版本和可执行文件 SHA。缺少模型、适配器或许可证时返回 `NOT_READY`，不以空矩阵产生 PASS。
4. 先运行 1 个微型模型的冒烟任务，校准内存和耗时，再开放矩阵。预检、冒烟和正式矩阵分别上传日志，防止用冒烟结果代替正式分母。
5. 每个 artifact 都带 `manifest.json`、`SHA256SUMS`、原始 stdout/stderr、退出码、墙钟、CPU 时间、峰值内存、输入 SHA 和运行环境。预填 verdict、预填 wall time、无原始日志的 PASS 均不进入汇总。

下文出现的 `tests/run_e3_03_integration.py`、`tests/run_e3_04_unified.py`、`tests/run_e3_06_baselines.py`、`tests/verify_e3_03_06.py` 和 `models/e3_*` 都是规划新增入口，启动前需实际落盘并审查；当前目录没有这些文件。现有 `tests/accept_e3.py` 只验收两个继承 P0 证据对象，可继续作为回归入口，不能替代 G2 集成或 G3 基线验收。

## 2. E3-03：13 项组件必须进入真实网络集成

### 2.1 输入

| 类型 | 路径 | 用途 |
|---|---|---|
| 冻结 ZIP | `baseline_readonly/inputs/R6_E2_complete_workspace.zip` | 唯一继承输入包，预检核对固定 SHA |
| ZIP 内主体参考 | `R6_E2/implementations/subject/r601.py` 至 `r613.py`，含 `r608_module.py` 与 `ap41_r6.py` | 只用于历史差异分析，不直接当作 E3 已通过实现 |
| ZIP 内独立参考 | `R6_E2/oracles/independent/r601_reference.py` 至 `r613_reference.py` | 检查历史参考能力边界；E3 仍需独立实现和变异 |
| ZIP 内真实模型样例 | `R6_E2/models/r603/endpoint.json`、`five_outcomes.json`、`budget_frontier.json` | 继承模型格式和边界样例，不能代替 13 项完整模型包 |
| ZIP 内历史变异记录 | `R6_E2/runs/g1_r601/` 至 `R6_E2/runs/g1_r613/` | 旧结果与旧错误复现线索，不作为新运行日志 |
| 合同与范围 | `R6_E2/contracts/experiment_scope_frozen.json`、`R6_E2/chapter6/protocol.json` | 记录历史 G2 仅为局部组件状态 |
| 规划新增 E3 模型 | `models/e3_integration/<component_id>/model.json` | 真实库所、变迁、弧、标识、时钟区间、标签、故障和首次完成定义 |
| 规划新增执行器 | `tests/run_e3_03_integration.py` | 执行原例、反例、网络 trace、主体/独立参考和源码变异 |

### 2.2 运行矩阵

矩阵 `component` 取 `LEGACY_R4, R6-01, …, R6-13`，共 14 个组件作业，`max-parallel: 4`。每个组件作业内部必须跑完全部正反例，不允许把单个 `original_case` 当作组件完成。

| component | 作业必须覆盖的真实语义和反例 |
|---|---|
| `LEGACY_R4` | 复现 `x` 消耗并重建 `py` 时中间标识的 Y 失能再使能和时钟重置；额外即时根按全部 `pre(t)≤M` 及真实权重竞争；M11 必须改变概率积分状态。保留旧错误退出码和修复后对照 |
| `R6-01` | 前/中/后使能、持续使能、时钟新实例、强时间紧迫、即时优先和中间失能重启 |
| `R6-02` | 同次故障与首次完成、零时差、窗口端点和外部完成条件 |
| `R6-03` | 合法完成、非完成终止、死锁、时域截断、预算前沿五类及质量守恒 |
| `R6-04` | 故障后首次完成、`B_c`/`H_A` 一致性、右端点即时闭合后截断 |
| `R6-05` | 逻辑混合 DBM/状态类精确差分分割，同类中的违例与非违例分别保留 |
| `R6-06` | 无损历史、观测词和完成时长一致、正常/故障见证与独立耦合 LP |
| `R6-07` | 全部即时根竞争、历史依赖联合密度、时钟生命周期和完整质量树 |
| `R6-08` | 算法 4.1 区间/阈值/先验/未决优先级、原始证书绑定和联合可行域 |
| `R6-09` | 有限有理分段密度、有限深度/时域、多面体精确积分和不可计算子类的 `UNSUPPORTED` |
| `R6-10` | 不同 `omega_c` 值上的 `omega_c→Y` 单射、外部完成、正常/故障域对齐；相同观测的多路径不得误判 |
| `R6-11` | 零测度支持相交、原子质量、观测粗化下 Bayes 风险与覆盖率差异 |
| `R6-12` | 第 6 章逻辑 52×4 的历史身份、方法见证和扩展全域合法范围 |
| `R6-13` | 32 工况、48 候选、5000 来源与概率数据的归属、区间和逐行对账 |

每个组件产物必须包含合同指定的 `original_case`、`new_counterexample`、`actual_network_trace`、`subject_output`、`oracle_output`、`invariant_verdict`、`mutation_patch`、`mutation_exit_code`、`coverage_limitations`。`v=0` 绑定可复放反例，`v=1` 绑定已定义域内穷尽证据或数学证书；预算前沿保持未决。

组件全部通过后，单独启动 `integration` 作业，在真实 PN/LSTPN 上串联模型解析、状态类/DBM、观测与首次完成、故障同步、LP 和诊断。该作业只可申请 `G2_INTEGRATED_PASS`，不能由 14 个组件的局部 PASS 自动推断。

### 2.3 Artifact 命名和内容

- `e3-03-preflight-${run_id}`：ZIP、工具、模型包和独立参考完整性检查。
- `e3-03-legacy-r4-${run_id}`：旧错误复现、修复补丁、M11 积分状态差异和回归日志。
- `e3-03-component-r6-01-${run_id}` 至 `e3-03-component-r6-13-${run_id}`：每个组件的完整九字段证据包。
- `e3-03-component-rollup-${run_id}`：13 项覆盖矩阵、缺失项、变异汇总和 SHA 清单。
- `e3-03-g2-integration-${run_id}`：真实网络集成 trace、主体/参考输出、资源数据及 `g2_integration_request.json`。

原始日志保留 14 天，汇总账本和签署申请保留 90 天。超过 2 GB 时优先压缩状态类转储，身份清单、反例、变异和 verdict 证据不删减。

### 2.4 本地核验入口

```bash
python3 -B tests/run_e3_03_integration.py \
  --frozen-zip baseline_readonly/inputs/R6_E2_complete_workspace.zip \
  --component R6-01 --mode all --output runs/e3_03/component_r601

python3 -B tests/verify_e3_03_06.py \
  --suite E3-03 --evidence-root runs/e3_03 --require-integration

python3 -B tests/accept_e3.py --evidence-root .
```

第一条是规划新增的真实执行入口，第二条是规划新增的覆盖与证据门禁，第三条只检查既有回归范围。

### 2.5 预算与授权

预检 10 分钟；14 个组件作业每个 `timeout-minutes: 75`，预计 30–60 分钟；集成作业上限 120 分钟。按 4 路并发估算 8–14 CPU 小时、3–5 小时墙钟，artifact 上限 2 GB。任一组件超过预算只记 `TIMEOUT/UNRESOLVED`，不缩短反例集。

启动真实执行前需要用户授权 GitHub Actions 分钟和 artifact 存储。`G2_INTEGRATED_PASS` 及其理论能力声明需要主理论助手审签；修改故障、完成、观测或时间语义以适配旧模型时，也需先签署语义变更。

## 3. E3-04：统一引擎用 52×4 调用验证四条路径

### 3.1 输入

| 类型 | 路径 | 用途 |
|---|---|---|
| 冻结 ZIP | 同 §2.1 的完整工作区 ZIP | 只读继承模型映射、历史运行和工具信息 |
| ZIP 内模型映射 | `R6_E2/chapter6/physical_to_tpn_mapping.csv`、`R6_E2/chapter6/protocol.json` | 核对物理事件、故障、观测和首次完成的语义来源 |
| ZIP 内逻辑来源 | `R6_E2/scope/逻辑逐行_完整精度.csv`、`R6_E2/scope/comparison_candidates_48.csv` | R6-12/13 和历史逻辑域对账，不直接充当统一 PN 模型 |
| ZIP 内历史 52 模型证据 | `R6_E2/results/tina_52_models.csv`、`R6_E2/runs/tina_52.stdout.json`、`R6_E2/runs/tina_52.stderr.log` | 核对历史原始字节是否可用；TINA 结果仅限其原生问题 |
| ZIP 内已有 PN 样例 | `R6_E2/models/r603/*.json` | 解析器兼容与最小集成测试 |
| 规划新增统一模型包 | `models/e3_unified/inherited16/`、`models/e3_unified/generated36/` | 完整 TPN 接口、时钟生命周期、分布版本和逐模型三层 SHA |
| 规划新增引擎与执行器 | `implementations/subject/unified_engine.py`、`tests/run_e3_04_unified.py` | 四方法真实调用、资源测量和证据输出 |

36 个生成模型的历史原始字节若缺失，必须标为 `RECONSTRUCTED` 并记录重建来源，不能写成原始模型恢复。16+36 的模型包在预检时先冻结，禁止根据运行速度、成功状态或 UNSUPPORTED 结果删行。

### 3.2 运行矩阵

| job | matrix | 调用数 | 必查内容 |
|---|---|---:|---|
| `identity` | `model_group=inherited16,generated36` | 52 次身份检查 | 原始字节可用性、重建身份、完整字段、适用性理由、三层 SHA |
| `engine` | `model_group=inherited16,generated36` × `method=MAIN,FULL_HISTORY,NO_SYNC,NO_ENVELOPE` | 2×4 个作业，共 208 次调用 | 同一输入、L/H、首次完成、故障、观测、时间语义和预算 |
| `oracle` | `model_group=inherited16,generated36`，仅限小型完备域 | 小型模型逐路径枚举 + 有理 LP + 独立 SMT/LP | 参考能力边界、搜索完备性、条件求积和预算限制 |
| `ablation_audit` | 4 方法 × 固定代表模型 | 4 组调用序列 | 消融作用点、调用栈、状态类/弧/同步对数、LP/积分次数确实不同 |
| `rollup` | 全矩阵 | 208 条记录核对 | 与历史状态差异、失败/超时、未决和原始证据绑定 |

`MAIN` 是论文完整法；`FULL_HISTORY` 保留无剪枝完整历史并调用独立耦合 LP；`NO_SYNC` 只去掉同步筛选；`NO_ENVELOPE` 只去掉时间包围筛选。共享模型解析可以接受，四个标签共用同一计算函数再改名的作业直接判 FAIL。

每次调用保存墙钟、CPU、峰值内存、状态类数、弧数、同步对数、LP/积分次数、超时和内存限制。预算耗尽、无限状态或超出独立参考能力时分别保留 `TIMEOUT`、`UNSUPPORTED` 或未决，不默认穷尽或返回 `v=1`。

### 3.3 Artifact 命名

- `e3-04-identity-${model_group}-${run_id}`：52 模型身份、原始/重建状态和输入 SHA。
- `e3-04-engine-${model_group}-${method}-${run_id}`：8 个方法分片，包含逐模型调用、trace、资源指标和退出码。
- `e3-04-oracle-${model_group}-${run_id}`：独立枚举、SMT/LP 证据及适用边界。
- `e3-04-ablation-audit-${run_id}`：四方法实际调用序列和消融作用点。
- `e3-04-208-rollup-${run_id}`：208 条总账、历史差异和 G2/G3 可复用输入。

原始引擎分片保留 14 天，208 条总账和身份清单保留 90 天，artifact 总量上限 4 GB。

### 3.4 本地核验入口

```bash
python3 -B tests/run_e3_04_unified.py \
  --model-root models/e3_unified --model-group inherited16 \
  --methods MAIN,FULL_HISTORY,NO_SYNC,NO_ENVELOPE \
  --output runs/e3_04/inherited16

python3 -B tests/verify_e3_03_06.py \
  --suite E3-04 --evidence-root runs/e3_04 \
  --expect-models 52 --expect-calls 208 --require-distinct-ablations
```

核验器需逐行检查 52 个模型身份和 208 个调用 ID，不能只检查文件是否存在。

### 3.5 预算与授权

身份作业上限 30 分钟；8 个引擎作业每个 `timeout-minutes: 180`，预计 60–150 分钟；独立参考和汇总各上限 120 分钟。按 `max-parallel: 2` 控制内存，估算 12–24 CPU 小时、6–12 小时墙钟。

52 模型集成不需要宣称 E3-05 全量主域已完成。任何扩展到 `frozen_full_domain.json` 的矩阵都必须等主理论助手签署正式研究域和 `domain_index.csv`，用户另行批准对应 Actions 预算；本规划的 208 次调用不能外推为 430,080 次全量调用。

## 4. E3-06：18 项登记先过同题审查，再进入对应矩阵

### 4.1 输入和预检

冻结 ZIP 内的 `R6_E2/baselines/baseline_registry.csv`、`semantic_equivalence_matrix.csv`、`reference_traceability.md`、`downloads/download.log` 是 18 项登记的起点。`R6_E2/baselines/downloads/tina-4.0.0-arm64-darwin.dmg` 只是 macOS ARM64 历史文件，不能当作 Linux Actions 可执行程序。共同模型语义来自 `R6_E2/chapter6/physical_to_tpn_mapping.csv` 和 `protocol.json`，四方法输入来自验收后的 E3-04 artifact。

`acquisition` 作业逐项检查来源标识、版本、许可证、artifact SHA、获取尝试和可执行性。默认不联网获取；用户显式开启 `allow_external_acquisition` 后，也只下载白名单内项目，许可证文本和获取日志随 artifact 保存。自行实现的文献算法标 `INDEPENDENT_ADAPTATION`，不冒称原作者程序。

### 4.2 18 项登记矩阵

表中的层级是规划分工，最终 `compatibility_class` 仍由逐项 `assumption_check` 决定。

| ID | 层级 | 规划比较内容 | 执行前置条件 |
|---|---|---|---|
| L-01 | B3 | Diagnoser，仅在无时间、共有事件观测投影比较 | 获取实现和许可证；主理论签署共同投影 |
| L-02 | B3 | Verifier Net，同上 | 同上 |
| L-03 | B3 | MBRG/BRD，同上 | 同上 |
| L-04 | B2 | Basile/Cabasino/Seatzu MSCG+LP，审查 K-诊断性与首次完成差异 | 获取或独立适配；主理论签署同题子域 |
| L-05 | B2 | TWINA/Product TPN，审核时间语言同步和完成定义 | 获取版本与许可证；签署适配语义 |
| L-06 | B2 | TINA state-class/monitor net，构造可复验任务完成查询 | 获取匹配平台的已验证工具；签署查询适配 |
| L-07 | B1 | FULL_HISTORY，无剪枝完整历史 + 独立耦合 LP | E3-04 四方法证据可用；同题账本签署 |
| L-08 | B1 | MAIN 完整法 | 同上 |
| L-09 | B1 | NO_SYNC 消融 | 同上 |
| L-10 | B1 | NO_ENVELOPE 消融 | 同上 |
| P-01 | B4 | 有限有理事件树 + 精确多面体积分，作为首要数学 oracle | 独立实现审查和共同概率查询签署 |
| P-02 | B4 | 随机状态类密度，对照匹配概率量 | 获取/独立适配、版本与分布语义核查 |
| P-03 | B4 | ORIS/Sirio 概率量对照 | 获取软件、许可证和匹配模型适配 |
| P-04 | B4 | 带标签随机 PN 故障模式可诊断性 | 审核原生问题，先证同题或降为共同投影 |
| P-05 | B4 | PRISM，仅合法 CTMC/DTMC 特例 | 证明模型归约和时间/概率语义；其余只作投影 |
| P-06 | B4 | 事件驱动 MC/SMC，近似精度和效率对照 | 固定种子、置信口径和样本预算；不作严格证书 |
| P-07 | B4 | 故意语义故障消融，检查错误语义能否被检出 | 内部变异包和独立参考审查，不冒充外部基线 |
| P-08 | B4 | 逻辑回归、随机森林、HGBT，仅工业数据预测语境 | 明确数据任务差异，默认 `CONTEXT_ONLY` |

### 4.3 执行矩阵

| stage | matrix | 预计调用 | 进入条件 |
|---|---|---:|---|
| `registry_audit` | 18 个 baseline_id | 18 项审计 | 可预检；不修改冻结登记 |
| `b1_same_task` | `method=MAIN,FULL_HISTORY,NO_SYNC,NO_ENVELOPE` × `common_domain` | 继承 52 模型时为 208 次 | B1 同题账本签署；可复用 SHA 一致的 E3-04 结果 |
| `b2_timed_pn` | `baseline=L-04,L-05,L-06` × `common_domain` | 每基线按签署共同域展开 | 工具/许可证/适配器和同题证明齐全 |
| `b3_untimed_des` | `baseline=L-01,L-02,L-03` × `shared_projection` | 每基线按无时间共同投影展开 | 仅需投影时也须签署投影规则 |
| `b4_probability` | `baseline=P-01,…,P-08` × `probability_query` | 按概率查询矩阵，不用 MC 样本数冒充模型数 | 概率、时间、观测和故障语义逐项核对 |
| `ledger_rollup` | 18 个 baseline_id | 18 行总账 + 运行明细 | 汇总成功、缺口和不适用原因，不强制凑齐可运行数 |

B1 的 MAIN 对 FULL_HISTORY 是正确性/效率对照，NO_SYNC/NO_ENVELOPE 是机制消融。B2 只在合法同题子域报告性能差异。B3 原生研究问题不同就保留文献或共同投影参照。B4 的 MC/SMC 只给近似精度与效率，PRISM 只进入合法 CTMC/DTMC 特例，机器学习结果不进入 PN 严格证书比较。

每个基线都写 `baseline_same_task_ledger.csv`，字段固定为：

```text
baseline_id,reference,original_task,source_url_or_identifier,license,version,
artifact_sha,acquisition_attempts,compatibility_class,assumption_check,
model_adapter,common_domain_definition,run_count,outcome_status,evidence_path
```

`compatibility_class` 只取 `EXACT_SAME_TASK / ADAPTED_SAME_TASK / SHARED_PROJECTION_ONLY / CONTEXT_ONLY / NOT_AVAILABLE / UNSUPPORTED`。获取失败保留尝试证据，原生规格不符记录 `CONTEXT_ONLY` 或 `SHARED_PROJECTION_ONLY`，不得从 `TINA-BOUNDED` 推导本文诊断更快。

### 4.4 Artifact 命名

- `e3-06-registry-audit-${baseline_id}-${run_id}`：18 项各自的来源、版本、许可证、获取尝试和适配检查。
- `e3-06-b1-${method}-${domain_sha}-${run_id}`：四方法同题运行或经核验复用的 E3-04 证据。
- `e3-06-b2-${baseline_id}-${domain_sha}-${run_id}`：B2 原始运行和共同域定义。
- `e3-06-b3-${baseline_id}-${projection_sha}-${run_id}`：B3 共同投影输入、输出和边界。
- `e3-06-b4-${baseline_id}-${query_sha}-${run_id}`：概率查询、种子/积分配置及原始输出。
- `e3-06-same-task-ledger-${run_id}`：18 行总账、逐项证据路径和未闭合原因。

原始运行 artifact 保留 14 天，总账和许可证/来源证据保留 90 天，总量上限 8 GB。

### 4.5 本地核验入口

```bash
python3 -B tests/run_e3_06_baselines.py \
  --registry baseline_readonly/e2/baselines/baseline_registry.csv \
  --baseline L-04 --mode preflight --output runs/e3_06/L-04

python3 -B tests/run_e3_06_baselines.py \
  --tier B1 --methods MAIN,FULL_HISTORY,NO_SYNC,NO_ENVELOPE \
  --common-domain models/e3_common_domain/frozen_domain.json \
  --output runs/e3_06/B1

python3 -B tests/verify_e3_03_06.py \
  --suite E3-06 --evidence-root runs/e3_06 \
  --expect-registry-rows 18 --require-same-task-ledger
```

`preflight` 只核验获取和适配证据。执行模式还必须提供共同域 SHA、工具 SHA、许可证路径和实际运行记录。

### 4.6 预算与授权

B1 复用 SHA 一致的 E3-04 结果时只增加汇总开销；独立重跑仍需 12–24 CPU 小时。B2 每基线作业 `timeout-minutes: 240`，合计估算 9–18 CPU 小时；B3 每项上限 90 分钟，合计 3–6 CPU 小时；B4 每项上限 180 分钟，合计 8–20 CPU 小时。不含 B1 重跑时约 20–44 CPU 小时，外部获取、构建和人工许可证审查时间另计。

以下项目需要用户逐项授权：外部源码/二进制获取、许可证接受、需要账号或密钥的下载、GitHub Actions 计算与存储预算、外部软件在 runner 上的安装执行。B1/B2 的同题定义、B3 的共同投影、B4 的概率查询及 `INDEPENDENT_ADAPTATION` 声明需要主理论助手签署。未完成这些步骤的项目保留原状态，不进入性能排名。

## 5. 签署门、总预算和验收边界

| 项目 | 所需签署或授权 | 签署前允许的工作 |
|---|---|---|
| E3-03 正式矩阵 | 用户授权 Actions 计算和存储 | 本地代码审查、输入清单、冒烟规划 |
| `G2_INTEGRATED_PASS` | 主理论助手审签真实网络集成证据 | 输出签署申请，不提前改门禁状态 |
| E3-04 全量主域扩展 | 主理论签署 `frozen_full_domain.json` 和 `domain_index.csv`；用户批准新增预算 | 仅做 52 模型集成和身份审计 |
| 外部基线获取与安装 | 用户逐项授权来源、版本、许可证和 runner 安装 | 记录公开标识与当前缺口，不执行下载 |
| B1/B2 同题比较 | 主理论签署故障、首次完成、观测、L/H、时间语义和预算完全一致的定义 | 准备适配器和反例，不发布加速比 |
| B3/B4 投影或概率比较 | 主理论签署共同投影/查询；外部工具另需用户授权 | 文献审计和输入准备 |
| 最终 G3 状态变更 | 主理论助手依据 18 行总账和实际运行证据审签 | 保留 `REGISTRY_ONLY` 或未闭合项 |

三条工作流的新增计算预算合计约 40–82 CPU 小时，B1 不复用 E3-04 结果时另加 12–24 CPU 小时。该估算不包含正式全量主域、外部获取的人工等待和超额重试。每次 `workflow_dispatch` 设置总预算上限，达到上限后停止新矩阵分片并保留未执行 ID。

最终核验顺序固定为：E3-03 组件与旧缺陷证据 → E3-04 的 52 模型身份和 208 次真实调用 → B1 同题复核 → B2/B3/B4 按授权矩阵执行 → `tests/verify_e3_03_06.py` 全量账本核验 → 主理论签署申请。任何阶段缺失原始日志、独立参考、共同域证明或许可证，都保留具体缺口，不以工作流绿色状态替代理论验收。
