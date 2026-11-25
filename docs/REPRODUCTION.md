# Reproduction

## One command

```sh
bash reproduce.sh
```

Expected output ends with `ALL CHECKS PASSED` (from
`scripts/run_all.sh`), then 28/28 digest lines ending in `OK`
(from `verify_digests.sh`), then `REPRODUCE OK`. Exit code 0.
Python 3.9+ standard library only. No network access at run time:
every script replays the vendored `data/` captures.

The runner writes unedited stdout to `outputs/<script>.log`
(`partition_model.log`, `overlay_audit.log`,
`recovery_drills.log`) and exits non-zero if any check fails.
`outputs/reproduce_selfcheck.log` in the repository is the log
from a clean-copy run (see below).

## Re-fetching fresh live inputs

```sh
python3 scripts/partition_model.py --live
```

This re-fetches the validator list, a close-time sample (server_info
+ 11 ledger headers), and the feature list from the public RPC
(`https://rpc.testnet.postfiat.org`,
`https://postfiat.org/testnet_vl.json`), overwrites the vendored
`data/testnet_vl.json`, `data/close_sample.json`, and
`data/features_sample.json`, and re-runs the model. The public RPC
intermittently drops connections; `scripts/rpc_client.py` retries
up to 4 times with exponential backoff. After a `--live` run,
regenerate the manifest:

```sh
bash reproduce.sh
find . -type f -not -path './.git/*' -not -name SHA256SUMS \
  | sort | xargs sha256sum > SHA256SUMS
```

(Note: `outputs/reproduce_selfcheck.log` itself is listed in the
manifest, so generate it last — see "Fresh-copy check" below.)

## Fresh-copy check

The repository was verified from a clean copy, not in place:

```sh
git clone <repo-url> /tmp/check && cd /tmp/check
bash reproduce.sh
```

Expected: exit 0, `REPRODUCE OK`, all digests pass. The log of
that run is vendored as `outputs/reproduce_selfcheck.log`.

## Re-verifying a source citation

Check out the pinned commit and run `grep -n` — never trust a line
number from a web fetch of a raw file:

```sh
git clone https://github.com/postfiatorg/postfiatd.git /tmp/postfiatd
cd /tmp/postfiatd
git rev-parse HEAD   # must print 0085a1ff885d6a446369cf73a4430f75af22be55
grep -n "calculateQuorum" src/xrpld/app/misc/detail/ValidatorList.cpp
grep -n "convergedLedgerLimit" src/xrpld/overlay/detail/Tuning.h
grep -n "negativeUNLLowWaterMark" src/xrpld/app/misc/NegativeUNLVote.h
```

Every blob SHA in `data/postfiatd_pin.json` was verified with
`git hash-object` on that checkout. The Theorem 8 quotation was
verified against the arXiv HTML version of arXiv:1802.07242,
section 4.1.

## Re-running the drills

```sh
python3 scripts/recovery_drills.py
```

Deterministic, local only, no network. Prints one PASS/FAIL line
per drill (D-01–D-04) and a final `M-04 drills: 0 failed`.

## Environment

- Python 3.9+ (developed and tested on 3.12), standard library only.
- `sha256sum` (coreutils) for `verify_digests.sh`.
- CI runs `bash reproduce.sh` on `ubuntu-latest` + Python 3.12
  (`.github/workflows/ci.yml`), with no secrets.
