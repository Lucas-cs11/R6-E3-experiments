# R6-E3 v3：R6-E2 全部未闭合事项逐项整改、全量实验、经典 PN 基线与独立联合复验——实验 Agent 强制执行指令

版本：2026-11-24  
性质：**执行合同；尚未执行，不是已取得的实验结果。**  
唯一理论基准：`example_revised_theory_v2_theory_round6_candidate.tex`；SHA-256 `a4196145c95812ff19376a5985b6a6f2cf469d432c80836071cad1c8ac174c5a`。  
唯一当前工程输入：2026-11-24 再次提交的 `R6_E2_complete_workspace(1).zip`（SHA-256 `bb72a68af34c852213e96588b4e29ecc602b0de428d406bbd30e8300a8656715`）及 `R6_E2_portable_evidence(1).zip`（SHA-256 `93572bde0ec70e19ddc8296b6b5872981a2fec8726bc7c2a9f54e8db81b2fbec`）。  
任务依据：《R6_E2_再次交付_独立深度验收报告_20261124.md》、《R6_E3_v2_全量诊断与经典基线_数学P0整改_完整执行指令.md》、《R6_E2_独立深度验收报告_20261123.md》及独立反例记录 `r6e2_repeat_independent_probes.json`、`r6e2_repeat_tamper_probes.json`、`r6e2_repeat_generator_probe.json`、`r6e2_repeat_module_rerun.json`。此前 R6-E1 v2/v3 与 E3 旧版的**未冲突强制项继续有效**；若语义冲突，先记录冲突并交主理论助手裁定，不得自行采用宽松解释。

> **立即执行本合同，不要再提交一份仅有计划、预注册或 PASS 自报的 R6-E2 包。** 以 `R6_E3` 建立全新独立工作区，逐项修复、实际运行、保留原始证据，按下述阶段门禁进入下一步。对明确属于论文数学定义、定理或正式研究域的分歧，列出具体待裁定问题、两种方案及影响数量，交主理论助手决定；不要擅自修改论文、证明、TeX，也不得为取得 PASS 改写数学命题。无需再追查已确认不可追回的旧 Linux 核心源码。

---

## 一、硬性工作边界与总验收制度

1. **原件不可变。** 所有 R4、R6-E1、历次 R6-E2 压缩包、旧程序、旧结果、失败与撤回报告原样保存且只读；所有修复、新模型和新运行写入 `R6_E3/`。在 `input_inventory.json` 写入每份输入的来源、SHA-256、版本、封版日期、读取方式。不得覆盖历史失败证据或在旧目录上原地修复。
2. **实验 Agent 的唯一职责**：模型生成/结构与动态语义、算法与独立参考的工程实现、实验执行、数据处理、测试变异、环境与日志、可复验交付。论文数学分析、定理证明与正文/TeX 修改均由主理论助手承担；实验发现不合定义之处以反例和待裁定问题提交。
3. **不得把以下任何产物等同于诊断效果实验**：143,360 行候选登记、107,520 个结构生成、1,620 个结构敏感性模型、107,520 项 TINA 无时间 P/T 投影有界性、52×4 历史结果比对、21 点解析核算、68 个局部组件 PASS、5000 条来源哈希、ZIP 校验、567 个符号配置占位。
4. **主域先冻结，再运行；全部合法配置逐项保留。** 不得因为超时、算不出、基线不适用、重复 PN、运行成本高或模型表现不佳，事后改变分母。所有调用须有不可变 `experiment_id` 与明确状态：`VALID_DECIDED_1`、`VALID_DECIDED_0`、`UNRESOLVED`、`TIMEOUT`、`RESOURCE_LIMIT`、`UNSUPPORTED`、`INVALID_BY_FROZEN_RULE`、`INVALID_INPUT`、`INVALID_EVIDENCE`、`NOT_EXECUTED`、`INFRA_FAILURE` 等；区分数学三值和工程失败，不能把失败填为阴性或阳性。
5. **结论与证据分级。** `ARCHIVE_INTEGRITY_PASS`、`STRUCTURE_PASS`、`COMPONENT_REGRESSION_PASS`、`SAME_TASK_DIAGNOSIS_VALIDATED`、`FULL_DOMAIN_EXECUTED`、`PROBABILITY_CERTIFIED`、`INDEPENDENTLY_ACCEPTED` 分开记录。仅独立复核可以确认适用范围内的验收；G7 由主理论助手逐条审阅后决定，实验 Agent 无权宣布论文理论闭合。
6. **不确定就保留不确定。** 一般连续 LSTPN 不属于当前精确有限可计算子类、外部经典基线无法同题、原始工业故障发射事件未观测到等，都必须明确限定论断，不得使用硬编码值、假造事件、填充 PASS 或把抽样视为总体证明。
7. **本轮无“只登记不执行”式完成。** 下列每项任务均需提供实际被测代码、独立路径、输入、运行命令、退出码、stdout/stderr、原始中间量、结果账本和复算器；资源或工具确实不可用的项目保持 `BLOCKED` 并提交实际失败证据。即使某个关卡被阻断，仍保留已完成的其他独立工作，但不能越过其下游的正式阶段验收。

## 二、冻结现状与未闭合事项总账（不得先改数字）

