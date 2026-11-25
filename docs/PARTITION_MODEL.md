# Partition Model — Quorum, Loss, Partitions, and UNL Overlap

All numbers in this document are produced by
`scripts/partition_model.py` from the vendored inputs
(`data/testnet_vl.json`, `data/close_sample.json`,
`data/features_sample.json`). Re-run it to reproduce every table.

## 0. Inputs

[MEASURED] The published validator list
(`https://postfiat.org/testnet_vl.json`, fetched 2026-11-25 18:15 UTC)
holds 25 validators, 25 unique validation public keys, 0 duplicates,
a manifest for every entry, sequence 31, effective Ripple-epoch
848866298 (2026-11-24T20:11:38Z), expiration 892052157
(2028-04-07T16:15:57Z). The blob is base64url JSON; its `effective`
field is a timestamp, not a size.

[MEASURED] Live `server_info` (fetched 2026-11-25 18:24 UTC,
validated ledger 8362579): `validation_quorum` 17, `server_state`
full, build 1.0.9, network_id 2025, 21 peers. The close-step sample
(11 consecutive headers) gives a mean close step of 3.0000 s
(diffs 8, 1, 1, 1, 7, 1, 1, 8, 1, 1 — quantized by the 10 s
close-time resolution). The 24 h mean measured 2026-11-24 → 25 was
3.0243 s, which agrees within 1%.

## 1. The quorum formula, and what does not move it

[MEASURED] `calculateQuorum` is defined at
`src/xrpld/app/misc/detail/ValidatorList.cpp:1845` and returns at
lines 1933–1934:

```
return static_cast<std::size_t>(std::max(
    std::ceil(effectiveUnlSize * 0.67f), std::ceil(unlSize * 0.6f)));
```

`unlSize` is the count of trusted master keys (25); `effectiveUnlSize`
is that count minus validators on the negative UNL (25 while the
negative UNL is empty); the 0.6 term is the AbsoluteMinimumQuorum
floor from the negative-UNL protocol. For n = 25:

- 67% rule: max(ceil(25 × 0.67), ceil(25 × 0.6)) = max(17, 15) = **17**
- 80% rule (upstream): max(ceil(25 × 0.80), 15) = max(20, 15) = **20**
- Floor: 15

The live `validation_quorum` of 17 matches the 67% formula exactly.

[MEASURED] `calculateQuorum` takes a third parameter, `seenSize`
(the count of validators seen recently), and never uses it. The
quorum therefore does **not** shrink when validators stop being
seen. A partition lowers nothing on its own: the quorum stays 17
until the negative UNL changes the effective size. (Drill D-04a
demonstrates this.)

## 2. Crash loss (validators down, the rest connected)

[SIMULATED] Remaining r = 25 − k validators can fully validate a
ledger iff r ≥ quorum:

| Lost k | Remaining r | Validates @67% (q=17) | Validates @80% (q=20) |
|---|---|---|---|
| 0 | 25 | yes | yes |
| 1 | 24 | yes | yes |
| 2 | 23 | yes | yes |
| 3 | 22 | yes | yes |
| 4 | 21 | yes | yes |
| 5 | 20 | yes | yes |
| 6 | 19 | yes | **no** |
| 7 | 18 | yes | **no** |
| 8 | 17 | yes | **no** |

Maximum tolerable crash loss: **8 @67%, 5 @80%**.

## 3. Partitions (network split into two sides)

[SIMULATED] A side of size s can fully validate iff s ≥ quorum.
A fork needs both sides at quorum, i.e. 2 × quorum ≤ 25:

| Split | @67% | @80% |
|---|---|---|
| 25/0 … 17/8 | larger side continues, smaller stalls | larger side continues (down to 20/5), smaller stalls |
| 16/9 … 13/12 | both sides halt | both sides halt |

Minimum survivable partition: **17 validators (68%) @67%**,
**20 (80%) @80%**. No partition of a single shared UNL can fork:
at 67%, 2 × 17 = 34 > 25; at 80%, 2 × 20 = 40 > 25. A fork needs
UNL divergence — different validators trusting different lists —
which is what section 4 bounds.

## 4. UNL overlap — Theorem 8, derived honestly

### 4.1 What the paper actually says

