# England's SEND system: what the data predicted, and what it predicts now

**Briefing note | Matt Sharpe, Oxford Internet Institute / Automattic | May 2026**

---

### What this analysis does

Using ten years of publicly available Crown data — DfE SEN2 statistics, S251 local authority expenditure returns, and SEND Tribunal records — this analysis tests whether the collapse of EHCP services in England's most financially stressed councils was foreseeable, and identifies which councils currently show the same pre-crisis signatures.

---

### Three findings

**1. The collapse was foreseeable — but different failure types had different warning signals.**

Eight predictive models were validated against 140+ local authorities. Timeliness failure (councils falling below 40% on-time EHCPs) was predicted by absolute growth in ASD and SEMH caseloads from as early as 2019 — *before* financial or legal-pressure data added meaningful signal. Legal-pressure and placement-cost failure were predicted from 2016 by tribunal appeal rates and independent-provider spending. These are distinct early warning signals, for distinct failure modes. No single indicator captures both.

**2. Official monitoring was watching the wrong measure.**

Published tracking — by DfE, IFS, and IfG — reports ASD and SEMH as a *percentage* of total EHCPs. This analysis shows that proportional share is near-useless for prediction (AUC ~0.50, equivalent to chance). Absolute volume — the raw number of ASD and SEMH EHCPs growing year on year — is the informative signal. Monitoring systems designed around shares missed the throughput-capacity squeeze before it became visible in timeliness statistics.

**3. Six councils currently show pre-crisis signatures with no formal DfE intervention.**

A predictive model trained on 2021 features — with no knowledge of Safety Valve or DBV programme membership — identifies the following councils as structurally similar to those that entered systemic failure:

| Council | Risk score | Mean timeliness 2022–24 | Appeal rate | Indep./1,000 pupils |
|---|---|---|---|---|
| Bristol, City of | 0.90 | 37.5% | 2.9% | 2.55 |
| Birmingham | 0.82 | 49.4% | 5.6% | 1.05 |
| Bromley | 0.77 | 33.7% | 4.0% | 3.86 |
| Lewisham | 0.72 | 53.5% | 2.6% | 5.28 |
| Staffordshire | 0.69 | 33.5% | 5.3% | 4.65 |
| Central Bedfordshire | 0.64 | 26.5% | 2.5% | 1.0 |

Several are already in collapse on individual indicators. Central Bedfordshire's 26.5% mean timeliness is among the worst of any council nationally. These are observations, not predictions: the crisis is present, not merely approaching.

*Risk scores are model outputs reflecting structural similarity to councils that entered collapse — not official designations. Enfield (score 0.69) is excluded from this shortlist because its 20-week timeliness is 89.7% — no crisis signal on any individual indicator.*

---

### The policy question

The government's February 2026 white paper addresses the structural design failures of the 2014 Act. This is the right long-run response. But neither the old system nor the new one includes a public, validated early-warning framework that combines absolute need-type growth, timeliness trend, independent-provider exposure, tribunal pressure, and DSG balance.

The data to build such a framework is already published. The question is whether DfE is using it — and whether the councils above are receiving proactive engagement proportionate to the risk the data shows.

---

### Full analysis and code

All code, data, and methodology are publicly available and fully reproducible:
**github.com/Kali89/la-send-analysis**

Three substantive articles are published in the repository: the original queue-vs-gatekeeping analysis, the forecastability study, and a structured post-mortem of the policy failure.

---

*Matt Sharpe is a staff data scientist at Automattic and a part-time DPhil candidate in Social Data Science at the Oxford Internet Institute. This analysis was conducted independently using publicly available data.*

*Correspondence: matthew.sharpe@a8c.com*
