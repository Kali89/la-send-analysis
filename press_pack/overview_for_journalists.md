# Overview for journalists
### England's SEND system: diagnosis, evidence, and what should happen

---

## The one-sentence finding

England's councils are not refusing too many children with special educational needs — they are legally required to process them but structurally unable to do so on time, and the government's five-year intervention programme has not fixed the underlying cause.

---

## What everyone thought

When the Department for Education launched its "Safety Valve" programme in 2022, placing 29 local authorities under financial supervision, the implicit diagnosis was that these councils were too generous — issuing too many Education, Health and Care Plans and failing to push back on families making unreasonable demands. The framing suggested that tighter gatekeeping would reduce costs and restore financial balance.

---

## What the data show

The gatekeeping hypothesis does not survive contact with the published data. Safety Valve councils refuse EHCP applications at 25.3%; councils with no intervention refuse at 25.1%. The difference is statistically indistinguishable (Mann-Whitney p = 0.76). The published data do not show Safety Valve councils formally refusing more or accepting fewer children at the front door. They are failing — on a legal statutory duty — to deliver the plan within 20 weeks of accepting the case.

Safety Valve councils issued only 35.8% of new EHCPs within the 20-week legal limit in 2024, against 57.0% for non-intervention councils. They face tribunal challenge rates of 7.5% of live EHCPs against 5.4% elsewhere. They place 37% more children per 1,000 pupils in independent specialist schools than non-intervention councils (0.89 vs 0.65 per 1,000), at a median cost of £97,322 per child per year.

This is a throughput failure, not a gatekeeping failure. The queue grows; the capacity to process it does not.

---

## Why Safety Valve failed

The Safety Valve programme treated the symptom — DSG deficits — rather than the cause. The deficits exist because councils do not have enough maintained special school places in the right locations for the right need types. When a child cannot access a maintained place locally, they are placed in an independent school. That placement costs the local authority roughly four times more than a maintained place. The deficit deepens. Councils cut support services. Plans worsen. Families go to tribunal. Legal costs rise. The cycle continues.

Predictive models trained only on data available before the Safety Valve programme existed could identify — from 2021 data — which councils would enter crisis, with cross-validated accuracy of AUC 0.88. The signals were in the public data: rising tribunal appeal rates, growing independent placement spend, flat timely-throughput against rising demand. They were not acted on through any public early-warning framework visible in the published record.

---

## What should happen now

The solution is not another retrospective bailout programme. It is a forward capital plan: build the right maintained provision, in the right places, for the right need types, before independent placements and tribunal pressure overwhelm more councils.

This analysis identifies 467 LA × need-type gaps across England, ranked by urgency. The top 30 alone — 20 new maintained special schools and 10 resourced provision units — address the most acute structural deficits in Hampshire, Essex, Norfolk, Cornwall, Suffolk, Lancashire, Bradford, Hertfordshire, and elsewhere. Each recommendation includes a specific location within the authority, derived from LSOA-level access modelling.

---

## The costed case

Thirty priority facilities require approximately £420 million of capital investment (ESFA free school programme benchmarks: £20 million per new special school, £2 million per resourced provision unit). Against the S251-derived saving of £75,000 per year for each child redirected from independent to maintained provision — conservative relative to the £97,322 median independent placement cost — the portfolio generates cumulative avoided costs that cross the £420 million threshold in 2034. By 2040, avoided costs reach £887 million against a £420 million investment. The 15-year Green Book-style discounted net present value is £220 million.

The urgency is created by lead times. New maintained special schools take four to six years from planning to first pupils. A capital decision deferred to 2027 delivers no new places before 2033 — and locks in three further years of independent placement costs accumulating at current rates.

---

## What good looks like

Five English councils demonstrate that high-performing SEND systems are achievable within existing structures: Lincolnshire (99% of EHCPs issued on time), Liverpool (97.9%), Southampton (93.5%), Oldham (85.8%), and Gateshead (82.3%). All maintain more than 5 maintained special school places per 1,000 pupils and place fewer than 7% of children in the independent sector.

These are not wealthy councils. Liverpool's average deprivation score (IMD 42.4) is among the highest in the dataset — substantially higher than Devon's (IMD 18.0), yet Liverpool achieves timeliness nearly 30 times higher than Devon's 3.2%. This evidence weakens the argument that poor performance is explained solely by deprivation or hard-to-serve populations. It suggests that maintained supply, throughput capacity, and system design matter considerably.

---

## The six councils to watch now

Six councils currently show the pre-crisis structural signatures of Safety Valve entrants, with no formal DfE intervention: Bristol (risk score 0.90, mean timeliness 37.5%), Birmingham (0.86), Bromley (0.77), Lewisham (0.69), Staffordshire (0.69), and Central Bedfordshire (0.66, timeliness 26.5%). Several are already in de facto collapse on the statutory standard. The question for DfE is whether it is engaging them before, or after, deficits become unmanageable.

---

## Caveats

- The cost-benefit model is indicative. It uses a Green Book-style discount rate (3.5%) and conservative diversion assumptions, but has not been subject to formal HMT optimism-bias adjustment. A 25% capital cost overrun would extend break-even by approximately two years without changing the sign of the 15-year NPV.
- Not all children in independent special schools could be served in maintained settings. The model assumes a 40% diversion rate (adjusted upward for LAs with high existing independent placement rates, capped at 65%), reflecting that some independent placements meet genuinely specialist needs unavailable in the maintained sector.
- The comparator councils (Lincolnshire, Liverpool, Southampton, Oldham, Gateshead) illustrate that better outcomes are achievable under challenging conditions. They do not prove causation between supply levels and timeliness; other factors — commissioning culture, workforce stability, long-standing investment decisions — will also matter.
- All figures are derived from publicly available Crown copyright data (S251, SEN2, GIAS). The analysis applies statistical methods beyond what DfE currently publishes; it does not claim DfE's data is wrong.

---

## Contact and access

**Author**: Matt Sharpe, Oxford Internet Institute / Automattic
**Email**: matthew.sharpe@oii.ox.ac.uk
**Full analysis, data and code**: github.com/Kali89/la-send-analysis

*All underlying data is Crown Copyright (DfE). Methodology, code, and outputs are fully open and reproducible.*