[MEASURED] Theorem 8 of Chase & MacBrough, "Analysis of the XRP
Ledger Consensus Protocol" (arXiv:1802.07242), verified verbatim
against the arXiv HTML version:

> "XRP LCP guarantees fork safety if Oi,j > nj/2 + ni − qi + ti,j
> for every pair of nodes Pi, Pj."

where Oi,j is the pairwise UNL overlap, ni/nj the UNL sizes,
qi the validation quorum, and ti,j = min(ti, tj, Oi,j) the
tolerated Byzantine faults in the overlap. The paper states
immediately after that the condition is **sufficient, not
necessary**, and that under 80% quorums and 20% faults it
"can be summarized as requiring roughly >90% UNL overlaps".

### 4.2 The bound for equal-size UNLs

[SIMULATED] For ni = nj = n, qi = qj = q, ti = tj = t, write
pi = ni − Oi,j and pj = nj − Oi,j for the per-side counts of
validators outside the overlap. Substituting into Theorem 8:

    O > n/2 + n − q + t
    n − pi > (n − pi + pj)/2 + n − q + t
    pi + pj < 2q − 2t − n

This is the exact bound the model tabulates, for every tolerated
fault count t = 0 … (n − q). (Assumption A-2: equal-size UNLs and
an even split of the total difference, so minimum overlap =
n − (max total difference)/2.)

**67% rule (q = 17, n = 25):**

| Byzantine t | Bound pi+pj < | Max total difference | Min overlap |
|---|---|---|---|
| 0 | 9 | 8 | 21 |
| 1 | 7 | 6 | 22 |
| 2 | 5 | 4 | 23 |
| 3 | 3 | 2 | 24 |
| 4 | 1 | 0 | 25 |
| 5–8 | ≤ −1 | — (no overlap certifies) | — |

**80% rule (q = 20, n = 25):**

| Byzantine t | Bound pi+pj < | Max total difference | Min overlap |
|---|---|---|---|
| 0 | 15 | 14 | 18 |
| 1 | 13 | 12 | 19 |
| 2 | 11 | 10 | 20 |
| 3 | 9 | 8 | 21 |
| 4 | 7 | 6 | 22 |
| 5 | 5 | 4 | 23 |

### 4.3 The 67% quorum forfeits the Theorem 8 certificate

[SIMULATED] At 67% quorum with worst-case faults (t = n − q = 8,
i.e. 33% Byzantine), the bound is 2×17 − 2×8 − 25 = **−7**. No
overlap satisfies Theorem 8 — not even identical UNLs. The theorem
cannot certify fork safety at 67% under the fault model the code
itself states (ti ≤ ni − qi). The certificate returns only as the
assumed fault count falls: at t = 4 the UNLs must already be
identical, and only at t = 0 does the familiar 21-of-25 figure
appear.

[MEASURED] The in-code comment at `ValidatorList.cpp:1898–1932`
quotes Theorem 8 correctly and then derives:

> "A 67% quorum allows two UNLs to safely have < .33*ni unique
> validators between them: pi + pj < .33*ni"

That conclusion does not follow from the formula it quotes under
the fault model it states. Substituting qi = 0.67ni and
ti,j = 0.33ni into the derivation above gives
pi + pj < 2(0.67ni) − 2(0.33ni) − ni = −0.32ni — impossible. The
claimed bound follows only if ti,j = 0, i.e. **zero Byzantine
faults**, while the same comment states ti ≤ .33ni. The 21-of-25
minimum overlap quoted for 67% in earlier work is therefore the
zero-Byzantine bound, not the worst-case bound. This is finding
R-01 in `docs/REMEDIATION.md`. The code itself
(`calculateQuorum`) is correct; the comment overstates what the
quorum guarantees.

### 4.4 What does protect the testnet, then

[SIMULATED] Theorem 8 is sufficient, not necessary, so its silence
at 67% is not proof of a fork. The direct quorum-intersection
argument covers the case that actually holds on the testnet —
identical UNLs. Two quorums of 17 drawn from the same 25 validators
intersect in at least 17 + 17 − 25 = 9 validators; with at most 8
Byzantine, at least one honest validator sits in every quorum
intersection, and an honest validator never validates conflicting
ledgers at the same sequence (the mechanism of Lemma 6 in the
paper). So with a single shared UNL, no fork is possible at 67%
even with t = 8. Fork safety on the testnet therefore rests on UNL
uniformity — every validator using the same published list — not on
Theorem 8. That uniformity is itself an assumption (A-1): the
per-validator UNL contents are not observable from the public RPC,
and a single publisher (`postfiat.org`) supplies the list.

