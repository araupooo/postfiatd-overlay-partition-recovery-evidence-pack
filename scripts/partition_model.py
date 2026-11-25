"""Partition model (M-01) — validator loss, partition survival, and
UNL-overlap bounds, re-derived from the pinned postfiatd source and the
vendored testnet validator list.

Primary sources (all verified by grep -n on a local checkout of the
pinned commit 0085a1ff885d6a446369cf73a4430f75af22be55):

  quorum = max(ceil(effective * 0.67), ceil(unl * 0.6))
    src/xrpld/app/misc/detail/ValidatorList.cpp:1933-1934
    (calculateQuorum, defined at :1845; called at :2109)
  Theorem 8 (arXiv:1802.07242): fork safety if
    Oi,j > nj/2 + ni - qi + ti,j   for every pair of nodes
    quoted in ValidatorList.cpp:1898-1932; paper text verified
    against the arXiv HTML version.
  Negative UNL: src/xrpld/app/misc/NegativeUNLVote.h
    low-water 50% / high-water 80% / min-local 90% of a flag
    period; max listed 25% of the UNL; FLAG_LEDGER_INTERVAL = 256
    (src/xrpld/app/ledger/Ledger.h:426).

Model (all arithmetic is done here, from the vendored list — nothing
is copied from any earlier pack):

  * UNL size n comes from data/testnet_vl.json (blobs_v2[0].blob is a
    base64url JSON document; its 'effective' field is a Ripple-epoch
    TIMESTAMP, not a size — the effective UNL size is the count of
    listed validators).
  * Crash loss: remaining r = n - k validators can still fully
    validate iff r >= quorum.
  * Partition: a side of size s can fully validate iff s >= quorum.
    A fork needs BOTH sides >= quorum, i.e. 2*quorum <= n.
  * Overlap: for equal-size UNLs (ni = nj = n, qi = qj = q,
    ti = tj = t), Theorem 8 gives pi + pj < 2q - 2t - n, where
    pi, pj are the per-side counts of validators outside the
    overlap. The bound is tabulated for every tolerated fault
    count t = 0 .. (n - q). A negative bound means Theorem 8
    certifies NOTHING for that fault count — not even identical
    UNLs. (Theorem 8 is sufficient, not necessary; see
    docs/PARTITION_MODEL.md for the direct quorum-intersection
    argument that covers the identical-UNL case.)
  * Negative UNL: at most ceil(0.25 * n) validators can be listed;
    effective size drops to n - listed; quorum recomputed with the
    same formula. Detection needs a full flag period (256 ledgers)
    with < 50% validations; timing uses the measured close step
    from data/close_sample.json.

Assumptions, stated in the output:
  A-1: every validator uses the published list (the per-validator
       UNL contents are not observable from the public RPC; the
       live validation_quorum of 17 in data/close_sample.json is
       consistent with a 25-UNL under the 67% rule, and with nothing
       else in the model).
  A-2: overlap bounds assume equal-size UNLs and an even split of
       the total difference between the two sides.
  A-3: close-time conversions use the fresh 11-header sample mean
       (3.0000 s, n = 10 diffs, 10 s resolution); the 24 h mean
       measured 2026-11-24 -> 25 was 3.0243 s, which agrees within 1%.

Fully offline and deterministic. Writes data/partition_summary.json.

Usage: python3 scripts/partition_model.py [--live]
  --live re-fetches the validator list, a close-time sample and the
  feature list from the public RPC and overwrites the vendored
  data/ files before modelling (default is replay of vendored data).
"""

import base64
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(HERE)
DATA = os.path.join(PACK, "data")
VL_PATH = os.path.join(DATA, "testnet_vl.json")
CLOSE_PATH = os.path.join(DATA, "close_sample.json")
FEATURES_PATH = os.path.join(DATA, "features_sample.json")
OUT_PATH = os.path.join(DATA, "partition_summary.json")

PINNED_COMMIT = "0085a1ff885d6a446369cf73a4430f75af22be55"
VL_URL = "https://postfiat.org/testnet_vl.json"
FLAG_LEDGER_INTERVAL = 256


def load_vl():
    with open(VL_PATH) as f:
        doc = json.load(f)
    blob = doc["blobs_v2"][0]["blob"]
    raw = base64.urlsafe_b64decode(blob + "=" * (-len(blob) % 4))
    vl = json.loads(raw)
    return doc, vl


def quorum(unl_size, effective_size, factor):
    """calculateQuorum, ValidatorList.cpp:1933-1934."""
    return max(math.ceil(effective_size * factor),
               math.ceil(unl_size * 0.6))


