# R6-E3 操作章程（superpowers 7.0.0 + 大厂工作流规范接入）

本章程把用户本机部署的 superpowers 技能集与大厂工程规范映射为 E3 项目的强制操作规则。所有主对话决策与子 Agent 派遣 prompt 均须遵守；与本项目合同（R6_E3 v3）冲突时以合同为准。

## 1. superpowers 映射

| 技能 | E3 强制规则 |
|---|---|
| subagent-driven-development | 每个实现任务派**新**子 Agent，prompt 自带全部所需上下文，不继承会话历史；任务后做规格符合性 + 代码质量双评审；分支级终审在收尾做。主对话只做协调。 |
| dispatching-parallel-agents | ≥2 个相互独立的问题域必须并行派遣（如 TINA 重放与 R604 重建），写范围显式隔离并记入 team task。 |
| verification-before-completion | **铁律：无新鲜验证证据不得声称完成。** 任何 PASS/通过声明必须附本次运行的命令、退出码与输出路径；Actions 结果以下载的 artifact 为准。 |
| systematic-debugging | 任何 bug/测试失败先定位根因（文件:行 + 可证伪假设 + 仪器验证），禁止症状补丁；三次假设失败即上报。 |
| test-driven-development | 新特性/修复先写失败测试再实现；变异测试（源码级 mutant）作为 TDD 的强化形式保留。例外需在任务记录中声明。 |
| writing-plans | 多步任务计划写入 `docs/superpowers/plans/YYYY-MM-DD-<名称>.md`，含文件清单、接口、每任务验收测试；不允许 TBD 占位。 |
| executing-plans | 计划执行不停顿请示；冲突/歧义/计划缺陷按 `Ruling: <决定> — <理由> — <错误代价>` 记入台账继续推进。只有合同要求的理论签署与用户授权两类门禁可停。 |
| using-git-worktrees | 重实验在独立仓库 `Lucas-cs11/R6-E3-experiments` 的 Actions 上运行；本地工作区只做轻量验证与证据归档。 |
| requesting/receiving-code-review | 合并 main 前按五轴（正确性/可读性/架构/安全/性能）评审；子 Agent 产出视同外部 PR。 |
| finishing-a-development-branch | 收尾=证据 ZIP + 台账 + 未决清单，不是"代码写完"。 |

## 2. 大厂规范映射

| 规范 | E3 强制规则 |
|---|---|
| karpathy-guidelines | 编码前显式列出假设；外科手术式修改（不顺手重构）；可验证成功标准先行；困惑摆上台面不隐藏。 |
| code-review-and-quality | 任何改动合并前过质量门；评审结论分 safe_auto / gated_auto / manual / advisory 四级。 |
| security-and-hardening | 一切外部输入（冻结 ZIP、artifact、账本、JSONL）视为不可信：先验哈希与 schema，再解析；篡改负测为必备件。 |
| api-and-interface-design | oracle/主体/验收器之间接口稳定、难以误用（如 `replay(root, pins=...)` 的 pins 只用于测试注入）；接口变更须同步全部调用方与测试。 |
| pua-en（PIP） | 三不可协商：穷尽选项才准说"不能"；先调查（附已查证据）再提问；端到端 Ownership（修 bug 必查同类、改配置必验相关项）。禁止把"环境问题"当结论而不验证。 |

## 3. 与既有门禁的关系

- 本章程不放宽 R6_E3 v3 合同的任何门槛；它收紧工程纪律。
- 理论签署（E3-05）与用户授权（全量 runner 分钟）仍是仅有的两类合法停顿点。
- 所有 Ruling 与评审记录进入 `reports/` 台账，随最终证据 ZIP 交付。
