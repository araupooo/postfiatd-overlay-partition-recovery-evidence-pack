# Decision Memo — Partition and Recovery Findings

Primary sources only. Each paragraph cites the source it rests on;
the full pin list is in `docs/SOURCES.md` and the claim index in
`docs/CLAIMS.md`.

## 1. The testnet survives losing 8 validators, and no partition of one shared list can fork it

Source: `data/partition_summary.json` (model from the vendored list
`data/testnet_vl.json`, seq 31, 25 validators) and the quorum formula
in postfiatd `0085a1ff885d6a446369cf73a4430f75af22be55`,
`src/xrpld/app/misc/detail/ValidatorList.cpp:1933-1934`.

With 25 validators and quorum 17, the network keeps validating
until 8 validators are lost (17 remain). A partition needs a
17-validator side to keep going; any split whose largest side has
16 or fewer validators halts both sides. No split can fork: a fork
needs both sides at quorum, 34 validators, and only 25 exist. The
live `validation_quorum` of 17 (`data/close_sample.json`) matches
the model exactly. Decision: for the testnet as configured, crash
tolerance is 8 and partition tolerance is "the big side survives
down to 17". Any operational runbook should treat 17 as the red
line, not 13 (a majority) — a 13/12 split is a total halt, not a
degraded mode.

## 2. The 67% quorum buys liveness at the price of the fork-safety certificate

Source: arXiv:1802.07242, Theorem 8 (verified verbatim), and the
derivation in `docs/PARTITION_MODEL.md` §4.

Theorem 8 certifies fork safety at 80% quorum with worst-case
faults only if pairwise UNL overlap is at least 23 of 25. At 67%
quorum the same theorem certifies nothing under worst-case faults:
the required overlap (28.5) exceeds the UNL size. The 21-of-25
figure quoted for 67% is the zero-Byzantine bound — it holds only
if no validator in the overlap is faulty — and the in-code comment's
"pi + pj < .33*ni" bound carries the same hidden assumption
(R-01). The 67% rule is a liveness choice: it lets the network
survive 8 losses instead of 5, and it lets a 17-validator side keep
going where 80% would need 20. Decision: keep 67% for testnet, but
do not quote Theorem 8 margins for it. Fork safety at 67% rests on
UNL uniformity (every validator using the same published list),
which the public RPC cannot verify per validator. The mainnet
revert to 80% — which the code comment itself prescribes — should
be treated as a fork-safety gate, not a cosmetic change, because
80% is the quorum at which the theorem starts certifying anything
under worst-case faults.

## 3. The negative UNL is live and is the only quorum-lowering path — but it cannot rescue a stalled side

Source: `data/features_sample.json` (NegativeUNL amendment enabled),
`src/xrpld/app/misc/NegativeUNLVote.h`, and the quorum formula.

The amendment is enabled on the testnet, so the recovery path is
real, not theoretical. At most 7 validators (25%) can be listed;
after full listing the quorum floor is 15, so a validating 17-side
can absorb 2 further losses. Detection takes at least one flag
period (~768 s at the measured close step) with under 50%
validations before a missing validator can even become a candidate,
and voting happens on voting ledgers. But the votes ride inside
ledgers: a side below quorum cannot close ledgers and therefore
cannot vote to lower its own quorum. Decision: the negative UNL is
a margin-extender for a surviving side, not a rescue mechanism for
a stalled one. A runbook for a sub-quorum side must heal the
partition first (restore connectivity to ≥ 17 validators) and only
then expect the negative UNL to do anything. Any plan that assumes
"the negative UNL will fix a 16-validator side" is wrong (R-03).

## 4. Peer tracking is slow to call a partition what it is

Source: `src/xrpld/overlay/detail/Tuning.h:32,36`,
`src/xrpld/overlay/detail/PeerImp.cpp:2104,2110`, and the measured
close step (3.0000 s).

A peer up to ~72 s behind still counts as converged, and is only
marked diverged after falling ~384 s (~6.4 min) behind. The idle
sweep runs every 4 s, so dead peers are reaped quickly once
identified, but the diverged flag itself takes minutes. Decision:
do not use the converged/diverged flags as a partition detector —
by the time a peer is flagged diverged, the partition is already
~6 minutes old and the negative-UNL detection clock has barely
started. Partition detection should watch validation counts per
flag period directly (the same signal the negative-UNL vote uses),
not the overlay tracking flags (R-04).

## 5. Recovery after healing is bounded by reply caps, not by reconnect speed

Source: `src/xrpld/overlay/detail/Tuning.h:39,42,61`,
`src/xrpld/overlay/detail/PeerImp.cpp:1535,3541,3560`, and
`src/xrpld/peerfinder/detail/Tuning.h`.

Reconnection itself is fast — first attempts within ~10 s, Fibonacci
backoff to 55 s, 20 simultaneous attempts — but ledger catch-up is
capped at 8,192 nodes per reply (12,288 hard) and 3 query levels
deep. A side that stalled for hours has a long ledger gap to fetch
in small replies. Decision: post-healing recovery time is dominated
by ledger fetch, not by peer reconnection. Drill D-04 covers UNL
re-sync (digest-verified); it does not cover ledger catch-up, which
is the larger unknown (U-06, R-05).
