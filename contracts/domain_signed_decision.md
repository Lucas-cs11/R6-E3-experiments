# Signed research-domain decision

Ruling: `MATH_SIGNED_SCOPE`, A scheme approved with limitations, seed=0 only.

- Candidates: 143,360; valid 107,520; invalid 35,840.
- Minimum task records: 430,080 = 107,520 × 4 methods.
- `fault_locations` is an upper bound saturated by used machines, not an exact fault count.
- Saturated configurations retained in A: 3,840.
- Canonical semantic network contents: 85,024, hashes are not behavioral equivalence classes.
- Declared ledger A: 104,052 BOUNDED + 3,468 TIMEOUT.
- Query-reconciled A: 104,212 boundedness-proved + 3,308 boundedness-undetermined.
- Auxiliary B: 103,680 configurations; declared 100,212 + 3,468; query-reconciled 100,372 + 3,308.
- Historical 15 seeds / param_slice:3 / 36,450 remain PROVENANCE_UNRESOLVED.

References:

- `reports/01_研究域_E3-05_主理论裁定附录.md`, SHA-256 `753e56a11a7f54e4fffb4fb1e0f1628f7b43932d7f3d0b7097c0f47d0d4b9a46`.
- `reports/decision_trace.csv`, SHA-256 `668bedee62d5dbdbae458bd4be83e06f716648dab0b53767740a0260b3df2309`.
- `contracts/frozen_full_domain.json`, SHA-256 `c3d3f966f4e16e40f94a56e82796b9b0ae879e58fde76cc52ea92324c5010c9c`.
- `contracts/domain_index.csv`, SHA-256 `b39aad320ab11a78b92da19c1049e370133c22d7550104fc453df9a4bce29332`.

This is a mathematical scope decision, not evidence that the 430,080 runs have
completed.  B is an auxiliary sensitivity view and does not replace A.