| 编号 | 2026-11-24 审查时的真实状态 | 本轮必须完成的目标 | 归口 |
|---|---|---|---|
| C00 | 两 ZIP 已通过归档 SHA/CRC；内含撤回与最新报告混杂 | 建立唯一 CURRENT/RETRACTED 权威清单及可运行完整性门禁 | E3-00 |
| C01 | G1 原有 20 用例/5 变异；非法 `Gamma`、`Pe` 仍返回确定结论 | 联合概率可行域、证书真实性、错误输入的独立拒绝 | E3-01 |
| C02 | R6-04 接受异常时刻；R6-10 使用路径 ID 伪单射 | 从真实 PN 提取时刻；按 `omega_c` 等价类判断单射 | E3-02 |
| C03 | 13 个局部组件 68 用例、36 变异；非端到端引擎 | 将 R6-01—13 与实际网络求解、独立参考完整连接 | E3-03/04 |
| C04 | 八轴 143,360 候选、107,520 静态合法、35,840 不合法 | 研究域/种子/切片/故障数/规范 PN 身份与动态有效性逐项裁定 | E3-05 |
| C05 | 请求故障位置超过实际使用机器的候选 3,840；配置哈希混同 PN 哈希 | 精确量化全部格的实际故障数和不随参数元数据变化的规范网络身份 | E3-05 |
| C06 | TINA P/T 投影：104,052 有界、3,468 超时 | 保留其有限结论，核实原始日志，不冒充定时诊断 | E3-06 |
| C07 | 18 项外部/内部基线登记但没有同题性能结果；52 格仅 36 结构适配 | 真实内部四方法与能运行、能证明同题的经典 PN 基线 | E3-06/07 |
| C08 | 107,520 主域配置尚未跑四实现；1,620 敏感性只生成 | 实际全量逐格四方法诊断及八轴、种子、L/H 敏感性 | E3-07/08 |
| C09 | 21 点 `a4` 等先验连续观测解析可复核 | 567 个真实 LSTPN 概率模型、135 个真实数值规格及联合判定 | E3-09 |
| C10 | PyScrew 5000 来源、2500 工件、50 组、48 经验候选 | 原始数据全源经验评价、32 旧证书重核、1413/1421 ID 差异 | E3-10 |
| C11 | 当前 `final_verify_r6_e2.py` 漏检改变 R6-04 或严格 TINA 结果 | 独立内容级和研究总体级验收、恶意变异必检 | E3-01/11 |
| C12 | G7 仍 NOT_CLOSED | 全部有效结论与第 2—6 章声明逐条映射，主理论助手单独签署 | E3-12 |

**注意：** 107,520 是当前“按旧静态规则合法”的格数，**不是**已经最终裁定的数学研究总体；430,080=107,520×4 仅是 seed=0 主域若最终确认为合法所对应的最低四方法调用数；旧协议 `n_seeds=15`、`param_slice=3` 尚须核实，不能把 107,520×15 或 36,450 当成已确认最终样本数。已有 3,840 格故障位置饱和疑点，不得在冻结旧 V0 表内静默修改。

## 三、严格执行顺序与逐项验收

### E3-00｜原始工程冻结、证据权威清理（先执行）

**输入：** 上述 E2 两 ZIP、E2 最新交付说明、两次独立审计报告、冻结 TeX、旧 R4/E1 证据。  
**执行：**

1. 在 `R6_E3/baseline_readonly` 保存原件或准确引用只读路径；全量核对 ZIP 外层 SHA、成员 CRC、`SHA256SUMS`；核实 TeX 精确 SHA。建立 `input_inventory.json` 和 `replay_environment.json`（OS、CPU、Python、包版本、工具版本、运行入口、容器/机器架构、时区、种子来源）。
2. 建立 `evidence_authority_manifest.csv`，字段必须包含：`artifact_path,sha256,version,status,claim_ids,supersedes,withdrawal_reason,source_of_truth,verified_by,verification_command`。四种状态：`CURRENT`、`RETRACTED`、`HISTORICAL`、`UNVERIFIED`。
3. 对旧 `results/tina_all_merged.csv`/`tina_all_merged_summary.json` 所声称的全体无界，以及旧 `results/probability_567_*`、`reports/probability_567_full.md`、`reports/probability_sensitivity_full.md` 的错误风险公式、`Gamma=0`、567 完成说法，建立机器可识别 `RETRACTED_DO_NOT_CITE`；保留文件字节与全部失败日志，不得物理删除。当前 TINA 严格账本为 P/T 投影记录；21 点概率解析才是受限当前参照。
4. `tests/verify_authority_manifest.py` 必须拒绝任何 CURRENT 汇总依赖 RETRACTED 资料；验收器不得从旧路径静默导入过期结果。重新制作统一 `reports/current_evidence_scope.md`，对每一个数字标注“结构、P/T、局部、同题诊断、概率、经验”层次。

**完成证据：** 全部输入哈希通过、权威列表逐项可追踪、故意将旧撤回表作为 CURRENT 汇总输入时明确失败；生成的当前摘要不能出现“全部无界/567 已完成/TINA 仍未下载”等旧说法。`E3-00` 通过仅代表归档管理完成。

### E3-01｜先修复 G1 数值证据 P0 和验收器的内容漏检

**源码核查入口：** `implementations/subject/ap41_r6.py`，`oracles/independent/ap41_reference.py`，`tests/final_verify_r6_e2.py`。  
**执行顺序：**

1. 明确输入分为 `RAW_INPUT`、`VALID_INTERVAL_ENCLOSURE`、`AUTHENTICATED_CERTIFICATE`；外部布尔 `evidence_valid=True` 不得自证证书真实。验证原始概率域、每项上下界有效性、先验质量、互斥观察类别质量、联合质量关系和可行域是否非空。落实 `q_0+q_1=1`，`q_i∈[0,1]`，`0≤Q_i^Y(B)≤q_i`，`P_e∈[0,min(pi_0,pi_1)]`，`Gamma_delta∈[0,1]`；证书数值和模型来源绑定。对有效但宽松的外包围先与自然域及其他已认证约束安全求交，不因上界过松直接报错；交集为空则 `INVALID_EVIDENCE`，不是性质失败。
2. **必须实际运行**以下输入：`Gamma=[2,3]` → 拒绝；`Gamma=[-2,-1]` → 拒绝；`Pe=[-1/4,-1/8]` → 拒绝；`Q0Y=[0,3/4],q0=1/2` → 可行收紧；`Q0Y=[3/5,3/4],q0=1/2` → 矛盾拒绝；`Pe=[0,2]` → 依合同保守收紧或明确拒绝原始格式，不得确证其上界为 2；互斥观察类别的下界和超过对应 `q_i` → 拒绝；置信包围相互矛盾 → 拒绝；先验质量为零或适用性下界不正 → 按冻结算法 4.1 返回相应不适用/未决，而非假装有证书。
3. 把 `algebraic_interval_evaluator` 与 `authenticated_certificate_verifier` 分离：前者只能给外包围和条件判定，后者必须从冻结 PN、原始路径、质量账本、积分输出和数值严格包围重新认证，才能输出 `CERTIFIED`。有限有理样例的独立 oracle 用**独立确切样本空间枚举或有理线性约束求解**，不得复用被测逻辑判定函数、导入同一核心模块或直接照抄其预期答案。
4. 先复现上一轮 `r6e2_repeat_independent_probes.json` 中的失败，再修复源码，复跑原 20 例/5 变异与新增反例；增加“主体+参考同样错误但第三方不变量检出”的元变异。保护旧有效证书；修复后所有确定 verdict 必须符合实际输入域。
5. 立即建立新版独立 `tests/accept_e3.py`，**不再依赖旧 `final_verify` 的状态计数通过**；先覆盖真实篡改 `runs/g2_r604/results.csv` 的 `subject_outcome`、最新 TINA 严格账本的 `BOUNDED→UNBOUNDED`，即使保留 PASS 和 CSV 行数也必须检出。先做失败性基线（旧验收器漏检）再做新版检出。

