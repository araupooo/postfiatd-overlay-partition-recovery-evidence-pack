# Claim-to-Evidence Index

Labels: [MEASURED] observed on the live testnet or read from the
pinned source, with the script and vendored output that produced it;
[SIMULATED] produced by a local model, drill, or analytic derivation
from the pinned source — not observed live; [UNSUPPORTED] cannot be
established from the public sources used here. Line numbers are from
the vendored files as committed (verify with `grep -n`); JSON keys
are given alongside for stability.

## Measured claims

| # | Claim | Evidence (script → output file:line) | Primary source |
|---|---|---|---|
| C-01 | Validator list: sequence 31, 25 validators, 25 unique keys, 0 duplicates, manifest for every entry; effective Ripple-epoch 848866298 (2026-11-24T20:11:38Z), expiration 892052157 (2028-04-07) | `scripts/partition_model.py` → `data/partition_summary.json:421,424` (`validator_list.*`); raw `data/testnet_vl.json` | `https://postfiat.org/testnet_vl.json`, fetched 2026-11-25 18:15 UTC |
| C-02 | Quorum 17 under the 67% rule, 20 under the upstream 80% rule, floor 15 | `scripts/partition_model.py` → `data/partition_summary.json:283,284,286` (`quorum.*`) | postfiatd `0085a1ff885d6a446369cf73a4430f75af22be55`, `src/xrpld/app/misc/detail/ValidatorList.cpp:1933-1934` |
| C-03 | Live `validation_quorum` is 17 and matches the 67% model | `scripts/partition_model.py` → `data/partition_summary.json:84,88` (`live_corroboration.*`) | `https://rpc.testnet.postfiat.org` (`server_info`), fetched 2026-11-25 18:24 UTC; raw `data/close_sample.json` |
| C-04 | `calculateQuorum` takes a `seenSize` parameter and never uses it: the quorum does not shrink when validators stop being seen | `grep -n seenSize` on the pinned checkout (only occurrence is the signature, `ValidatorList.cpp:1845-1848`) | postfiatd `0085a1ff…`, `src/xrpld/app/misc/detail/ValidatorList.cpp:1845-1934` |
| C-05 | The NegativeUNL amendment is enabled on the testnet (amendment `B4E4F5D2D6FB84DF7399960A732309C9FD530EAE5941838160042833625A6076`, enabled: true, supported: true) | `scripts/partition_model.py` → `data/partition_summary.json:91` (`negative_unl_amendment.*`); raw `data/features_sample.json` (101 amendments) | `https://rpc.testnet.postfiat.org` (`feature`), fetched 2026-11-25 18:25 UTC |
| C-06 | Negative-UNL voting thresholds: disable below 50% of a flag period (score < 128 of 256 validations), re-enable above 80% (score > 204, minimum qualifying 205 of 256), local node votes only above 90% (score > 230, minimum qualifying 231 of 256), at most 25% of the UNL listed, flag period 256 ledgers | Source pin only | postfiatd `0085a1ff…`, `src/xrpld/app/misc/NegativeUNLVote.h:56-57,62-63,68-69,78`, `src/xrpld/app/misc/NegativeUNLVote.cpp:221,231,282,292`; `src/xrpld/app/ledger/Ledger.h:426` |
| C-07 | Overlay tuning: convergedLedgerLimit 24, divergedLedgerLimit 128, softMaxReplyNodes 8192, hardMaxReplyNodes 12288, sendqIntervals 4, dropSendQueue 192, targetSendQueue 128, checkIdlePeers 4, maxQueryDepth 3 | `scripts/overlay_audit.py` → `data/overlay_audit.json` (`overlay_tuning.rows`) | postfiatd `0085a1ff…`, `src/xrpld/overlay/detail/Tuning.h:32,36,39,42,46,49,52,58,61` |
| C-08 | Peerfinder tuning: secondsPerConnect 10, maxConnectAttempts 20, outPercent 15, minOutCount 10, defaultMaxPeers 21, maxRedirects 30, backoff 1,1,2,3,5,8,13,21,34,55, bootcacheSize 1000, maxHops 6, secondsPerMessage 151, liveCacheSecondsToLive 30, recentAttemptDuration 60 | `scripts/overlay_audit.py` → `data/overlay_audit.json` (`peerfinder_tuning.rows`) | postfiatd `0085a1ff…`, `src/xrpld/peerfinder/detail/Tuning.h:40,44,52,59,63,70,79-80,90,110,124,128,132` |
| C-09 | Untrusted-manifest bound 1000, overridable via `[overlay] max_untrusted_count` | `scripts/overlay_audit.py` → `data/overlay_audit.json:20` (`manifest_bounds.rows`) | postfiatd `0085a1ff…`, `src/xrpld/app/misc/Manifest.h:279,283,287` |
| C-10 | Peer tracking: converged if within 24 ledgers, diverged if more than 128 behind | Source pin only | postfiatd `0085a1ff…`, `src/xrpld/overlay/detail/PeerImp.cpp:2104,2110` |
| C-11 | Idle-peer sweep runs every 4th one-second timer tick (every 4 s) | Source pin only | postfiatd `0085a1ff…`, `src/xrpld/overlay/detail/OverlayImpl.cpp:111-112` |
| C-12 | Ledger-data reply caps: soft 8192, hard 12288 nodes; requests above the hard cap are rejected | Source pin only | postfiatd `0085a1ff…`, `src/xrpld/overlay/detail/PeerImp.cpp:1535,3541,3560` |
| C-13 | Close-step mean 3.0000 s (n = 10 diffs: 8, 1, 1, 1, 7, 1, 1, 8, 1, 1; 10 s resolution) | `scripts/partition_model.py` → `data/partition_summary.json:81,291` (`close_step_mean_s`); raw `data/close_sample.json` | `https://rpc.testnet.postfiat.org` (`ledger`, 11 headers), fetched 2026-11-25 18:24 UTC |
| C-14 | Amendment threshold 67/100, held two weeks | Source pin only | postfiatd `0085a1ff…`, `include/xrpl/protocol/SystemParameters.h:85,87-88` |
| C-15 | Theorem 8 (arXiv:1802.07242): "XRP LCP guarantees fork safety if Oi,j > nj/2 + ni − qi + ti,j for every pair of nodes"; the condition is sufficient, not necessary; at 80% quorums and 20% faults it requires roughly >90% UNL overlap | Paper text verified against the arXiv HTML version, section 4.1 | arXiv:1802.07242 (Chase & MacBrough), Theorem 8 and the note following it |

