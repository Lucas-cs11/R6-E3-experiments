# E3-10 stage-3: 32-condition certificate audit

## Result

- Historical structural outcomes: 3 PASS, 25 FAIL, 3 UNRESOLVED, 1 INSUFFICIENT_DATA.
- New validity: 0 REAUTHENTICATED, 31 PARTIAL, 1 NOT_REAUTHENTICATED.
- Numeric interval and threshold-decision replay matched: 31/32 cases.
- Full model/path/integration replay completed: 0/32 cases.

The three historical PASS cases remain PARTIAL, not new PASS.  Exact Pe/Gamma
interval agreement and threshold-decision agreement do not prove completion
semantics.  The frozen sources do not contain the original LSTPN engine bytes
or raw integration traces, and archived stops include TIME_BUDGET/SPLIT_BUDGET.

## NOT_REAUTHENTICATED

303_right

303_right is NI in the historical certificate and has no reauthentication path.
It is retained rather than removed or backfilled.  Every other case retains its
numeric replay result, the original stop state, and the engine/path/log gaps.
