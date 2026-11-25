# Remediation Guidance

Severity scale: HIGH = exploitable or data-exposing now; MEDIUM =
weakens a security boundary or mainnet readiness; LOW = hygiene or
observability; INFO = context, no action required.

## R-01 — MEDIUM: correct the quorum comment's fork-safety claim

[SIMULATED] The comment at
`src/xrpld/app/misc/detail/ValidatorList.cpp:1898-1932` quotes
Theorem 8 correctly and then derives "pi + pj < .33*ni" — a bound
that follows only if ti,j = 0 (zero Byzantine faults), while the
same comment states ti ≤ .33ni. Under the stated fault model,
Theorem 8 certifies nothing at 67% quorum (required overlap 28.5
> 25). The 21-of-25 minimum overlap quoted for 67% is the
zero-Byzantine bound. An operator reading the comment would believe
67% quorum tolerates up to 8 differing validators between UNLs
with full Byzantine tolerance; it does not.

Guidance: rewrite the comment to state the bound honestly — at 67%,
Theorem 8 gives no certificate under worst-case faults, and the
21/25 figure assumes zero Byzantine faults in the overlap. Keep
the mainnet-revert note (the comment already says mainnet "should
be reverted to 80%") and add that the revert is what restores the
Theorem 8 certificate (23/25 overlap at worst-case faults).
Re-verify after the fix: the comment's algebra should match the
derivation in `docs/PARTITION_MODEL.md` §4.2
(pi + pj < 2q − 2t − n).

## R-02 — MEDIUM: do not treat UNL uniformity as verified

[SIMULATED] Fork safety at 67% rests on every validator using the
same published list (see `docs/PARTITION_MODEL.md` §4.4). The
per-validator UNL contents are not observable from the public RPC,
and a single publisher (`postfiat.org`) supplies the list. If any
validator runs a different list, the Theorem 8 margins apply — and
at 67% those margins are vacuous under worst-case faults.

Guidance: add an operational check that compares the validator
list each validator reports (e.g. via the `validators` RPC or the
`server_info` validation quorum) against the published list, and
alert on any divergence. Until such a check exists, treat "all
validators share one UNL" as an assumption (A-1), not a fact, in
every fork-safety statement. For mainnet, require more than one
independent list publisher before relying on uniformity.

## R-03 — MEDIUM: document that a sub-quorum side cannot self-rescue via the negative UNL

[SIMULATED] A side with 16 or fewer validators cannot close
ledgers, so it cannot vote UNLModify transactions to lower its own
quorum (the votes ride inside ledgers). The negative UNL can only
help a side that is already validating (quorum 17 → 15 after full
listing). A runbook that assumes otherwise will wait forever: the
side stalls, no votes happen, and the quorum never drops.

Guidance: write the recovery runbook around healing first —
restore connectivity until ≥ 17 validators can see each other —
and only then rely on negative-UNL listing to absorb further
losses. Drill D-04 demonstrates the full sequence; add the D-04
checks to CI as a regression test for the quorum arithmetic
(it already runs in `reproduce.sh`).

## R-04 — LOW: do not use converged/diverged flags as a partition detector

[MEASURED] A peer counts as converged while within 24 ledgers
(~72 s) and is only marked diverged after falling more than 128
ledgers (~384 s) behind (`PeerImp.cpp:2104,2110`). The 24–128
ledger band is a grey zone where a peer is neither.

Guidance: for partition detection, watch per-validator validation
counts per flag period — the same signal the negative-UNL vote
uses (disable below 128 of 256 validations) — instead of the
overlay tracking flags. Consider logging a warning when a peer
crosses 24 ledgers behind, rather than waiting for the 128-ledger
diverged mark.

## R-05 — LOW: plan ledger catch-up capacity for long partitions

[MEASURED] Ledger-data replies are capped at 8,192 nodes (soft) /
12,288 (hard) with a maximum query depth of 3
(`PeerImp.cpp:1535,3541,3560`; `Tuning.h:39,42,61`). A side that
stalled for hours has a long gap to fetch in small replies.

Guidance: after healing, measure actual catch-up time for a
stalled node (ledgers behind ÷ fetch rate) before declaring the
partition recovered. If catch-up is the bottleneck, consider
raising the soft cap or parallelizing ledger fetch across peers.
This pack measures the caps, not the catch-up rate (U-06).

## R-06 — INFO: reconnection pacing is adequate for healing

[MEASURED] After a partition heals, reconnection is paced by
`secondsPerConnect` 10 s, Fibonacci backoff to 55 s,
`maxConnectAttempts` 20, and 10 outbound peers at defaults
(`peerfinder/detail/Tuning.h`). Nothing here blocks recovery; the
bottlenecks are the quorum (R-03) and ledger catch-up (R-05), not
peer reconnection. No change recommended.
