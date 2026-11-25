# PFTL Overlay Partition-Recovery Evidence Pack

An assessment of postfiatd overlay resilience to network partitions
and validator loss, and of the recovery path after a partition heals.
Built from the measured 25-validator testnet list and the pinned
postfiatd source (commit
`0085a1ff885d6a446369cf73a4430f75af22be55`, release 1.0.9).

Every substantive claim is labelled [MEASURED] (observed on the live
testnet or read from the pinned source, with the script and raw output
that produced it), [SIMULATED] (produced by a local model or drill, or
derived analytically from the pinned source — not observed live), or
[UNSUPPORTED] (cannot be established from the public sources used
here). Every claim is mapped to its evidence in `docs/CLAIMS.md`.

## Headline results

[MEASURED] Quorum is 17 of 25 under the 67% rule (20 under the
upstream 80% rule), confirmed live by `server_info`
(`validation_quorum` 17). The quorum does not shrink when validators
stop being seen — `calculateQuorum` takes a `seenSize` parameter and
never uses it — so a partition does not lower the quorum on its own.

[SIMULATED] A partition needs a 17-validator side to keep validating
(68% of the network); any split whose largest side has 16 or fewer
validators halts both sides. No partition of a single shared UNL can
fork: a fork needs both sides at quorum, i.e. 34 validators, but only
25 exist. Crash loss is survivable up to 8 validators at 67% (5 at
80%).

[SIMULATED] Theorem 8 (arXiv:1802.07242) certifies fork safety at 80%
quorum with worst-case faults only if pairwise UNL overlap is at least
23 of 25. At 67% quorum the same theorem certifies nothing under
worst-case faults — the required overlap exceeds the UNL size. The
21-of-25 figure quoted for 67% in earlier work is the zero-Byzantine
bound: it holds only if no validator in the overlap is faulty. The
in-code comment's "pi + pj < .33*ni" bound has the same hidden
assumption. See `docs/PARTITION_MODEL.md` for the derivation and
`docs/REMEDIATION.md` R-01.

[MEASURED] The NegativeUNL amendment is enabled on the testnet
(`feature` RPC, amendment
`B4E4F5D2D6FB84DF7399960A732309C9FD530EAE5941838160042833625A6076`).
At most 7 validators (25% of the UNL) can be listed; after full
listing the quorum floor is 15. Detection takes at least one flag
period (256 ledgers, ~768 s at the measured close step) with under
50% validations. A side below quorum cannot vote to lower its own
quorum — it must heal first (R-03).

[MEASURED] Peer tracking: a peer within 24 ledgers (~72 s) counts as
converged; a peer is only marked diverged after falling more than 128
ledgers (~384 s) behind. Idle peers are swept every 4 s. Ledger-data
replies are capped at 8,192 nodes (soft) / 12,288 (hard).

## How to run it

```sh
bash reproduce.sh
```

Python 3.9+ standard library only; no network at run time — the
scripts replay the vendored `data/` captures. Each script prints
PASS/FAIL and writes its unedited stdout to `outputs/<script>.log`.
The runner exits non-zero if any script fails and prints a final
`ALL CHECKS PASSED` / `FAILED` summary, then `verify_digests.sh`
checks the SHA-256 manifest.

To re-capture fresh live inputs instead of replaying the vendored
ones, see `docs/REPRODUCTION.md` (command:
`python3 scripts/partition_model.py --live`).

## File map

| Path | Contents |
|---|---|
| `scripts/rpc_client.py` | Shared read-only JSON-RPC client (retries, backoff) |
| `scripts/partition_model.py` | M-01: quorum / loss / partition / overlap model |
| `scripts/overlay_audit.py` | M-02: overlay + peerfinder + manifest parameter audit |
| `scripts/recovery_drills.py` | M-04: four recovery drills with unedited logs |
| `scripts/run_all.sh` | Runs every check, captures outputs/*.log |
| `data/testnet_vl.json` | Published validator list, fetched 2026-11-25 18:15 UTC |
| `data/close_sample.json` | server_info + 11 ledger headers, fetched 2026-11-25 18:24 UTC |
| `data/features_sample.json` | feature RPC output (101 amendments), fetched 2026-11-25 18:25 UTC |
| `data/partition_summary.json` | M-01 model output |
| `data/overlay_audit.json` | M-02 audit output |
| `data/postfiatd_pin.json` | Pinned commit + blob SHAs + line pins |
| `docs/PARTITION_MODEL.md` | The model, its derivation, and its limits |
| `docs/OVERLAY_AUDIT.md` | The parameter audit, configured vs measured |
| `docs/CLAIMS.md` | Claim-to-evidence index |
| `docs/DECISION_MEMO.md` | Decisions the evidence supports |
| `docs/REMEDIATION.md` | Findings R-01–R-06 with guidance |
| `docs/FAILURE_MODES.md` | What can go wrong, and what each drill covers |
| `docs/REPRODUCTION.md` | How to reproduce, re-fetch, and re-verify citations |
| `docs/SOURCES.md` | Every primary source with fetch/checkout details |