## Simulated claims

| # | Claim | Evidence (script → output file:line) | Primary source |
|---|---|---|---|
| S-01 | Maximum tolerable crash loss: 8 validators @67%, 5 @80% | `scripts/partition_model.py` → `data/partition_summary.json:8,9` (`crash_loss.*`) | Quorum formula C-02 applied to the measured list C-01 |
| S-02 | Minimum survivable partition: 17 validators (68%) @67%, 20 (80%) @80% | `scripts/partition_model.py` → `data/partition_summary.json:117,118` (`partitions.*`) | Quorum formula C-02; partition table in the same file |
| S-03 | No partition of a single shared UNL can fork (needs both sides ≥ quorum: 34 > 25 @67%, 40 > 25 @80%); splits 17/8 and larger continue on the big side, splits 16/9 and smaller halt both sides | `scripts/partition_model.py` → `data/partition_summary.json:114` (`partitions.fork_from_partition_alone_67pct`) and `partitions.table` | Quorum formula C-02; model derivation in `docs/PARTITION_MODEL.md` §3 |
| S-04 | Overlap tables for every tolerated fault count t: @67% t=0 → min overlap 21 (diff ≤ 8), t=4 → identical UNLs only, t≥5 → Theorem 8 certifies nothing; @80% t=5 → min overlap 23 (diff ≤ 4) | `scripts/partition_model.py` → `data/partition_summary.json` (`unl_overlap_theorem8.table_67pct`, `table_80pct`) | Theorem 8 C-15; derivation `pi + pj < 2q − 2t − n` in `docs/PARTITION_MODEL.md` §4.2 |
| S-05 | At 67% quorum with worst-case faults (t = 8), Theorem 8 requires overlap > 28.5 — impossible for a 25-UNL; it certifies nothing, not even identical UNLs | `scripts/partition_model.py` → `data/partition_summary.json:410` (`unl_overlap_theorem8.vacuity_67pct`) | Theorem 8 C-15; bound derivation §4.2 |
| S-06 | The in-code comment's "pi + pj < .33*ni" bound follows only if ti,j = 0 (zero Byzantine faults); under the stated fault model ti ≤ .33ni the derivation gives pi + pj < −0.32ni | `docs/PARTITION_MODEL.md` §4.3 (algebra shown step by step) | postfiatd `0085a1ff…`, `ValidatorList.cpp:1898-1932` (comment text) vs Theorem 8 C-15 |
| S-07 | With identical UNLs, no fork is possible at 67% even with t = 8: two quorums of 17 from 25 validators intersect in ≥ 9 validators, at most 8 Byzantine, so ≥ 1 honest validator sits in every quorum intersection | `docs/PARTITION_MODEL.md` §4.4 (direct argument; Theorem 8 is sufficient, not necessary) | Quorum definition C-02; Lemma 6 mechanism, arXiv:1802.07242 §4.1 |
| S-08 | Negative UNL: at most 7 validators listed (25% cap); after full listing the quorum floor is 15; detection takes at least one flag period, ~768 s at the measured close step | `scripts/partition_model.py` → `data/partition_summary.json:101,102,106` (`negative_unl_recovery.*`) | Negative-UNL rules C-06; quorum formula C-02; close step C-13 |
| S-09 | A side below quorum cannot vote to lower its own quorum: UNLModify votes ride inside ledgers, and a side that cannot close ledgers cannot vote | `scripts/recovery_drills.py` → `outputs/recovery_drills.log` (D-04c) | postfiatd `0085a1ff…`, `src/xrpld/app/consensus/RCLConsensus.cpp:379-385` (voting-ledger gate + `nUnlVote_.doVoting`); quorum formula C-02 |
| S-10 | Time conversions at the measured close step: converged below ~72 s, diverged above ~384 s, flag period ~768 s | `scripts/overlay_audit.py` → `data/overlay_audit.json:6,8,11` (`derived_time_conversions`) | Tuning limits C-07; flag interval C-06; close step C-13 |
| S-11 | Recovery drills D-01–D-04 all pass (0 failed): retry-after-failure, resume-with-gap-filling, digest-mismatch, post-partition UNL re-sync | `scripts/recovery_drills.py` → `outputs/recovery_drills.log` (unedited) | Local fixtures only; see `docs/FAILURE_MODES.md` |
| S-12 | Liveness: a single agreed-upon UNL plus leaves cannot get stuck (Theorem 11; here q = 17 = 25 − floor(24/3)); conversely a network can get stuck even with 99% UNL overlap and no Byzantine faults once UNLs diverge (Example 9) | Paper text verified against the arXiv HTML version, §4.2 | arXiv:1802.07242, Theorem 11 and Example 9 |

## Unsupported claims

| # | Claim | Why it cannot be established here |
|---|---|---|
| U-01 | Every validator uses the published list | Per-validator UNL contents are not observable from the public RPC (assumption A-1). The live quorum of 17 is consistent with a 25-UNL under the 67% rule, but does not prove uniformity. |
| U-02 | Behavior under real load or real Byzantine faults | No validator was taken down and no partition was induced on the live network; all loss/partition figures are analytic. |
| U-03 | Any claim about mainnet | All measurements are testnet (network_id 2025); mainnet does not exist yet and the 67% → 80% quorum revert is unexecuted. |
| U-04 | That any tuning threshold has ever triggered on the testnet | No peer was observed going idle, diverging, or being disconnected; no send queue was observed filling; no reply cap was observed binding. |
| U-05 | That negative-UNL voting has ever run on the testnet | The amendment is enabled (C-05), but no UNLModify transaction was observed and no validator is currently listed. |
| U-06 | Recovery timing after a real partition | No real partition occurred during this work; the ~768 s detection figure is a lower bound from the code, not a measurement. |
| U-07 | That the 21 peers in `server_info` use defaultMaxPeers | The peer count is consistent with the default (21) but the RPC does not report per-peer configuration. |
