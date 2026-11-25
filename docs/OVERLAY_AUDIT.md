# Overlay Parameter Audit — Configured vs Measured

Source of every value: the pinned postfiatd commit
`0085a1ff885d6a446369cf73a4430f75af22be55`, verified by `grep -n`
on a local checkout. The full machine-readable table is
`data/overlay_audit.json` (produced by `scripts/overlay_audit.py`).

The audit separates three kinds of statement, and they must not be
confused:

- **Configured**: a constant in the pinned source. It says what the
  code will do when the condition arises. It does not say the
  condition has ever arisen.
- **Derived**: arithmetic on a configured constant and the measured
  close step (3.0000 s, fresh 11-header sample). Order-of-magnitude.
- **Measured**: a live observation from `data/close_sample.json`.

No constant in this audit has ever been observed triggering on the
testnet in this pack. The testnet is idle (0.47 transactions per
sampled ledger in the 24 h window measured 2026-11-24 → 25) and no
partition, divergence, or idle-peer event was induced or observed.

## 1. Overlay tuning — `src/xrpld/overlay/detail/Tuning.h`

| Constant | Value | Line | Use | What it means |
|---|---|---|---|---|
| convergedLedgerLimit | 24 | 32 | `PeerImp.cpp:2104` | A peer within 24 ledgers of the validation's counts as converged. Derived: < ~72 s of lag. |
| divergedLedgerLimit | 128 | 36 | `PeerImp.cpp:2110` | A peer more than 128 ledgers behind is marked diverged. Derived: > ~384 s (~6.4 min) of lag. |
| softMaxReplyNodes | 8192 | 39 | `PeerImp.cpp:3541` | Soft cap on ledger entries in one ledger-data reply. |
| hardMaxReplyNodes | 12288 | 42 | `PeerImp.cpp:1535,3560` | Hard cap; a request for more node IDs is rejected as bad data, and a reply never exceeds this many nodes. |
| sendqIntervals | 4 | 46 | `PeerImp.cpp:728` | Timer intervals a send queue must stay large before the peer is disconnected. |
| dropSendQueue | 192 | 49 | `PeerImp.cpp:2595,3476` | At or above this many queued messages, queries are refused. |
| targetSendQueue | 128 | 52 | `PeerImp.cpp:275` | Sustained send-queue size considered reasonable. |
| checkIdlePeers | 4 | 58 | `OverlayImpl.cpp:111-112` | Idle-peer sweep runs every 4th one-second timer tick — every 4 s. |
| maxQueryDepth | 3 | 61 | `PeerImp.cpp:1552` | Maximum levels searched when answering a ledger query; deeper queries are rejected. |

Reading the tracking thresholds together: a peer can lag by up to
23 ledgers (~70 s) and still count as converged, and is only flagged
diverged after falling more than 128 ledgers (~6.4 min) behind. The
gap between "converged" and "diverged" is wide — 24 to 128 ledgers
is a grey zone where a peer is neither. During a partition, a peer
on the far side crosses into "diverged" only after ~6.4 min of
silence. Finding R-04.

The reply caps bound post-partition catch-up: a recovering node
fetching ledger history gets at most 12,288 nodes per reply (8,192
soft), at most 3 query levels deep. A long partition means many
round trips to re-sync. Finding R-05.

## 2. Peerfinder tuning — `src/xrpld/peerfinder/detail/Tuning.h`

| Constant | Value | Line | What it means |
|---|---|---|---|
| secondsPerConnect | 10 | 40 | Seconds between batches of connection attempts. |
| maxConnectAttempts | 20 | 44 | Maximum simultaneous connection attempts. |
| outPercent | 15 | 52 | Percentage of peer slots that are outbound. |
| minOutCount | 10 | 59 | Hard minimum on outgoing connections. |
| defaultMaxPeers | 21 | 63 | Default total peer slots. Outbound count is max(minOutCount, outPercent × maxPeers) with special rounding; at defaults that is max(10, ~3) = 10 outbound peers. |
| maxRedirects | 30 | 70 | Max redirects accepted from one connection (anti-flood). |
| connectionBackoff | 1, 1, 2, 3, 5, 8, 13, 21, 34, 55 | 79–80 | Fibonacci backoff in seconds between reconnect attempts to the same address. |
| bootcacheSize | 1000 | 90 | Boot address-cache entries above which the cache is trimmed by 10% (line 94). |
| maxHops | 6 | 110 | Incoming messages with more hops are dropped; each mtENDPOINTS carries 2 × maxHops = 12 endpoints. |
| secondsPerMessage | 151 | 124 | Seconds between mtENDPOINTS messages per peer (prime, by design). |
| liveCacheSecondsToLive | 30 | 128 | How long an endpoint stays in the live cache. |
| recentAttemptDuration | 60 | 132 | Seconds before an outgoing address is tried again. |

After a partition heals, reconnection is paced by these constants:
a first reconnect attempt within ~10 s (secondsPerConnect), then
Fibonacci backoff up to 55 s per address if the far side is still
unreachable, with at most 20 simultaneous attempts. A node with 21
peer slots keeps 10 outbound connections at defaults, so a healed
partition has at most 10 outbound slots per node to rebuild with.

## 3. Manifest bounds — `src/xrpld/app/misc/Manifest.h`

| Constant | Value | Line | What it means |
|---|---|---|---|
| defaultMaxUntrustedManifests | 1000 | 283 | Default cap on untrusted manifests held in cache. |
| untrustedManifestCount | configured.value_or(1000) | 287 | The bound actually used, given an optional `[overlay] max_untrusted_count` override (comment at :279: the override "must stay well above the number of" validators). |

With 25 validators, the 1000-manifest bound is 40× the UNL size;
it cannot bind on this testnet. It would matter only if the
validator set grew past ~1000 or if gossip flooded the cache with
untrusted manifests.

## 4. What is measured, and what is not

[MEASURED] Live `server_info` (2026-11-25 18:24 UTC): validation
quorum 17, server_state full, 21 peers. The quorum corroborates
the 67% model; the peer count (21) is consistent with
defaultMaxPeers (21) but does not prove any node uses the default.

[UNSUPPORTED] Everything else in this audit is configured, not
observed: no peer has been seen going idle, diverging, or being
disconnected; no send queue has been seen filling; no ledger-data
reply has been seen hitting a cap; no endpoint has been seen
expiring. A configured constant is a promise about code paths, not
evidence those paths ran. Any claim that a threshold "works" on
the testnet would need a live observation of the threshold
triggering, which this pack does not have.