**阻断门槛：** 任何无可行概率的证据产生 `v_P∈{0,1}`、任何主体/参考共错未被数学不变量检出、任何上述实际篡改未被新验收器检出，则 `E3-01 FAIL/P0`。不得提前出具 G1 PASS。

### E3-02｜修复真实轨迹时间合法性与第五章观测单射（P0）

**时间模块：** `implementations/subject/r604.py`、`oracles/independent/r604_reference.py`；关联 R6-02/R6-03。  
**单射模块：** `implementations/subject/r610.py`、`oracles/independent/r610_reference.py`。  
**执行：**

1. 从模型原始发射序列和时间戳、完整标识、故障变迁、完成谓词**计算** `tau_f`、`tau_c`、首次完成位置、当前有效时域；外部 `tau_f/tau_c` 若存在，只能作为待校验声明，不能作为合法完成历史的信任源。对完成于分析时域外、负时间、完成早于该历史首次故障、非首次完成、前缀未闭合、完成后重复故障等分类按定义拒绝或另归类。
2. 必跑四个负测：`tau_f=3,tau_c=2`；`tau_f=1,tau_c=20,H_A=5`；`tau_f=-1`；`B_c=0`（当前理论的 `B_c>0`）。必跑正测：同一变迁同时故障与完成 `tau_f=tau_c`、首次完成恰在合法 `H_A` 端点、`tau_c=tau_f+B_c`、合法零时间/即时发射优先序。短前缀不得被当作 violation；未决右端点保留全部前沿。
3. 对 R6-10 每条路径从原始事件构造 `omega_c=(observable_word, first_completion_total_time)` 与 `Y=psi(omega_c)`；单射定义域是**不同的 `omega_c` 值集合**，不是路径 ID 集。要求实测 `omega1≠omega2 ⇒ g(omega1)≠g(omega2)`；相同 `omega_c` 的多条路径允许相同 `Y`。不同 `omega_c` 被量化为同一 `Y` 时，严禁使用第五章严格跨层充分定理。
4. 另外核查真实外部完成信号、正常/故障域对齐、同一强时间语义和样本支持与可测性；任何检查依赖仅靠 `True` 字段声明而没有证据，则留 `NOT_CERTIFIED`。
5. 独立 oracle 从实测网络可达运行进行有界枚举或符号约束判定，不照搬主体按路径 ID 去重的算法。正反例加真实源码级变异并保留运行原始日志。

**阻断门槛：** 任何非法时间仍输出 `COMPLETED_IN_TIME`，或两条同观测不同路径被误判“不满足单射”，则 `E3-02 FAIL/P0`；第 5 章跨层充分条件不可宣称已实现。

### E3-03｜恢复旧 R4 P0/P1 并将 R6-01—13 逐项提升为真实 PN/LSTPN 输入

**不可省略的旧缺陷：** R4 的 `x` 消耗并重建 `py` 时，需在**中间标识**识别 `Y` 失能再使能、重置时钟；额外使能即时根必须使用全部 `pre(t)≤M` 的候选及真实权重；M11 时钟生命周期变异必须改变参与概率积分的状态而不是只改变日志。以上均需真实代码/变异并保留旧错误复现。

**13 项逐一完成（每项都要模型、主体输出、独立参考、正反例、实际变异、验收记录）：**

| ID | 应实现的真实语义及必须检查的反例 | 不能用作替代的现有结果 |
|---|---|---|
| R6-01 | 前/中/后使能、持续使能与时钟新实例、强时间紧迫、即时优先；中间失能重启时钟 | 3 个局部 PASS |
| R6-02 | 同次故障与首次完成、零时差、完成窗口端点、外部完成条件 | 5 个预设结果 |
| R6-03 | 完整合法样本、非完成终止、死锁、时域截断、计算预算前沿五类及质量守恒 | 3 条标签分类 |
| R6-04 | 故障后首次完成、`B_c` 与 `H_A` 一致性、右端点即时闭合后再截断 | 6 条有错误输入域的旧测试 |
| R6-05 | 逻辑混合 DBM/状态类的精确差分分割；同类中违例与非违例不能整体丢弃 | 3 个手设分割例 |
| R6-06 | 无损历史保持、可观测词与完成时长一致、同故障/正常见证与耦合 LP | 6 个独立标签例 |
| R6-07 | 即时根全部竞争、历史依赖的联合密度传播、时钟生命周期与完整质量树 | 5 条人工质量账本 |
| R6-08 | 算法 4.1 全部区间/阈值/先验/未决优先级、原始证书绑定与联合可行域 | 10 个模块代数 PASS |
| R6-09 | 有限有理分段密度、有限深度/时域、多面体类别精确积分；不可计算子类正确 UNSUPPORTED | 5 条子类声明 |
| R6-10 | 真实 `omega_c→Y` 单射、外部完成标志、正常故障域对齐、严格充分定理适用 | 8 条路径 ID 检查 |
| R6-11 | 零测度支持相交、原子质量、观测粗化下 Bayes 风险与覆盖率的不同规律 | 4 个闭式数字 |
| R6-12 | 第 6 章逻辑 52×4 历史可追溯性、方法输出/见证与扩展全域的合法范围 | 5 个状态标签 |
| R6-13 | 第 6 章 32 工况/48 候选/5000 来源及概率数据的归属、区间与数据对账 | 5 个来源数字 |

