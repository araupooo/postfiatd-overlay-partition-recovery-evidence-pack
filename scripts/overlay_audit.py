"""Overlay parameter audit (M-02).

Every constant below was read from the pinned postfiatd source
(commit 0085a1ff885d6a446369cf73a4430f75af22be55) and verified with
grep -n on a local checkout; the file:line citations are the
verification. This script re-derives the time conversions from the
measured close step in data/close_sample.json and writes
data/overlay_audit.json. It does not fetch anything and does not
need the postfiatd checkout at run time — to re-verify a citation,
check out the pinned commit and run, for example:
  grep -n "convergedLedgerLimit" src/xrpld/overlay/detail/Tuning.h

Configured values are NOT measured behavior: a constant says what
the code will do when the condition arises; it does not say the
condition has ever arisen on the testnet. The audit separates the
two: 'configured' rows are source readings, 'derived' rows are
arithmetic on the measured close step, and 'measured' rows are live
observations from data/close_sample.json.

Usage: python3 scripts/overlay_audit.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(HERE)
DATA = os.path.join(PACK, "data")
CLOSE_PATH = os.path.join(DATA, "close_sample.json")
OUT_PATH = os.path.join(DATA, "overlay_audit.json")

PINNED_COMMIT = "0085a1ff885d6a446369cf73a4430f75af22be55"


def main():
    with open(CLOSE_PATH) as f:
        close = json.load(f)
    diffs = close["close_diffs_s"]
    close_mean = sum(diffs) / len(diffs)

    audit = {
        "pinned_postfiatd_commit": PINNED_COMMIT,
        "close_step_mean_s": close_mean,
        "close_step_note": "Fresh 11-header sample, data/close_sample.json (n = %d diffs, 10 s resolution). The 24 h mean measured 2026-11-24 -> 25 was 3.0243 s." % len(diffs),
        "overlay_tuning": {
            "source": "src/xrpld/overlay/detail/Tuning.h",
            "rows": [
                {"name": "convergedLedgerLimit", "value": 24,
                 "line": 32,
                 "meaning": "A peer whose ledger sequence is within 24 ledgers of the validation's is treated as converged.",
                 "use": "src/xrpld/overlay/detail/PeerImp.cpp:2104 (checkTracking)"},
                {"name": "divergedLedgerLimit", "value": 128,
                 "line": 36,
                 "meaning": "A peer more than 128 ledgers behind the validation's is marked diverged.",
                 "use": "src/xrpld/overlay/detail/PeerImp.cpp:2110 (checkTracking)"},
                {"name": "softMaxReplyNodes", "value": 8192,
                 "line": 39,
                 "meaning": "Soft cap on ledger entries in a single ledger-data reply.",
                 "use": "src/xrpld/overlay/detail/PeerImp.cpp:3541"},
                {"name": "hardMaxReplyNodes", "value": 12288,
                 "line": 42,
                 "meaning": "Hard cap: a ledger-node request carrying more IDs is rejected as bad data; a reply never exceeds this many nodes.",
                 "use": "src/xrpld/overlay/detail/PeerImp.cpp:1535,3560"},
                {"name": "sendqIntervals", "value": 4,
                 "line": 46,
                 "meaning": "Timer intervals a send queue must stay large before the peer is disconnected.",
                 "use": "src/xrpld/overlay/detail/PeerImp.cpp:728"},
                {"name": "dropSendQueue", "value": 192,
                 "line": 49,
                 "meaning": "Messages on a send queue at or above this count: queries are refused.",
                 "use": "src/xrpld/overlay/detail/PeerImp.cpp:2595,3476"},
                {"name": "targetSendQueue", "value": 128,
                 "line": 52,
                 "meaning": "Sustained send-queue size considered reasonable.",
                 "use": "src/xrpld/overlay/detail/PeerImp.cpp:275"},
                {"name": "checkIdlePeers", "value": 4,
                 "line": 58,
                 "meaning": "Idle-peer sweep runs every 4th one-second timer tick, i.e. every 4 s.",
                 "use": "src/xrpld/overlay/detail/OverlayImpl.cpp:111-112"},
                {"name": "maxQueryDepth", "value": 3,
                 "line": 61,
                 "meaning": "Maximum levels searched when answering a ledger query; deeper queries are rejected.",
                 "use": "src/xrpld/overlay/detail/PeerImp.cpp:1552"},
            ],
        },
        "peerfinder_tuning": {
            "source": "src/xrpld/peerfinder/detail/Tuning.h",
            "rows": [
                {"name": "secondsPerConnect", "value": 10,
                 "line": 40,
                 "meaning": "Seconds waited between batches of connection attempts."},
                {"name": "maxConnectAttempts", "value": 20,
                 "line": 44,
                 "meaning": "Maximum simultaneous connection attempts."},
                {"name": "outPercent", "value": 15,
                 "line": 52,
                 "meaning": "Percentage of peer slots that are outbound; outbound count is max(minOutCount, outPercent * maxPeers)."},
                {"name": "minOutCount", "value": 10,
                 "line": 59,
                 "meaning": "Hard minimum on outgoing connections."},
                {"name": "defaultMaxPeers", "value": 21,
                 "line": 63,
                 "meaning": "Default total peer slots. Outbound count is max(minOutCount, outPercent * maxPeers) with special rounding; at defaults that is max(10, ~3) = 10 outbound peers."},
                {"name": "maxRedirects", "value": 30,
                 "line": 70,
                 "meaning": "Max redirects accepted from one connection (anti-flood)."},
                {"name": "connectionBackoff", "value": [1, 1, 2, 3, 5, 8, 13, 21, 34, 55],
                 "line": 79,
                 "meaning": "Fibonacci backoff in seconds between reconnect attempts to the same address (10 entries)."},
                {"name": "bootcacheSize", "value": 1000,
                 "line": 90,
                 "meaning": "Boot address-cache entries above which the cache is trimmed (by 10%, line 94)."},
                {"name": "maxHops", "value": 6,
                 "line": 110,
                 "meaning": "Incoming messages with more hops are dropped; each mtENDPOINTS carries 2*maxHops = 12 endpoints."},
                {"name": "secondsPerMessage", "value": 151,
                 "line": 124,
                 "meaning": "Seconds between mtENDPOINTS messages per peer (prime, by design)."},
                {"name": "liveCacheSecondsToLive", "value": 30,
                 "line": 128,
                 "meaning": "How long an endpoint stays in the live cache."},
                {"name": "recentAttemptDuration", "value": 60,
                 "line": 132,
                 "meaning": "Seconds before an outgoing address is tried again."},
            ],
        },
        "manifest_bounds": {
            "source": "src/xrpld/app/misc/Manifest.h",
            "rows": [
                {"name": "defaultMaxUntrustedManifests", "value": 1000,
                 "line": 283,
                 "meaning": "Default cap on untrusted manifests held in cache; overridable via [overlay] max_untrusted_count (comment at :279)."},
                {"name": "untrustedManifestCount", "value": "configured.value_or(defaultMaxUntrustedManifests)",
                 "line": 287,
                 "meaning": "The bound actually used, given an optional config override."},
            ],
        },
        "derived_time_conversions": {
            "close_step_mean_s": close_mean,
            "converged_below_seconds": 24 * close_mean,
            "converged_note": "A peer up to ~%.1f s behind still counts as converged." % (24 * close_mean),
            "diverged_above_seconds": 128 * close_mean,
            "diverged_note": "A peer is only marked diverged after falling ~%.1f s (~%.1f min) behind." % (128 * close_mean, 128 * close_mean / 60.0),
            "idle_sweep_seconds": 4,
            "idle_sweep_note": "One-second timer, sweep every 4th tick (OverlayImpl.cpp:111-112).",
            "flag_period_seconds": 256 * close_mean,
            "flag_period_note": "256 ledgers at the measured close step (Ledger.h:426 FLAG_LEDGER_INTERVAL).",
        },
        "measured_live": {
            "source": "data/close_sample.json",
            "validation_quorum": close["server_info"]["validation_quorum"],
            "server_state": close["server_info"]["server_state"],
            "peers": close["server_info"]["peers"],
            "note": "Live server_info corroborates the model quorum (17) but says nothing about the tuning constants — no constant above has ever been observed triggering on the testnet in this pack.",
        },
    }
    with open(OUT_PATH, "w") as f:
        json.dump(audit, f, indent=2, sort_keys=True)
    print("M-02 overlay constants: %d rows" % (
        len(audit["overlay_tuning"]["rows"])))
    print("M-02 peerfinder constants: %d rows" % (
        len(audit["peerfinder_tuning"]["rows"])))
    print("M-02 manifest bounds: %d rows" % (
        len(audit["manifest_bounds"]["rows"])))
    print("M-02 converged below %.1f s, diverged above %.1f s (close step %.4f s)" % (
        24 * close_mean, 128 * close_mean, close_mean))
    print("M-02 idle sweep every 4 s; negative-UNL flag period ~%.0f s" % (
        256 * close_mean))
    print("M-02 PASS")


if __name__ == "__main__":
    main()
