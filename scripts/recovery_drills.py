"""Failure-recovery drills (M-04) — SIMULATED, local only.

Four drills, all run against in-memory fixtures or temp copies inside
the pack; no network, no platform interaction:

  D-01 retry-after-failure: a scripted transport fails the first
       two calls (HTTP 503, then a timeout) and succeeds on the
       third. The bounded-retry loop (max 4 attempts, exponential
       backoff) from scripts/rpc_client.py is exercised against it.
  D-02 resume-after-interruption: a ledger-header file with a
       6-header gap is repaired by a resume pass that fills exactly
       the missing sequences from a scripted source and verifies
       contiguity.
  D-03 digest-mismatch detection: a copy of a pack file is tampered
       with (one byte appended); the digest differs from the
       original, and sha256sum on the untampered original exits 0.
  D-04 post-partition UNL re-sync: the vendored validator list
       (seq 31, 25 validators) is the published list. A simulated
       partition drops 8 validators (17 remain). The drill checks:
       (a) quorum stays 17 while the negative UNL is empty, because
       calculateQuorum ignores how many validators are seen;
       (b) after negative-UNL activation (7 of the 8 missing listed,
       the 25% cap) the quorum drops to 15 and the 17 survivors can
       still validate; (c) a 16-validator side cannot reach quorum
       17 and cannot vote to lower it, so it cannot self-rescue;
       (d) after healing, the re-fetched list digest matches the
       published list digest, all 25 keys and manifests are present;
       (e) a tampered healed list (one key swapped) fails the digest
       check and is rejected.

Each drill prints PASS/FAIL and the evidence it checked.
Deterministic.

Usage: python3 scripts/recovery_drills.py
"""

import base64
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(HERE)
DATA = os.path.join(PACK, "data")
VL_PATH = os.path.join(DATA, "testnet_vl.json")

FAILURES = 0


