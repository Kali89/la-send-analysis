# Anticipated challenges
### Questions journalists or officials may raise, and how to answer them

---

## "These are just model outputs — you can't say these councils are at risk"

**Short answer**: For two of the six named councils, "at risk" understates what the data shows. Essex issued 9.3% of EHCPs on time over 2022–2024; Newcastle upon Tyne issued 9.4%. These councils are not flagged as potentially failing in the future — they are failing now, on the statutory legal standard, by a wide margin. Bromley (33.7%), Staffordshire (33.5%), and Derby (20.6%) are below the 40% threshold used throughout this analysis. Hertfordshire (43.0%) is borderline. The model risk scores are corroborated by the observed timeliness data. The model is confirming what the raw numbers already show.

---

## "The 2026 white paper addresses the structural problems — why does the operational picture matter?"

**Short answer**: The white paper's structural redesign — the four-tier system, national price bands for independent school fees, and EHCP restrictions from 2030 — is the right long-run response. But structural reform operating on a five-year legislative and implementation timescale does not address what is happening now in councils that are already failing and have no formal DfE programme around them. Essex and Newcastle have timeliness below 10%. Hertfordshire's appeal rate is 11.7%. These councils are deteriorating while the structural framework is still being built. Proactive data-driven engagement with failing councils — using the kind of early-warning monitoring this analysis sets out — and structural legislative reform are not mutually exclusive. Both tracks can run simultaneously.

---

## "You're unfairly targeting specific councils"

**Short answer**: The councils are identified by their own published data — timeliness statistics, tribunal rates, and spend figures that DfE publishes annually. Nothing in this analysis is derived from non-public information. Any council can verify its own numbers. Essex, Newcastle, Bromley, Hertfordshire, Staffordshire, and Derby are named because their situation warrants public transparency, not because of any editorial judgement about their leadership or intent.

---

## "Correlation isn't causation — you can't say tribunal rates predict collapse"

**Short answer**: Agreed, and the analysis does not claim causation. The claim is that tribunal appeal rates and independent placement spend were early observable signals of structural conditions that subsequently produced collapse — and that these signals were in the public data and were not acted on. A model that achieves AUC 0.88 from 2021 data does not need to establish causation to be a useful early warning tool.

---

## "Safety Valve LAs were already struggling before the programme — the programme isn't making things worse"

**Short answer**: This is correct and is stated in the analysis. Safety Valve LAs were already 11.6 percentage points worse on timeliness in the three years before they entered the programme (52.6% vs 64.2% for controls). The programme identified the right councils. The finding is not that the programme made things worse — it is that the programme has not reversed the underlying structural deterioration, and that six comparable councils with no intervention are now showing the same signals.

---

## "Your refusal rate finding is misleading — councils use delays to gatekeep, not refusals"

**Short answer**: This is a valid limitation, stated explicitly in the methodology. The refusal rate comparison shows that Safety Valve councils refuse 26.7% of applications versus 22.9% for no-programme councils — a difference that is not statistically significant (p=0.126). Programme status is not a reliable predictor of refusal rate: councils in all categories show both high and low refusal rates. The headline finding is not that one group gatekeeps more aggressively than another; it is that the gatekeeping framing as applied to programme entry does not hold in the published data. The delay-as-gatekeeping hypothesis is a separate and valid concern — where councils with large backlogs have lower apparent refusal rates because many decisions are still pending — and is noted in the methodology. That further concern reinforces, not undermines, the overall argument about throughput failure.

---

## "Why should we trust an independent analysis over the DfE's own monitoring?"

**Short answer**: The DfE's own monitoring data is the source material for this analysis. Every figure used — timeliness, refusal rates, tribunal appeal rates, S251 expenditure returns — is Crown Copyright data published by DfE. The analysis applies statistical methods to that data that go beyond what DfE currently publishes. All code, data outputs, and methodology are publicly available for scrutiny and replication. This is not a claim that DfE's data is wrong — it is an argument that more can be done with it.

---

## "The AUC values aren't that impressive — 0.70 isn't much better than random"

**Short answer**: AUC 0.70 is from 2016 data — six years before the collapse outcome. At training year 2021 (three years before the collapse window), the best model achieves AUC 0.88. For context, medical early-warning tools with AUC in the 0.70–0.80 range are routinely used to trigger clinical interventions. The relevant standard is not perfection but whether the signal was actionable — and at AUC 0.70 in 2016, it was.

---

## "Is the £75,000 saving per child too high? Independent placements often reflect genuine specialist need"

**Short answer**: The £75,000 figure is deliberately conservative — well below the S251 median independent placement cost of £97,322 per child per year in 2023/24. It is also not assumed that all independent placements are substitutable. The model applies a 40% base diversion rate (the share of new maintained places assumed to redirect children from the independent sector), adjusted upward for LAs with already-high independent placement rates and capped at 65%. This explicitly builds in the assumption that a substantial proportion of independent placements reflect genuine specialist needs that would not be met in the maintained sector. The sensitivity analysis confirms that the invest-to-save case is robust at £60,000 per child and above, at base capital costs.

---

## "Are you suggesting children should be moved out of independent placements to save money?"

**Short answer**: No. The analysis is about preventing avoidable independent placements where suitable maintained provision could have been built locally — not about moving children currently in appropriate independent settings. When a child ends up in an independent school because no maintained alternative exists within reasonable distance, that is a commissioning failure, not a reflection of individual need. The cost-benefit model captures only this avoidable portion. It does not recommend disrupting existing placements.

---

## "Does the cost-benefit model include optimism bias and capital overruns?"

**Short answer**: It does not include a formal HMT optimism-bias adjustment. However, the sensitivity analysis explicitly models capital cost overruns. A 25% overrun increases total capital from £420 million to £525 million; at the base £75,000 saving assumption, the 15-year discounted NPV remains positive at £116 million. A 40% overrun at the same saving assumption gives an NPV of £53 million — still positive. The case turns negative only if both savings are at the very conservative £60,000 level and capital overruns by 25% or more. The model also includes occupancy ramp-up schedules (no revenue until facilities open, then phased to full capacity) and facility-specific lead times. These are published in `cost_benefit_sensitivity.csv` in the repository.

---

*Contact: Matthew Sharpe, matthew.sharpe@oii.ox.ac.uk*
*Full analysis: github.com/Kali89/la-send-analysis*