[MEASURED] On liveness, the paper's Theorem 11 says a network of a
single agreed-upon UNL plus leaves cannot get stuck (quorum
n − floor((n−1)/k); here q = 17 = 25 − floor(24/3), so k = 3 and
|X| = 25 ≥ 3). Conversely its Example 9 shows a network can get
stuck even with 99% UNL overlap and no Byzantine faults once UNLs
diverge. Both point the same way: uniformity is the load-bearing
property.

## 5. Negative-UNL recovery

[MEASURED] The NegativeUNL amendment is **enabled** on the testnet
(`feature` RPC, amendment
`B4E4F5D2D6FB84DF7399960A732309C9FD530EAE5941838160042833625A6076`,
enabled: true, supported: true; see `data/features_sample.json`).

[MEASURED] The voting rules, from
`src/xrpld/app/misc/NegativeUNLVote.h`:

- A validator is a disable candidate if it validated in fewer than
  50% of the last flag period (`negativeUNLLowWaterMark`,
  lines 56–57: 256 × 50/100 = **128** of 256 ledgers; the check is
  score < 128).
- Re-enable needs a score above 80% (`negativeUNLHighWaterMark`,
  lines 62–63: 256 × 80/100 = **204**; the check is score > 204,
  so the minimum qualifying score is 205 of 256).
- The local node votes only if it issued more than 90%
  (`negativeUNLMinLocalValsToVote`, lines 68–69: 256 × 90/100 =
  **230**; the check is score > 230, so the minimum qualifying
  count is 231 of 256; 230 or fewer abstains).
- At most 25% of the UNL can be listed (`negativeUNLMaxListed`,
  line 78): ceil(25 × 0.25) = **7** validators.
- A flag period is 256 ledgers (`FLAG_LEDGER_INTERVAL`,
  `src/xrpld/app/ledger/Ledger.h:426`); voting happens on voting
  ledgers, when the feature is enabled
  (`src/xrpld/app/consensus/RCLConsensus.cpp:379-385`, voting-ledger
  gate + `nUnlVote_.doVoting`).

[SIMULATED] With 7 validators listed, the effective UNL size is 18
and the quorum becomes max(ceil(18 × 0.67), 15) = **15**. So a
validating 17-side can, after listing, tolerate 2 further losses
(down to 15). Detection takes at least one flag period:
256 ledgers × 3.0000 s ≈ **768 s (~12.8 min)** at the measured close
step, before a missing validator can even become a candidate.

[SIMULATED] The trap (finding R-03): the votes are cast by
UNLModify transactions inside ledgers, so a side must be able to
close ledgers to vote. A side with 16 or fewer validators cannot
reach quorum 17, cannot close ledgers, and therefore cannot vote to
lower its own quorum. The negative UNL can only help a side that is
already validating. A fresh partition still needs 17 to start;
15 is the floor only for a side that activated the negative UNL
before further losses. Drill D-04 demonstrates all four steps.

## 6. Limits of this model

- [UNSUPPORTED] Whether every validator actually uses the published
  list (A-1). The model assumes it; the public RPC cannot confirm
  or refute it per validator.
- [UNSUPPORTED] Behavior under real load or real Byzantine faults.
  All loss/partition figures are analytic; no validator was ever
  taken down and no partition was ever induced on the live network.
- [UNSUPPORTED] Any claim about mainnet. All measurements are
  testnet (network_id 2025); mainnet does not exist yet, and the
  67% → 80% quorum revert is unexecuted.
- [SIMULATED] Time conversions use the fresh 11-header close sample
  (mean 3.0000 s, n = 10 diffs, 10 s resolution). They are
  order-of-magnitude, not precise timings.
- [SIMULATED] The overlap tables assume equal-size UNLs and an even
  split of the difference (A-2). Unequal UNLs change the numbers;
  the general formula Oi,j > nj/2 + ni − qi + ti,j still applies.