每个组件至少包含：`original_case`、`new_counterexample`、`actual_network_trace`、`subject_output`、`oracle_output`、`invariant_verdict`、`mutation_patch`、`mutation_exit_code`、`coverage_limitations`。对`v=0`必须有可独立复放的合法反例见证；对`v=1`必须提供相应已定义域内的穷尽证据或严格数学证书；预算结束不得返回 `v=1`。互相复制的主体/参考模块不算独立验证。

**阶段门槛：** R6-01—13 的局部回归全部通过只是 `COMPONENT_REGRESSION_PASS`；必须进一步在真实 PN/LSTPN 上通过集成测试，才能申请 `G2_INTEGRATED_PASS`。

### E3-04｜实现可从真实 PN 出发的统一诊断引擎与独立参考

1. 实现能够读取本轮全部合法 TPN 模型的完整数据接口，保留库所、变迁、弧权重、初始标识、可观测标号、故障变迁、首次完成谓词、上下时间区间、强时间紧迫、`L/H`、时钟实例生命周期与所用随机分布版本。模型适用性判定应给可检查理由，不能仅 `supported=True`。
2. 共同状态路径：真实使能和发射→状态类/DBM→必要的精确区域拆分→观测词与首次完成时长→正常/故障同步与完整历史保存→可行性 LP→诊断 `1/0/⊥` 或受限域 `UNSUPPORTED`；任何判定必须有 trace/certificate 或可重放搜索证据。若存在潜在无限状态行为，须有冻结的有限界或严格抽象完备证明，不能在预算耗尽时默认穷尽。
3. 实现四条**真实不同的计算路径**：`MAIN`（论文完整法）、`FULL_HISTORY`（无剪枝完整历史及独立耦合 LP）、`NO_SYNC`（去同步筛选但保留其他约束）、`NO_ENVELOPE`（去时间包围筛选但保留其他约束）。不可让四个标签调用同一代码然后填写不同名字；共享基础语义解析可接受，但消融作用点、调用序列、状态类计数和真实性必须从代码实际运行反映。
4. 对精确结果设计独立 oracle：小型模型完备逐路径枚举+有理 LP、独立 SMT/LP 可行性、条件严格求积；标明参考的完整能力边界与预算限制，不允许在一般大规模模型上用局部 oracle 声称总体正确性。
5. 实现真实的资源度量：墙钟、CPU 时间、峰值内存、状态类/弧/同步对数、LP/积分调用数、超时/内存限制；统一硬件、运行配置、输入和预算。数据行中禁止使用预填 wall time、硬编码 `PASS`、先验期望 verdict。
6. 先在继承 16 微型+36 生成模型上真实运行并报告历史原始字节是否可用、52 个模型重建身份、4 方法的 208 条新调用结果和与历史状态的差异。再逐步进入完整主域；禁止先根据运行速度或成功状态裁剪正式实验分母。

**门槛：** 若只有局部组件、手写标签、人工概率公式而无模型驱动的统一引擎，则 E3-04 `NOT_CLOSED`，G4 主域诊断一项不得声称执行。

### E3-05｜全量实验研究域仲裁、故障数审计与双层模型哈希

1. 从 `scope/fullscale_protocol_corrected.yaml`、`scope/generator_candidate_universe_full.csv`、`scope/model_validity_rules.json`、历史 `n_seeds:15`、`param_slice:3`、36,450 实例和 52/54 格逐项追踪生成谱系。输出所有原始组合及修订建议；主理论助手最终裁定正式 seed/切片、参数域、L/H 域和有效性规则**之前**，Agent 只能完成域事实审计和模型准备，不得对一个自选子集给“全量主域已完成”结论。
2. 保留 `domain_V0_143360.csv`（原 143,360 候选/107,520 静态合法/35,840 静态不合法，原样）；针对 3,840 个 `fault_locations>min(n_machines,n_parts×ops)` 的格实际从生成 PN 复算 `requested_fault_locations, used_machine_count, actual_distinct_fault_machine_count, actual_fault_transition_count`。若定义是精确需求，提出新的正式 `domain_V1`，保留原 V0 与变更记录；若定义是上限/饱和参数，明确更名及实际故障数分析。绝不在 V0 上直接删行或修改标记。
3. 每条至少保存三种身份：`config_sha256`（含完整配置/种子/生成器版本），`semantic_net_sha256`（排除无作用元数据、包含真正库所/变迁/弧权重/初始标识/时间区间/标签/故障/完成属性），`spec_sha256`（L/H/窗口/观测与概率参数）。同构未被证明时，只称“规范内容相同”，不称“行为等价”。完整 107,520 配置都要计算 `semantic_net_sha256`，报告不同规范内容数、每个内容对应多少配置及导致无真实变化的参数轴计数；前缀 1,000→352 只能作旧发现，不能外推全域。
4. 区分结构静态合法、实际动态可达、有界、完成可达、在规定时域有完备可诊断查询的适用性。TINA 非时间投影的结果不能单独证明定时语义，也不能以超时项充作无界。不符合精确数学定义的模型应附原始反例，按**预先冻结规则**分类，不得根据计算难易重设合法域。
5. 输出审查签署申请 `formal_domain_adjudication_request.md`，列出每一种研究域选择会导致的精确样本数、预计算法调用数及与论文已有结果的关系。主理论助手签署后的 `frozen_full_domain.json` 和逐行 `domain_index.csv` 将成为所有实验唯一分母；签署前不得按未确定域做最终统计。

**门槛：** 未明确种子/切片、故障位置准确含义和规范 PN 身份的研究，G0 继续 `PARTIAL`。研究域裁定不能由实验 Agent 自封。

