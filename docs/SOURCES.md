# Sources

Every primary source used in this pack, with how it was fetched or
checked out and when. Nothing here comes from a secondary summary.

## postfiatd source (pinned)

- Repository: https://github.com/postfiatorg/postfiatd
- Commit: `0085a1ff885d6a446369cf73a4430f75af22be55`
  (release 1.0.9, 2026-10-10)
- Verified by `git rev-parse HEAD` on a local checkout
  (2026-11-26). Every blob SHA in `data/postfiatd_pin.json` was
  verified with `git hash-object` on that checkout; every cited
  line number was verified with `grep -n` on that checkout.
- Files cited (with blob SHAs in `data/postfiatd_pin.json`):
  `src/xrpld/app/misc/detail/ValidatorList.cpp`,
  `include/xrpl/protocol/SystemParameters.h`,
  `src/xrpld/app/misc/Manifest.h`,
  `src/xrpld/overlay/detail/Tuning.h`,
  `src/xrpld/peerfinder/detail/Tuning.h`,
  `src/xrpld/app/misc/NegativeUNLVote.h`,
  `src/xrpld/app/misc/NegativeUNLVote.cpp`,
  `src/xrpld/app/ledger/Ledger.h`,
  `src/xrpld/overlay/detail/PeerImp.cpp`,
  `src/xrpld/overlay/detail/OverlayImpl.cpp`,
  `src/xrpld/app/consensus/RCLConsensus.cpp` (flag-ledger voting
  branch).

## Live testnet inputs (vendored in `data/`)

- Validator list: `https://postfiat.org/testnet_vl.json`, fetched
  2026-11-25 18:15 UTC (plain HTTPS GET; `data/testnet_vl.json`).
  Response is `{version, blobs_v2, manifest, public_key}`;
  the list lives in `blobs_v2[0].blob` as base64url JSON.
- Close-time sample: `https://rpc.testnet.postfiat.org`
  (`server_info` + 11 consecutive `ledger` calls), fetched
  2026-11-25 18:24 UTC (`data/close_sample.json`). The endpoint
  dropped several connections mid-fetch; `scripts/rpc_client.py`
  retried up to 4 times with exponential backoff.
- Feature list: `https://rpc.testnet.postfiat.org` (`feature`
  method), fetched 2026-11-25 18:25 UTC
  (`data/features_sample.json`, 101 amendments). The NegativeUNL
  amendment id is
  `B4E4F5D2D6FB84DF7399960A732309C9FD530EAE5941838160042833625A6076`.

## Paper

- Chase, B. & MacBrough, E., "Analysis of the XRP Ledger Consensus
  Protocol", arXiv:1802.07242. Theorem 8, Proposition 7, Lemma 6,
  Theorem 11, and Example 9 verified verbatim against the arXiv
  HTML version (ar5iv) on 2026-11-25. The paper's quorum is
  ⌈0.8n⌉ with at most n − q Byzantine faults; its headline result
  is that 80% quorums need roughly >90% UNL overlap under the
  general fault model.

## What was NOT used

- No Discord content, no forum posts, no secondary summaries. The
  Theorem 8 quotation, the quorum formula, and every tuning
  constant come from the primary source (paper text or pinned
  source) directly.
- No per-validator configuration was available: the public RPC
  does not report individual validators' UNLs, so UNL uniformity
  is an assumption (A-1), stated wherever it is used.
