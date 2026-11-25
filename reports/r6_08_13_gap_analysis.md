# R6-08..R6-13 缺口分析（批次 B 施工单）

依据合同第 96-110 行。结论：六项中两项主体已存在（R6-08、R6-10），两项部分存在（R6-11、R6-13），两项基本新建（R6-09、R6-12）。

## R6-08｜算法 4.1 全区间/阈值/先验/未决优先级 + 原始证书绑定 + 联合可行域

已有：
- `implementations/subject/ap41_intervals.py`（区间/先验/未决优先级，CONDITIONAL_ONLY）
- `implementations/probability/immediate_evidence.py`（模型 SHA 绑定 + 账本重放）
- `implementations/probability/immediate_metrics.py`（精确 Pe/Gamma）
- `oracles/independent/ap41_polytope.py`（联合可行域顶点枚举，51 例对照）

缺口：
1. 阈值边界与先验零质量的**逐条优先级表**驱动用例（合同列的 9 类输入在 `runs/math_p0/legacy_probability_reproduction.json` 只覆盖 3 类；`Gamma=[2,3]`、`Pe=[-1/4,-1/8]`、互斥类别下界和超 q_i、置信包围矛盾、先验零质量需全部进测试）。
2. "原始证书绑定"到判定输出的单入口（现在 evidence 与 metrics 是两步）。
3. 组件化封装进 `r6_components` 模式（acceptance record + 变异：如 IGNORE_CATEGORY_SUM 已有局部版，需迁移到统一变异表）。

## R6-09｜有限有理分段密度、有限深度/时域、多面体类别精确积分；不可计算子类正确 UNSUPPORTED

基本新建：
- 分段有理密度的精确积分器（有理区间上多项式密度 → 精确有理原函数求值）。
- 多面体类别上的精确质量计算（可按类别分解为区间乘积时逐维积分）。
- 明确 `UNSUPPORTED` 子类判定（非有理分段密度、无限深度、非多面体观测区域）。
- 参考：独立换元/分部积分路径，与主体不同算法。

## R6-10｜真实 omega_c→Y 单射、外部完成标志、正常故障域对齐、严格充分定理适用

已有（主体基本完整）：
- `implementations/subject/cross_layer.py`（结构/投影/支持/可区分性/证据检查）
- `implementations/subject/reachability.py` + `omega_injectivity`（探索集单射）
- `implementations/subject/timed_trace.py`（omega_c 构造）

缺口：
1. 独立参考实现（现有 reference 只覆盖 projection_status；跨层全项需独立重算）。
2. 组件化封装 + 变异（如去掉 uncompleted_distinguishable 检查、把碰撞当适用）。

## R6-11｜零测度支持相交、原子质量、观测粗化下 Bayes 风险与覆盖率的不同规律

部分存在：`immediate_metrics` 的原子质量与 Pe/Gamma 精确计算。缺口：
1. 零测度单点共享不贡献 Bayes 错误的构造性用例（连续密度族）。
2. 观测粗化（量化/合并原子）下 Pe 单调不减、Gamma 规律变化的成对用例。
3. 组件化封装。

## R6-12｜第 6 章逻辑 52×4 历史可追溯性、方法输出/见证与扩展全域合法范围

基本新建（数据工程）：
- 52 模型身份台账（16 微模型 YAML/oracle 在冻结 E2 `logic/models/M01..M16`，36 生成点标 RECONSTRUCTED）。
- 208 条历史状态逐条追溯（状态/模型 SHA/来源），与 E3-04 引擎新结果的对照接口（引擎未实现前留 NOT_EXECUTED）。
- "扩展全域合法范围"声明绑定 E3-05 签署（未签署前一律 DOMAIN_PENDING）。

## R6-13｜第 6 章 32 工况/48 候选/5000 来源及概率数据归属、区间与数据对账

部分存在：
- `runs/domain_audit/pyscrew_population_facts.json`（5000/2500/25 类×200/配对/4307+693 实测）
- 冻结 `scope/pyscrew_raw_manifest.csv`、E1 的 `comparison_candidates_48.csv`

缺口：
1. 历史 1,413 vs 1,421 ID 对账（旧 32 工况子集 ID 与新 5,000 manifest 的映射与差异清单）。
2. 48 候选的逐条来源登记（24×2，CANDIDATE 状态，不作证书）。
3. 组件化封装与对账测试。

## 施工顺序建议

1. R6-08 组件化（复用最多，最快）→ 2. R6-10 独立参考 → 3. R6-11 成对用例 → 4. R6-13 对账 → 5. R6-09 积分器（数学最重）→ 6. R6-12 台账（依赖 E3-04 接口，最后做）。