### E3-06｜经典权威 PN 基线：先证同题，再做真对比

按原 18 项登记逐项完成获取、版本、许可证、原生数学规格、模型转换、观测/时间/完成/故障语义、适用子域、运行日志；不可只改 `NOT_AVAILABLE` 字段。

**对比层级：**

- **B1 必须完成、同一研究问题：** MAIN、FULL_HISTORY、NO_SYNC、NO_ENVELOPE，完全相同模型、首次完成、故障、观测词与完成时长、L/H、时间语义、预算。MAIN 对 FULL_HISTORY 是主要正确性/效率对照，NO_SYNC/NO_ENVELOPE 是必要机制消融。
- **B2 时间 PN 领域：** Basile/Cabasino/Seatzu 一类 MSCG+LP、TINA 对应可复验任务完成查询、TWINA/Product TPN。必须审核 K-诊断性、时间语言同步与本论文首次完成定义不同之处；仅建立合法同题适配的共同子域才能算直接性能差异。若采用自己实现的文献算法，标 `INDEPENDENT_ADAPTATION`，不能冒称原作者原版可执行程序。
- **B3 PN/离散事件经典：** Diagnoser、Verifier Net、MBRG/BRD，仅在无时间/共有事件观测子问题上比较；原生研究问题不同则只做文献或共同投影参照。
- **B4 概率 PN：** 有理事件树+独立精确多面体积分是首要数学 oracle；ORIS/Sirio/随机状态类方法作匹配概率量对照；PRISM 只在合法 CTMC/DTMC 特例；MC/SMC 只作近似精度与效率，不是严格证书。机器学习基线仅属于工业数据预测研究。

每项填写 `baseline_same_task_ledger.csv`：`baseline_id,reference,original_task,source_url_or_identifier,license,version,artifact_sha,acquisition_attempts,compatibility_class,assumption_check,model_adapter,common_domain_definition,run_count,outcome_status,evidence_path`。分类只允许 `EXACT_SAME_TASK / ADAPTED_SAME_TASK / SHARED_PROJECTION_ONLY / CONTEXT_ONLY / NOT_AVAILABLE / UNSUPPORTED`；不能从 `TINA-BOUNDED` 得出“本文算法诊断更快”或从不同算法的问题规格比较正确率。

**门槛：** 四种内部同题算法没实际运行则 G3 核心不通过；适用外部同题基线有源码/许可/兼容性却未执行其预先定义共同域，同样不通过。确实无法取得的外部方法提供尝试证据，保留缺口，不伪造结果。

### E3-07｜全量逻辑主实验：所有冻结合法格 × 四方法真实运行

1. 按 `frozen_full_domain.json` 展开唯一 `domain_index.csv`，每个 `config_id×seed×spec_id×method_id` 一行，**先写入全部预期任务 ID 和 `NOT_EXECUTED`**，再用真实运行逐行更新。合法/不合法及 `UNSUPPORTED` 必须有来源规则，不能在运行后重新计算分母。
2. 若经正式裁定主域为现有 seed=0 的 107,520 个配置且每配置一组 L/H，四种内部方法至少应有 430,080 条调用记录。若种子谱系决定更多组合，严格按新冻结总量执行，数量需要单独重新计算，不能凭 15 倍机械推断。
3. 实施可恢复且幂等的批处理：显式资源限制、固定工作池/环境、模型和输入哈希、独立日志、退出码、每条实际资源、失败重试次数与原因；失败重试不更换模型 ID，所有旧失败原始日志保留，禁止伪填运行时间、将未启动任务记为 TIMEOUT。
4. 每条由原始源码产生 `result_status, v_L, witness_path, completeness_certificate, timed_trace, symbolic_state_count, synchronized_pair_count, LP_count, elapsed_wall, cpu_seconds, peak_rss, exit_code`。两种方法的同题配对必须在完全相同模型/规格上执行，配对加速比只算双方成功且正确可比的共同集合，同时报告主域各状态总数。
5. 凡 `v_L=0`，独立重放正常/故障两条首次完成运行，验证观察同值且满足约束；凡 `v_L=1`，验收其完整探索/数学证书，不能用“无搜索结果+预算耗尽”充当证明；`⊥`保留未决。
6. 与历史 52×4 记录差异单列，不得把历史 208 行导入 `fresh_run`。所有完成/未完成的状态进入逐格总账，任何缺行将使全域验收 FAIL。

**门槛：** `FULL_DOMAIN_EXECUTED` 仅表示所有预注册任务均真实启动且达到明确终态（允许真实 TIMEOUT/UNRESOLVED），不等于所有数学结论通过；`FULL_DOMAIN_DIAGNOSIS_CERTIFIED` 还需每项确定结论具备可独立核验证据与一致性。任何未启动任务不能换名为超时来凑齐执行率。

### E3-08｜全量敏感性：八轴总体 + 1,620 配置 + L/H/资源与交互

1. **主域八轴统计**必须对所有冻结参数格产生可复算分组结果：机台、工件类型、工序、WIP、不可观比例、故障位置、时间区间宽度、可调比例，另外报告并发数、实际故障数、观测混叠、状态类、LP 数与预算。每个轴报告全体状态组成与计算成本，不只报告成功样本；对两因素交互明确预注册组合和共同可比范围。不要把重复配置当作不同结构网络的独立重复试验。
2. **1,620 逻辑敏感性模型**采用冻结的 `54×10 seeds×3 WIP`，每个具体模型真实运行四方法；若正式签定 3×3 L/H，形成 14,580 个模型—规格任务及 58,320 条算法调用。必须先确定 L/H 取值和边界合法性；如果这些参数没有理论签定则标 `SPEC_BLOCKED`，不能在结果后选择容易的三档。
3. 记录 L/H 窗口端点、故障位置、不可观测比例、计时宽度、观测粗化、并发、LP 容差、资源预算的独立/配对影响；不违反冻结理论假设地做变化。展示模型内容加权与配置格加权两套描述统计，不把参数重复造成的样本量误写为模型多样性。
4. 对已声明理论单调性执行系统性正反例：同域 L/H 变化歧义见证保留的适用条件、固定先验下观测粗化时 Bayes 最小风险不下降、可靠覆盖率不预设单调性。报告违反条件时的反例而非事后删除。