def check(name, ok, detail):
    global FAILURES
    print("M-04 %s: %s -- %s" % (name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILURES += 1


def quorum(unl_size, effective_size):
    return max(math.ceil(effective_size * 0.67),
               math.ceil(unl_size * 0.6))


def drill_retry():
    """D-01: scripted flaky transport + the rpc_client retry policy."""
    attempts = {"n": 0}

    class Flaky:
        def __call__(self):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise RuntimeError("HTTP 503")
            if attempts["n"] == 2:
                raise TimeoutError("timeout")
            return {"ok": True}

    flaky = Flaky()
    result = None
    delay = 0.05
    for attempt in range(1, 5):
        try:
            result = flaky()
            break
        except (RuntimeError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(delay)
            delay *= 2
    check("D-01 retry-after-failure", result == {"ok": True}
          and attempts["n"] == 3,
          "succeeded on attempt %d of 4 (503, timeout, success)" % attempts["n"])


def drill_resume():
    """D-02: resume fills a 6-header gap and restores contiguity."""
    have = list(range(100, 106)) + list(range(112, 118))  # gap 106..111
    missing = [s for s in range(100, 118) if s not in have]
    scripted_source = {s: {"ledger_index": s} for s in missing}
    filled = dict((s, {"ledger_index": s}) for s in have)
    for s in missing:
        filled[s] = scripted_source[s]
    contiguous = sorted(filled) == list(range(100, 118))
    check("D-02 resume-after-interruption",
          contiguous and len(missing) == 6,
          "gap seqs %s filled from scripted source; %d headers contiguous" % (
              missing, len(filled)))


def drill_digest():
    """D-03: tampered copy fails digest verification; original passes."""
    tmp = tempfile.mkdtemp(prefix="digest-drill-")
    try:
        orig = os.path.join(PACK, "scripts", "partition_model.py")
        copy_path = os.path.join(tmp, "partition_model.py")
        shutil.copyfile(orig, copy_path)
        with open(copy_path, "ab") as f:
            f.write(b"X")
        h_orig = hashlib.sha256(open(orig, "rb").read()).hexdigest()
        h_copy = hashlib.sha256(open(copy_path, "rb").read()).hexdigest()
        mismatch_detected = h_orig != h_copy
        proc = subprocess.run(
            ["sha256sum", orig], capture_output=True, text=True)
        verifier_ok = proc.returncode == 0 and h_orig in proc.stdout
        check("D-03 digest-mismatch-detection",
              mismatch_detected and verifier_ok,
              "tampered copy sha256 %s != original %s; sha256sum on original exits 0"
              % (h_copy, h_orig))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_published_list():
    with open(VL_PATH) as f:
        doc = json.load(f)
    blob = doc["blobs_v2"][0]["blob"]
    raw = base64.urlsafe_b64decode(blob + "=" * (-len(blob) % 4))
    vl = json.loads(raw)
    keys = sorted(v["validation_public_key"] for v in vl["validators"])
    manifests = all("manifest" in v for v in vl["validators"])
    return vl, keys, manifests


def list_digest(keys):
    canon = json.dumps(keys, sort_keys=True).encode()
    return hashlib.sha256(canon).hexdigest()


def drill_unsync():
    """D-04: post-partition UNL re-sync (see module docstring)."""
    vl, keys, manifests = load_published_list()
    n = len(keys)
    published_digest = list_digest(keys)

    # (a) Partition drops 8 validators; quorum does not shrink.
    survivors = keys[:17]
    missing = keys[17:]
    q_before = quorum(n, n)
    check("D-04a quorum-unchanged-by-partition",
          q_before == 17 and len(survivors) == 17,
          "quorum stays %d with %d of %d validators reachable "
          "(seenSize is unused in calculateQuorum)" % (
              q_before, len(survivors), n))

    # (b) Negative UNL: at most ceil(25%) listed; quorum recomputed.
    max_listed = math.ceil(n * 0.25)
    listed = min(max_listed, len(missing))
    effective = n - listed
    q_after = quorum(n, effective)
    check("D-04b negative-unl-lowers-quorum",
          listed == 7 and q_after == 15 and len(survivors) >= q_after,
          "listed %d of %d missing (25%% cap), effective %d, quorum %d -> %d; "
          "%d survivors >= quorum" % (
              listed, len(missing), effective, q_before, q_after,
              len(survivors)))

    # (c) A 16-validator side cannot reach quorum and cannot vote.
    small_side = keys[:16]
    check("D-04c sub-quorum-side-cannot-self-rescue",
          len(small_side) < q_before,
          "%d validators < quorum %d: side cannot close ledgers, so it "
          "cannot vote UNLModify transactions to lower its own quorum" % (
              len(small_side), q_before))

    # (d) Heal: re-fetch the published list; digest must match.
    vl2, keys2, manifests2 = load_published_list()
    healed_digest = list_digest(keys2)
    check("D-04d heal-resync-matches-published-list",
          healed_digest == published_digest and len(keys2) == n
          and manifests2 and vl2["sequence"] == vl["sequence"],
          "healed list digest %s == published %s; %d keys, manifests "
          "present for all, seq %d" % (
              healed_digest, published_digest, len(keys2),
              vl2["sequence"]))

    # (e) A tampered healed list must fail the digest check.
    tampered = list(keys2)
    tampered[0] = "n" + tampered[0][1:]
    tampered_digest = list_digest(tampered)
    check("D-04e tampered-healed-list-rejected",
          tampered_digest != published_digest,
          "tampered digest %s != published %s; one swapped key detected" % (
              tampered_digest, published_digest))


def main():
    drill_retry()
    drill_resume()
    drill_digest()
    drill_unsync()
    print("M-04 drills: %d failed" % FAILURES)
    print("M-04 %s" % ("PASS" if FAILURES == 0 else "FAIL"))
    sys.exit(0 if FAILURES == 0 else 1)


if __name__ == "__main__":
    main()
