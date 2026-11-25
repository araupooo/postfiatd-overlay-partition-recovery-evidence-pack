# Failure Modes

Severity follows `docs/REMEDIATION.md` (R-01–R-06).

## F-01 In-code comment overstates the 67% fork-safety margin

(Measured in the source; remediation R-01, MEDIUM.) The comment at
`ValidatorList.cpp:1898-1932` derives "pi + pj < .33*ni" from
Theorem 8, but the derivation only holds if ti,j = 0. Under the
fault model the comment itself states (ti ≤ .33ni), Theorem 8
requires overlap > 28.5 for a 25-UNL — impossible. An operator
relying on the comment would overestimate fork safety by a wide
margin. The code (`calculateQuorum`) is unaffected.

## F-02 UNL divergence between validators

(Simulated, C-01/S-04; remediation R-02, MEDIUM.) If validators
run different lists, the overlap bounds apply — and at 67% they are
vacuous under worst-case faults. The single published list is also
a single point of trust: a compromised or stale publisher list
propagates to every validator that fetches it. Detection: compare
each validator's reported list/quorum against the published list.
Recovery: re-publish a correct list and restart affected validators
with it; there is no in-protocol repair for divergent UNLs.

## F-03 Partition with a sub-quorum side

(Simulated, S-02/S-03/S-09; remediation R-03, MEDIUM.) A split
whose largest side has 16 or fewer validators halts both sides.
The stalled side cannot vote to lower its quorum, so it cannot
self-rescue. Detection: validation counts per flag period (a
validator below 128 of 256 validations is a disable candidate).
Recovery: restore connectivity until ≥ 17 validators can see each
other, then let the negative UNL absorb further losses (quorum
floor 15). Drill D-04 covers the sequence.

## F-04 Slow divergence detection

(Measured, C-10; remediation R-04, LOW.) A peer is only marked
diverged after falling more than 128 ledgers (~384 s) behind, and
counts as converged while within 24 ledgers (~72 s). A partition
is ~6 minutes old before the overlay flags it. Detection: watch
validation counts per flag period instead. Recovery: none needed
by the detector; the fix is in what is watched.

## F-05 Slow ledger catch-up after healing

(Measured, C-12; remediation R-05, LOW.) Ledger-data replies are
capped at 8,192 nodes (soft) / 12,288 (hard), 3 query levels deep.
A node that stalled for hours fetches its gap in many small
replies. Detection: measure catch-up rate after healing.
Recovery: parallelize fetch across peers or raise the soft cap;
do not assume healing equals recovery.

## F-06 Validator list fetch failure

(Measured, C-01.) The published list is fetched once and vendored
in `data/testnet_vl.json`. If `postfiat.org` is unreachable or the
blob is malformed, `scripts/partition_model.py --live` fails loudly
and the replay path still works from the vendored file. The model
is only as fresh as its last fetch; re-fetch before quoting the
sequence number.

## F-07 RPC endpoint drops connections

(Measured, C-03/C-13.) The public RPC intermittently closes
connections without a response (observed during the close-sample
fetch: several `RemoteDisconnected` errors before retries
succeeded). `scripts/rpc_client.py` retries up to 4 times with
exponential backoff. If the endpoint is down entirely, the
`--live` path fails and the replay path still works.

## F-08 Digest mismatch in the pack

(Simulated, S-11; drill D-03.) A tampered pack file is detected by
`verify_digests.sh` (exit non-zero, names the file). Recovery:
re-clone the repository and re-run `bash reproduce.sh`; do not
edit files in place and re-run the digest check expecting it to
pass.

## F-09 Reconnection backoff after healing

(Measured, C-08; remediation R-06, INFO.) After a partition heals,
reconnection attempts back off along 1, 1, 2, 3, 5, 8, 13, 21, 34,
55 s per address, with at most 20 simultaneous attempts. A node
whose far-side addresses are all in backoff waits up to 55 s
before retrying one of them. This is pacing, not a failure: the
first attempts happen within ~10 s.