**门槛：** 只有 1,620 个 `GENERATED_STRUCTURE_PASS` 或只对 54 个子域做图表，不算敏感性任务完成。

### E3-09｜概率：真实 567 个 LSTPN、135 个数值规格及严格积分

1. 以已经验收的 `a4=3..4` 共 21 个连续观测点作为受限校核基准：核对 `a4=3` 时 `Pe=1/4,Gamma=1/2`，`a4=3.5` 时 `Pe=1/8,Gamma=17/24`，`a4=4` 时 `Pe=0,Gamma=1`。这些**不构成** 567 格，不能继续使用旧 `Pe=(4-a4)^2/[4(5w-a4)]` 或 `Gamma=0` 等已撤回式子。
2. 在主理论助手确认模型适用的数学类后，事先列出 21 个 `a4` ×3 个**真实定义的**分布族 ×3 个即时根权重方案 ×3 个明确的观测量化规则 = 567 个有独立模型/规则指纹的实验配置。每格保存实际输入 LSTPN、各时钟密度及支持、根竞争权重、条件先验、观察映射、求积域、实际路径联合测度及起止条件。`D1/P1/Q1` 等只有标签却无定义的记录不得计为模型已生成。
3. 真正执行有限有理分段密度、有限时域/深度且可精确处理的严格子类，完成历史依赖的条件联合概率和安全区间求积；subject 和 oracle 采取不同路径（精确有理分段积分/完整小样本空间/多面体分解）。对于数学上不支持的分布或观察类按预冻结适用条件 `UNSUPPORTED`，不得套用等先验 21 点公式。
4. 冻结 5×3×3×3 = 135 个具体 `(pi,epsilon,delta,gamma)` 元组，并给出各轴实际数值、数学合法性、来源与唯一规格哈希。消除 `FILLED_SINGLE_POINT_ALL`、全部符号占位或单一点复制。将全部 567×135 = 76,545 个潜在模型—规格判定单元先写入全量任务账本，再逐格产生认证、未决或不支持（不适用时说明数学原因）。
5. 对严格认证记录保存 `q0,q1` 联合界、各互斥观测类别 `Q_i^Y(B)`、归一化/适用性、`Pe` 严格界、`Gamma` 严格界、数值算法误差证书、未解析前沿质量及实际证据绑定。检查即时根额外转移、持续时钟与真实重抽样突变对结果的影响；误差区间和处理时间作完整敏感性。
6. 独立重复计算所有 21 已知点及全部正式 567/135 输出的必要验证；不得将局部解析参照与全模型数值求解混为一谈。若严格模型类不能覆盖某些预注册组合，必须报告 `UNSUPPORTED`，由主理论助手裁定是否修改正式科学表述，不得运行后换目标。

**门槛：** 567 模板、135 符号标签或 76,545 行公式复制，都不是概率全量完成；决定性质的 `v_P=0/1` 需要可检查有效证书，无法证实时保持 `⊥` 或相应工程状态。

### E3-10｜PyScrew：5000 全源数据、四模型经验对比与历史证书核验

1. 使用 `chapter6/build_population_portable.py`、`chapter6/split_plan.csv` 和 `scope/pyscrew_raw_manifest.csv` 中的版本规则，支持 `--raw-root` 可移植入口；在真实可访问的目录逐个对 5000 JSON 复算 SHA、工件和左右侧配对、25 类/50 来源组、`OK=4307,NOK=693`。数据未随包交付时，本地独立审计状态必须为 `RAW_NOT_VERIFIED_ON_AUDITOR_MACHINE`；Agent 有原始访问记录可标 `AGENT_LOCAL_REPLAYED`，两个层次不可混淆。
2. 对每条原始记录建立 `raw_record_id,physical_workpiece_id,side,class,source_sha,split,raw_status,feature_status,completion_status,reason_for_exclusion,label,model_id,prediction,uncertainty` 等完整账本。预先冻结工件级训练/校准/留出划分，严禁同一工件左右侧数据泄漏到不同集合；对于 NOK 条目记录不可评价的具体原因，而不是从总体清单删除。
3. 真实运行原协议四个经验模型（以冻结原文件的算法 ID 为准，不可凭印象更名），在**相同有效 ID 交集**上报告 AUROC、Brier、NLL、平衡准确率、风险—覆盖曲线、失败率与按类别/左右侧/完成状态分层。无可评价标签的记录仍报告清单覆盖和排除原因，不能把不同分母结果直接排名。
4. 逐个查明历史 1413 条共同有效记录与 1421 条主方法有效记录的差异 ID、排除条件、数据源和预测来源；拿不到历史源文件时标 `PROVENANCE_UNRESOLVED`，不得删掉 8 条来制造历史一致。
5. 历史 32 个工况逐项重取原始模型/先验/数值证书、检验 `3 PASS/25 FAIL/3 UNRESOLVED/1 INSUFFICIENT_DATA` 的旧结构结果是否有新版有效性；“风险过阈”不等于完整逻辑规格均认证。48 个变化/正常对照均入经验比较，在无物理缺陷→PN 故障实际发射→外部完成信号的可查映射时保持 `NOT_CERTIFIABLE_FOR_STRICT_LSTPN`，不能补造故障时刻或生成虚假严格风险证书。
6. 输出实际可评价子域及全部来源层分母，按可观测输入类型、分布漂移、量化/阈值、类别、左右侧、随机种子做预先声明的全量敏感性与不确定性报告；不得使用历史 32 工况子集支撑全部数据的严格风险结论。

**门槛：** 5000 来源 SHA 对账不是四模型结果；48 个 `NOT_CERTIFIABLE` 并不阻止做经验全量实验；历史 32 工况没有重新认证不能写新 PASS。

### E3-11｜独立终验：字节、内容、数学与研究范围四层验收