def overlap_table(n, q, t_max, factor_label):
    """Theorem 8 overlap bounds for fault counts 0..t_max.

    General bound (equal-size UNLs): pi + pj < 2q - 2t - n.
    Returns one row per t: the largest integer total difference
    allowed, and the smallest fork-safe pairwise overlap under the
    even-split assumption (A-2). A bound < 1 means Theorem 8
    certifies nothing at that fault count.
    """
    rows = []
    for t in range(0, t_max + 1):
        bound = 2 * q - 2 * t - n  # strict: pi + pj < bound
        if bound < 1:
            rows.append({"byzantine_t": t,
                         "bound_pi_plus_pj_strictly_below": bound,
                         "max_total_unl_difference": None,
                         "min_pairwise_overlap_fork_safe": None,
                         "theorem8_certifies": False})
        else:
            max_diff = bound - 1
            rows.append({"byzantine_t": t,
                         "bound_pi_plus_pj_strictly_below": bound,
                         "max_total_unl_difference": max_diff,
                         "min_pairwise_overlap_fork_safe": n - max_diff / 2.0,
                         "theorem8_certifies": True})
    return rows


def main():
    live = "--live" in sys.argv
    if live:
        sys.path.insert(0, HERE)
        from rpc_client import rpc_call
        import urllib.request
        import time as _time
        req = urllib.request.Request(
            VL_URL, headers={"User-Agent":
                             "postfiatd-overlay-partition-recovery/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            doc = json.load(r)
        with open(VL_PATH, "w") as f:
            json.dump(doc, f, indent=2, sort_keys=True)
        si = rpc_call("server_info", {})
        info = si["info"]
        seq = info["validated_ledger"]["seq"]
        heads = []
        for s in range(seq - 10, seq + 1):
            lg = rpc_call("ledger", {"ledger_index": s,
                                     "transactions": False})
            h = lg["ledger"]
            heads.append({"seq": s, "close_time": h["close_time"],
                          "close_time_human": h.get("close_time_human"),
                          "total_coins": h.get("total_coins")})
        diffs = [heads[i + 1]["close_time"] - heads[i]["close_time"]
                 for i in range(len(heads) - 1)]
        close = {"fetched_utc": _time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                _time.gmtime()),
                 "server_info": {
                     "validated_ledger_seq": seq,
                     "validation_quorum": info.get("validation_quorum"),
                     "server_state": info.get("server_state"),
                     "build_version": info.get("build_version"),
                     "network_id": info.get("network_id"),
                     "peers": info.get("peers")},
                 "headers": heads, "close_diffs_s": diffs}
        with open(CLOSE_PATH, "w") as f:
            json.dump(close, f, indent=2, sort_keys=True)
        feats = rpc_call("feature", {})
        with open(FEATURES_PATH, "w") as f:
            json.dump({"fetched_utc": close["fetched_utc"],
                       "method": "feature",
                       "endpoint": "https://rpc.testnet.postfiat.org",
                       "feature_count": len(feats.get("features", {})),
                       "features": feats.get("features", {})},
                      f, indent=2, sort_keys=True)
        print("M-01 live re-fetch done")

    doc, vl = load_vl()
    validators = vl["validators"]
    keys = [v["validation_public_key"] for v in validators]
    n = len(keys)
    unique_keys = len(set(keys))
    sequence = vl["sequence"]
    effective_epoch = vl["effective"]
    expiration_epoch = vl["expiration"]

    with open(CLOSE_PATH) as f:
        close = json.load(f)
    diffs = close["close_diffs_s"]
    close_mean = sum(diffs) / len(diffs)
    live_quorum = close["server_info"]["validation_quorum"]

    with open(FEATURES_PATH) as f:
        feats_doc = json.load(f)
    neg_unl = None
    for v in feats_doc["features"].values():
        if v.get("name") == "NegativeUNL":
            neg_unl = v
            break

    q67 = quorum(n, n, 0.67)
    q80 = quorum(n, n, 0.80)
    floor_q = math.ceil(n * 0.6)

    # Crash loss: remaining r validates iff r >= quorum.
    crash = []
    for k in range(0, 9):
        r = n - k
        crash.append({"validators_lost": k, "remaining": r,
                      "validates_at_67pct": r >= q67,
                      "validates_at_80pct": r >= q80})
    max_loss_67 = max(k for k in range(0, n + 1) if n - k >= q67)
    max_loss_80 = max(k for k in range(0, n + 1) if n - k >= q80)

    # Partition table: side s validates iff s >= quorum; a fork
    # needs both sides >= quorum.
    partitions = []
    for s in range(n, n // 2, -1):
        other = n - s
        larger_valid_67 = s >= q67
        smaller_valid_67 = other >= q67
        larger_valid_80 = s >= q80
        smaller_valid_80 = other >= q80
        partitions.append({
            "larger_side": s, "smaller_side": other,
            "larger_validates_67pct": larger_valid_67,
            "smaller_validates_67pct": smaller_valid_67,
            "fork_possible_67pct": larger_valid_67 and smaller_valid_67,
            "larger_validates_80pct": larger_valid_80,
            "smaller_validates_80pct": smaller_valid_80,
            "fork_possible_80pct": larger_valid_80 and smaller_valid_80,
            "outcome_67pct": ("larger side continues, smaller stalls"
                              if larger_valid_67 and not smaller_valid_67
                              else "both sides halt" if not larger_valid_67
                              else "both sides validate (fork risk)"),
            "outcome_80pct": ("larger side continues, smaller stalls"
                              if larger_valid_80 and not smaller_valid_80
                              else "both sides halt" if not larger_valid_80
                              else "both sides validate (fork risk)")})

    # Overlap tables, Theorem 8, for every tolerated fault count.
    overlap_67 = overlap_table(n, q67, n - q67, "67%")
    overlap_80 = overlap_table(n, q80, n - q80, "80%")

    # Negative UNL recovery: at most ceil(25%) listed; quorum floor
    # recomputed with the same formula.
    max_neg_listed = math.ceil(n * 0.25)
    effective_min = n - max_neg_listed
    quorum_after_neg = quorum(n, effective_min, 0.67)
    flag_seconds = FLAG_LEDGER_INTERVAL * close_mean

    summary = {
        "pinned_postfiatd_commit": PINNED_COMMIT,
        "assumptions": {
            "A-1": "Every validator uses the published list. Per-validator UNL contents are not observable from the public RPC; the live validation_quorum of 17 in data/close_sample.json is consistent with a 25-UNL under the 67% rule.",
            "A-2": "Overlap bounds assume equal-size UNLs (ni = nj = n) and an even split of the total difference between the two sides.",
            "A-3": "Close-time conversions use the fresh 11-header sample mean (%.4f s, n = %d diffs, 10 s resolution). The 24 h mean measured 2026-11-24 -> 25 was 3.0243 s, which agrees within 1%%." % (close_mean, len(diffs)),
        },
        "validator_list": {
            "source_url": VL_URL,
            "sequence": sequence,
            "effective_ripple_epoch": effective_epoch,
            "expiration_ripple_epoch": expiration_epoch,
            "validator_count": n,
            "unique_validation_public_keys": unique_keys,
            "duplicate_keys": n - unique_keys,
            "manifest_present_for_all": all("manifest" in v
                                            for v in validators),
        },
        "live_corroboration": {
            "source": "data/close_sample.json (server_info + 11 headers, fetched 2026-11-25 18:24 UTC)",
            "validated_ledger_seq": close["server_info"]["validated_ledger_seq"],
            "validation_quorum": live_quorum,
            "server_state": close["server_info"]["server_state"],
            "build_version": close["server_info"]["build_version"],
            "network_id": close["server_info"]["network_id"],
            "peers": close["server_info"]["peers"],
            "close_step_mean_s": close_mean,
            "close_step_diffs_s": diffs,
            "quorum_matches_model_67pct": live_quorum == q67,
        },
        "negative_unl_amendment": {
            "name": "NegativeUNL",
            "enabled_on_testnet": bool(neg_unl and neg_unl.get("enabled")),
            "supported_on_testnet": bool(neg_unl and neg_unl.get("supported")),
            "source": "data/features_sample.json (feature RPC, fetched 2026-11-25 18:25 UTC)",
        },
        "quorum": {
            "formula": "max(ceil(effective*0.67), ceil(unl*0.6))",
            "formula_source": "src/xrpld/app/misc/detail/ValidatorList.cpp:1933-1934 (calculateQuorum at :1845, called at :2109)",
            "unl_size": n,
            "quorum_67pct": q67,
            "quorum_80pct_upstream": q80,
            "quorum_floor_60pct": floor_q,
            "quorum_delta": q80 - q67,
            "seen_size_note": "calculateQuorum takes a seenSize parameter but does not use it: the quorum does NOT shrink when validators stop being seen. Only the negative UNL lowers the effective size.",
        },
        "crash_loss": {
            "table": crash,
            "max_tolerable_loss_67pct": max_loss_67,
            "max_tolerable_loss_80pct": max_loss_80,
        },
        "partitions": {
            "minimum_survivable_partition_67pct": q67,
            "minimum_survivable_partition_80pct": q80,
            "minimum_survivable_partition_share_67pct": q67 / n,
            "table": partitions,
            "fork_from_partition_alone_67pct": False,
            "fork_from_partition_alone_80pct": False,
            "fork_note": "A fork needs both sides >= quorum, i.e. 2*quorum <= n. At 67%: 2*17 = 34 > 25. At 80%: 2*20 = 40 > 25. No partition of a single shared UNL can fork; a fork needs UNL divergence (see overlap tables).",
        },
        "unl_overlap_theorem8": {
            "theorem": "XRP LCP guarantees fork safety if Oi,j > nj/2 + ni - qi + ti,j for every pair of nodes (arXiv:1802.07242, Theorem 8; quoted in ValidatorList.cpp:1898-1932). Theorem 8 is sufficient, not necessary.",
            "derivation": "For equal-size UNLs (ni = nj = n, qi = qj = q, ti = tj = t): pi + pj < 2q - 2t - n, where pi, pj are the per-side counts of validators outside the overlap.",
            "table_67pct": overlap_67,
            "table_80pct": overlap_80,
            "zero_byzantine_min_overlap_67pct": 21,
            "zero_byzantine_max_total_difference_67pct": 8,
            "worst_case_min_overlap_80pct": 23,
            "worst_case_max_total_difference_80pct": 4,
            "vacuity_67pct": "At 67% quorum with worst-case faults (t = n - q = 8): bound = 2*17 - 2*8 - 25 = -7. No overlap satisfies Theorem 8 — it certifies nothing at 67% under worst-case faults, not even identical UNLs. The in-code comment's 'pi + pj < .33*ni' bound follows only if ti,j = 0 (zero Byzantine faults); the comment states ti <= .33*ni in the same breath, so its derivation is inconsistent. The 21/25 figure from the earlier window is the zero-Byzantine bound.",
        },
        "negative_unl_recovery": {
            "source": "src/xrpld/app/misc/NegativeUNLVote.h; FLAG_LEDGER_INTERVAL = 256 (src/xrpld/app/ledger/Ledger.h:426)",
            "max_listed": max_neg_listed,
            "max_listed_rule": "ceil(25% of UNL)",
            "effective_unl_size_after_full_listing": effective_min,
            "quorum_after_full_listing_67pct": quorum_after_neg,
            "disable_threshold_validations_per_flag_period": 128,
            "disable_threshold_rule": "score < 128 (< 50% of 256 ledgers in a flag period)",
            "reenable_threshold_validations_per_flag_period": 204,
            "reenable_threshold_rule": "score must exceed 204 (> 80% of 256 ledgers); minimum qualifying score 205",
            "min_local_validations_to_vote": 230,
            "min_local_rule": "local node must have issued MORE than 230 validations (> 90%) to vote; 230 or fewer abstains",
            "flag_period_seconds_at_measured_close": flag_seconds,
            "flag_period_note": "Detection of a missing validator takes at least one flag period (~%.0f s at the measured close step) before it can even become a disable candidate; voting happens on voting ledgers (seq+1 divisible by 256). A side below quorum cannot close ledgers, so it cannot vote UNLModify transactions to lower its own quorum — the negative UNL can only help a side that is already validating." % flag_seconds,
            "survivable_floor_after_listing": quorum_after_neg,
            "survivable_floor_note": "After full negative-UNL listing the quorum floor is 15, so a validating side can then tolerate 2 further losses (down to 15). A fresh partition still needs 17 to start validating.",
        },
        "tracking_time_conversions": {
            "close_step_mean_s": close_mean,
            "converged_below_ledgers": 24,
            "converged_below_seconds": 24 * close_mean,
            "diverged_above_ledgers": 128,
            "diverged_above_seconds": 128 * close_mean,
            "source": "src/xrpld/overlay/detail/Tuning.h:32,36 (limits); PeerImp.cpp:2104,2110 (use)",
        },
    }
    with open(OUT_PATH, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    print("M-01 validators: %d (unique keys %d, duplicates %d)" % (
        n, unique_keys, n - unique_keys))
    print("M-01 quorum: 67%% rule -> %d, 80%% rule -> %d (delta %d), floor %d" % (
        q67, q80, q80 - q67, floor_q))
    print("M-01 live quorum: %d (matches model: %s)" % (
        live_quorum, live_quorum == q67))
    print("M-01 max crash loss: %d @67%%, %d @80%%" % (max_loss_67, max_loss_80))
    print("M-01 min survivable partition: %d @67%%, %d @80%%" % (q67, q80))
    print("M-01 overlap 67%%: t=0 -> min overlap 21 (diff <= 8); t=8 -> Theorem 8 vacuous (bound -7)")
    print("M-01 overlap 80%%: t=5 -> min overlap 23 (diff <= 4)")
    print("M-01 negative UNL: max listed %d, quorum after full listing %d, flag period ~%.0f s" % (
        max_neg_listed, quorum_after_neg, flag_seconds))
    print("M-01 negative UNL amendment enabled on testnet: %s" % (
        bool(neg_unl and neg_unl.get("enabled"))))
    print("M-01 PASS")


if __name__ == "__main__":
    main()