1. 对全新 `R6_E3` 完整/便携证据 ZIP 洁净解压，独立执行逐项 SHA、CRC、输入指纹、解释器/工具和参数版本校验；外部原始 JSON 不存在时不显示 `FULL_RAW_REPRODUCIBLE`。
2. 实验结果级：从输入模型、正式运行日志、原始 TINA 标准输出、原始参考 LP/积分中间数据独立复算关键 verdict、质量、风险/覆盖、时间和分类结果；拒绝仅检查 `PASS`、行数、哈希长度和预录总计。
3. 研究范围级：校验每个冻结候选×seed×L/H×方法都存在唯一实际执行记录，状态与原始运行日志一致，缺行不容忍；校验 1,620、567、135、76,545、5000、48、32 各自是**正式运行还是仅登记**；验证 52×4 历史/新运行来源区别和经典基线同题性矩阵。
4. **至少 16 类真实故意注错，逐类现场运行且每次恢复原始副本**：①`Gamma>1`；②`Pe<0`；③互斥类别质量超先验；④`tau_c<tau_f`；⑤`tau_c>H_A`；⑥同观测不同路径的伪单射；⑦不同观测被粗化的伪适用；⑧中间失能不重置；⑨漏加额外即时根；⑩仅日志重抽样不影响积分；⑪改 R6-04 outcome 保留 PASS；⑫改严格 TINA 结果保留 PASS；⑬改模型规范 SHA 为等长错误值；⑭改概率总质量或 Pe/Gamma 原始数值保留状态；⑮删一条四方法调用/改状态为 TIMEOUT 伪装未启动；⑯改变 PyScrew 评价分母/工件组泄漏。另对撤回旧数据污染 CURRENT 汇总做独立负测。每类留下实际补丁、变异后输入 SHA、命令、退出码、stdout/stderr、检测器命中位置、预期/实测、恢复原样的 SHA。
5. 独立验收不能由被测主体自身导入同一个 oracle 或同一份预期 JSON 直接宣告通过；尽可能由独立测试入口、算法不同的参考和数学不变量交叉检查。验收用例本身如发现假定错误，保留争议并提交主理论助手，不能为了绿灯删掉反例。

**终验输出：** `independent_acceptance.md` 的每一项有运行命令、原始证据路径、适用范围、当前状态和未解决反例。四层门禁全部对应合同对象通过才可授予 `E3_ACCEPTED_WITH_DECLARED_LIMITS`；涉及明确强制范围未执行或 P0 未解时一律 `PARTIAL_NOT_CLOSED/FAIL`。

### E3-12｜逐项关联第 2—6 章数学声明与交付结案

建立 `claim_to_evidence.csv`，字段至少 `chapter,claim_id,exact_theory_anchor,model_domain,mathematical_precondition,subject_source,oracle_source,test_case_id,raw_log,completeness_or_uncertainty,evidence_status,remaining_gap,requires_theory_review`。必须覆盖全部 R6-01—13、算法 4.1 判定分支、第五章跨层关系、第六章每张逻辑/概率/工业表及每个经典方法性能结论。

对于每条明确结论，保留证据等级：`PROVED_BY_THEORY_ONLY`、`EXECUTABLY_CROSSCHECKED`、`STRICTLY_CERTIFIED_ON_DECLARED_SUBCLASS`、`EMPIRICALLY_EVALUATED_ON_FROZEN_POPULATION`、`HISTORICAL_ONLY`、`RETRACTED`、`UNVERIFIED`。证据不得高于实际范围。实验 Agent 不负责修正文中定理，仅附“哪些论文表述不受现有证据支持”的精确清单供主理论助手裁决。

## 四、分阶段放行表（必须先通过前序 P0）

| 顺序 | 验收门禁 | 通过条件 | 未通过的允许报告 |
|---|---|---|---|
| 0 | E3-00 输入/权威冻结 | 原 ZIP/TeX SHA、CURRENT/RETRACTED 隔离和调用链核对 | `ARCHIVE_BLOCKED` |
| 1 | E3-01/02 数学 P0 与内容篡改 | 必跑全部上一轮反例、第三方不变量、真实篡改检测 | `P0_FAIL`，后续结果不得封版 |
| 2 | E3-05 研究域事实审计及主理论裁定 | 种子、切片、故障数、模型/规格身份全部冻结 | `DOMAIN_PENDING_THEORY_SIGNOFF` |
| 3 | E3-03/04 集成引擎 | 真 PN/LSTPN 驱动，13 模块全回归，见证/穷尽/数值证书可重放 | `INTEGRATION_NOT_CLOSED` |
| 4 | E3-06 经典基线准入 | 内部四方法可跑；外部方法逐项判断可比性与共同域 | `BASELINE_PARTIAL` |
| 5 | E3-07/08 主域及逻辑敏感性 | 冻结全集逐格实际执行，状态与证据全量对账 | `FULL_LOGIC_PARTIAL` |
| 6 | E3-09 概率 567/135 | 分布与规格真实冻结、实际传播/积分、有效证书及未决完整保留 | `PROBABILITY_PARTIAL` |
| 7 | E3-10 PyScrew 全源 | 5000 全量经验评价、48 比较、32 历史证书和样本差异说明 | `PYSCREW_PARTIAL` |
| 8 | E3-11 独立终验 | 至少 16 类故意注错、字节/数学/内容/总体四层检查 | `INDEPENDENT_ACCEPTANCE_FAIL` |
| 9 | E3-12 理论映射 | 各章逐主张证据支持范围，交主理论助手另行签字 | `G7_NOT_CLOSED` |

若受预算阻断，可如实交付中间完整工程与失败证据，但**不能跳过未执行的项目、缩小分母后改称“全量通过”或把完成计划当成完成实验**。每一阻断应写入 `reports/remaining_blockers.md`，包含未执行任务数、受影响的理论声明、必要补救条件和下一次可恢复的精确实验 ID。

## 五、统一结果行规范与全过程复算

所有结果必须至少有：`experiment_id,domain_version,config_id,seed,spec_id,method_id,semantic_net_sha256,input_model_sha256,implementation_commit,oracle_commit,tool_version,command,started,exit_code,elapsed_wall_seconds,cpu_seconds,peak_rss_bytes,status,logical_verdict,applicability_status,witness_or_certificate_sha256,raw_stdout_path,raw_stderr_path,error_reason,attempt_no`。概率另外保存 `q0/q1/Q_i(B)/Pe/Gamma` 严格上下界、证明/积分证书、原始质量路径、未解析质量与适用性；工业数据另外保存来源文件哈希、工件与侧别、实际样本分母、是否完成、预测 ID/证据。

结果依赖链必须从 `raw_input→generator/model→executable_subject→independent_oracle→raw_output→content_verifier→claim_manifest` 可追踪。每一条诊断 PASS 必须有实际执行时间和可核查原始文件；纯生成/结构/预注册的 `execution_stage` 必须不同。全域汇总由明细自动计算，禁止人工把汇总状态写成 PASS。

## 六、必须交付的目录和文件（文件缺失或空壳不能通过）

```text
R6_E3/
  README.md
  baseline_readonly/                 # 不修改原件；可引用原只读 ZIP
  contracts/
    input_inventory.json
    math_interface_contract.md
    evidence_authority_manifest.csv
    domain_V0_143360.csv
    formal_domain_adjudication_request.md
    frozen_full_domain.json          # 主理论签署后才生效
    execution_matrix_frozen.csv
    benchmark_budget_frozen.json
  implementations/
    subject/                         # 全部真实 PN 语义和四方法实现
    probability/                     # 联合传播与严格证书
    generator/                       # 版本、参数语义和身份计算
  oracles/
    independent/                     # 不复用主体决定性判断
  models/
    regression/                      # 数学 P0、旧 R4、13 组真实例
    generated/                       # 真实模型可重放、哈希可查
  baselines/
    baseline_same_task_ledger.csv
    source_and_license_inventory.csv
    semantic_equivalence_matrix.csv
  results/
    model_semantic_identity.csv
    full_logic_4methods.csv
    sensitivity_full_logic.csv
    probability_567_model_runs.csv
    probability_135_specs.csv
    probability_76545_decisions.csv
    pyscrew_full_5000.csv
    pyscrew_48_comparisons.csv
    historical_32_certificate_audit.csv
    historical_1413_1421_reconciliation.csv
    claim_to_evidence.csv
    phase_gate_status.csv
  tests/
    run_all_math_regressions.py
    run_subject_oracle_comparison.py
    verify_authority_manifest.py
    verify_full_domain_coverage.py
    run_negative_controls.py
    accept_e3.py
  runs/
    math_p0/
    logic_main/
    logic_sensitivity/
    probability/
    pyscrew/
    baselines/
    negative_controls/
    independent_acceptance/
  reports/
    protocol_lineage_and_actual_faults.md
    new_math_counterexamples.md
    benchmark_fairness_and_limits.md
    full_scope_audit.md
    independent_acceptance.md
    remaining_blockers.md
    final_delivery.md
  SHA256SUMS
  R6_E3_complete_workspace.zip
  R6_E3_portable_evidence.zip
```

文件格式可根据已冻结现有工程做等价精确映射，但必须在 `README.md` 提供一一对应路径；不能将 `NOT_EXECUTED` 行装作已运行，不能生成只有列名没有数据或日志的“完成”文件。脚本接口示例（根据实际 `R6_E3` 工程实现，不准空函数回显 PASS）：

```bash
python -B tests/run_all_math_regressions.py
python -B tests/verify_full_domain_coverage.py --domain contracts/frozen_full_domain.json
python -B tests/run_subject_oracle_comparison.py
python -B tests/run_negative_controls.py
python -B tests/accept_e3.py --mode archive
python -B tests/accept_e3.py --mode content
python -B tests/accept_e3.py --mode population
python -B tests/accept_e3.py --mode math
# 如原始工业数据真实可访问，再运行：
python -B tests/accept_e3.py --mode raw-data --raw-root /path/to/pyscrew
```

如任何一条脚本尚未实现，真实退出非零并显示 `NOT_IMPLEMENTED`，不能通过固定打印 `PASS` 代替。

## 七、最终报告必须遵循的结论模板

1. **原始资产**：原始归档 SHA/CRC、TeX 哈希，旧撤回证据已隔离。  
2. **数学 P0**：逐反例展示“旧错误输出→新程序输出→独立数学参照→真实变异检出”，尚错则 FAIL。  
3. **实验研究域**：143,360 原始形式全集、原静态合法 107,520、故障数不一致 3,840、正式冻结 V1（若有）、每轴真实取值、实际种子/L/H 数量、规范 PN 独立数量及重复配置。  
4. **逻辑主域**：预期调用、已实际启动、完成/未决/超时/错误、四方法配对结果、见证/穷尽证书覆盖率，逐格可查。  
5. **经典基线**：各方法的原生任务、合法同题域、源码/版本/许可证、真实运行条数、不可比理由，不得给未运行方法虚构速度。  
6. **逻辑/概率敏感性**：真实 1,620×方法、L/H、567 LSTPN、135 具体规格、76,545 单元执行与证书状态，不得用旧撤回风险公式。  
7. **PyScrew**：5000 原始记录中 OK/NOK 的去向、四经验模型一致分母、48 比较候选、32 旧证书状态、1413/1421 差异。  
8. **独立验收**：实际从文件/模型/日志复算的证据及 16 类真变异检出，不能只贴一份预期结果 JSON。  
9. **结论边界与 G7**：哪条第 2—6 章数学/实验声明可被当前证据支持、仍有哪些 P0/P1、哪些结论必须撤回或重做。实验 Agent 最终仅可提出 `G7_REVIEW_REQUESTED`，不能自行设成 `G7_CLOSED`。

**结束条件**：全部合同必做任务在冻结范围内真实完成、数值和数学接口的 P0 消失、外部对照有诚实同题性说明、原始实验可复放、独立验收通过，方可申请主理论助手裁决；任何任务无法完成都必须交付已完成的真实证据和明确未闭合账本。不要反复以“资料包哈希验证 PASS”“组件局部 PASS”或者“已注册全部候选”为由宣布阶段完成。
